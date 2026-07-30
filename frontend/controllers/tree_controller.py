import threading
from datetime import datetime, timezone

from PyQt6.QtCore import QObject, pyqtSignal

from core.port_check_manager import PortCheckManager
from core.workers.tree_loader_worker import TreeLoaderWorker
from core.protocol_launcher import ProtocolLauncher

from core.logger import get_logger
from core.api.base import ApiError
from core.workers.credentials_worker import CredentialsWorker
from core.workers.diagnostics_worker import DiagnosticsWorker
from core.ssh.diagnostics import CHECKS as DIAGNOSTIC_CHECKS, CUSTOM_CHECK_KEY

log = get_logger(__name__)


def _split_data(data: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    main_branches: list[dict] = []
    xclarity_branches: list[dict] = []
    ups_branches: list[dict] = []

    for branch in data:
        main_servers = []
        xclarity_servers = []
        ups_servers = []

        for server in branch.get("servers", []):
            dt = server.get("device_type")
            if dt == "xclarity":
                xclarity_servers.append(server)
            elif dt == "ups":
                ups_servers.append(server)
            else:
                main_servers.append(server)

        if main_servers:
            main_branches.append({**branch, "servers": main_servers})
        if xclarity_servers:
            xclarity_branches.append({**branch, "servers": xclarity_servers})
        if ups_servers:
            ups_branches.append({**branch, "servers": ups_servers})

    return main_branches, xclarity_branches, ups_branches


class TreeController(QObject):
    loaded = pyqtSignal()
    error_occurred = pyqtSignal(ApiError)
    system_error = pyqtSignal(object)  # Exception — окно показывает диалог ошибки
    checking_started = pyqtSignal()
    checking_finished = pyqtSignal()

    # Внутренний сигнал: перебрасывает результат сохранения комментария
    # из фонового потока в GUI-поток (напрямую трогать виджеты оттуда нельзя)
    _comment_saved = pyqtSignal(str, int, int, str, str)

    def __init__(
        self,
        api,
        dash_main,
        dash_xclarity,
        dash_ups,
        detail_tree,
        user_settings,
        busy,
        ask_master_password,
        show_credential_popup,
        ask_custom_command,
        show_diagnostics_result,
    ):
        """
        ask_master_password(ip, port, mode, on_submit),
        show_credential_popup(ip, port, username, password),
        ask_custom_command(ip) -> str | None и
        show_diagnostics_result(ip, port, label, output) — колбэки,
        реализованные в ui-слое: контроллер не знает о конкретных диалогах.
        """
        super().__init__()
        self.api = api
        self.dash_main = dash_main
        self.dash_xclarity = dash_xclarity
        self.dash_ups = dash_ups
        self.detail_tree = detail_tree
        self.user_settings = user_settings
        self.busy = busy
        self._ask_master_password = ask_master_password
        self._show_credential_popup = show_credential_popup
        self._ask_custom_command = ask_custom_command
        self._show_diagnostics_result = show_diagnostics_result
        self.detail_tree.set_user_settings(self.user_settings)

        self._data: list[dict] = []
        self._data_main: list[dict] = []
        self._data_xclarity: list[dict] = []
        self._data_ups: list[dict] = []
        self._servers_by_id: dict[int, dict] = {}
        self._active_tab: int = 0
        self._current_branch: str | None = None
        self._runtime_status = {}
        self.checker = PortCheckManager(max_threads=10)
        self._check_count = 0

        # Держим ссылки на все живые воркеры: перезапись единственного
        # атрибута уничтожала работающий QThread → краш.
        self._workers: set = set()

        self._comment_saved.connect(self._on_comment_saved)

    def _launch(self, worker):
        """Запускает QThread, сохраняя ссылку до его завершения."""
        self._workers.add(worker)
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        worker.start()

    @property
    def data(self) -> list[dict]:
        return self._data

    @property
    def active_data(self) -> list[dict]:
        if self._active_tab == 1:
            return self._data_xclarity
        if self._active_tab == 2:
            return self._data_ups
        return self._data_main

    def set_active_tab(self, index: int):
        self._active_tab = index

    def status_counts(self) -> tuple[int, int, int]:
        """Возвращает (up, partial, down) по серверам активной вкладки."""
        up = partial = down = 0
        for branch in self.active_data:
            for server in branch.get("servers", []):
                ports = server.get("ports", [])
                if not ports:
                    continue
                checked = [p for p in ports if p.get("is_up") is not None]
                if not checked:
                    continue
                has_up = any(p["is_up"] is True for p in checked)
                has_down = any(p["is_up"] is False for p in checked)
                if has_up and has_down:
                    partial += 1
                elif has_up:
                    up += 1
                else:
                    down += 1
        return up, partial, down

    def start_load(self):
        worker = TreeLoaderWorker(self.api)
        worker.success.connect(self._on_loaded)
        worker.error.connect(self._on_error)
        self._launch(worker)

    def _on_loaded(self, data):
        self._data = data
        self._data_main, self._data_xclarity, self._data_ups = _split_data(data)
        # Словари серверов разделяются между _data и срезами вкладок,
        # поэтому обновление через индекс видно во всех представлениях
        self._servers_by_id = {s["id"]: s for b in data for s in b.get("servers", [])}
        self._runtime_status.clear()
        self.dash_main.render(self._data_main)
        self.dash_xclarity.render(self._data_xclarity)
        self.dash_ups.render(self._data_ups)
        self.loaded.emit()

    def _on_error(self, message):
        error = ApiError(message, status_code=None)
        self.error_occurred.emit(error)

    def _begin_check(self, n: int):
        if n == 0:
            return
        if self._check_count == 0:
            self.checking_started.emit()
        self._check_count += n

    def _end_one(self):
        self._check_count -= 1
        if self._check_count == 0:
            self.checking_finished.emit()

    def refresh_all(self):
        active = self.active_data
        if not active:
            return

        servers = [s for b in active for s in b["servers"]]
        n = sum(len(s["ports"]) for s in servers)
        self._begin_check(n)
        self.checker.check_ports(servers, self._on_port_checked, self.api)

    def _on_port_checked(self, server_id, port, ok):
        self._runtime_status[(server_id, port)] = ok

        self._update_port_status(server_id, port)

        port_data = self._get_port_data(server_id, port)
        if port_data is not None:
            self.detail_tree.update_port_item(server_id, port, port_data)
            for ds, data in (
                (self.dash_main, self._data_main),
                (self.dash_xclarity, self._data_xclarity),
                (self.dash_ups, self._data_ups),
            ):
                for b in data:
                    if any(s["id"] == server_id for s in b.get("servers", [])):
                        ds.update_branch(b)
                        break

        self._end_one()

    def _get_port_data(self, server_id, port):
        server = self._servers_by_id.get(server_id)
        if server is None:
            return None
        for p in server.get("ports", []):
            if p["port"] == port:
                return p
        return None

    def _update_port_status(self, server_id, port):
        p = self._get_port_data(server_id, port)
        if p is None:
            return

        ok = self._runtime_status[(server_id, port)]
        p["is_up"] = ok

        now = datetime.now(timezone.utc).isoformat()
        if ok:
            p["last_success"] = now
        else:
            p["last_failure"] = now

    def show_all(self):
        if not self._data or not self._current_branch:
            return
        branch = next(
            (b for b in self.active_data if b["name"] == self._current_branch), None
        )
        if branch:
            self.detail_tree.render([branch])

    def show_problem(self):
        if not self._data or not self._current_branch:
            return
        branch = next(
            (b for b in self.active_data if b["name"] == self._current_branch), None
        )
        if not branch:
            return
        bad = [
            s
            for s in branch["servers"]
            if any(p.get("is_up") is False for p in s["ports"])
        ]
        if bad:
            self.detail_tree.render([{"name": branch["name"], "servers": bad}])

    def drill_into_branch(self, branch_name: str):
        self._current_branch = branch_name
        branch = next((b for b in self.active_data if b["name"] == branch_name), None)
        if branch:
            self.detail_tree.render([branch])
            self.detail_tree.expandAll()

    def clear_current_branch(self):
        self._current_branch = None

    def refresh_branch(self, branch_name: str):
        if not self._data:
            return

        branch = next((b for b in self._data if b["name"] == branch_name), None)
        if not branch:
            return

        servers = branch.get("servers", [])
        n = sum(len(s["ports"]) for s in servers)
        self._begin_check(n)
        self.checker.check_ports(servers, self._on_port_checked, self.api)

    def refresh_server(self, server_id: int, ip: str):
        server = self._servers_by_id.get(server_id)
        if server is None or not server["ports"]:
            return

        self._begin_check(len(server["ports"]))
        self.checker.check_ports([server], self._on_port_checked, self.api)

    def refresh_port(self, server_id: int, port: int, ip: str):
        server = self._servers_by_id.get(server_id)
        if server is None:
            return

        p = self._get_port_data(server_id, port)
        if p is None:
            return

        self._begin_check(1)
        self.checker.check_ports(
            [{"id": server_id, "ip": server["ip"], "ports": [p]}],
            self._on_port_checked,
            self.api,
        )

    def show_credentials(self, server_id: int, port: int, ip: str):
        self._ask_master_password(
            ip,
            port,
            "show",
            lambda master_password: self._start_credentials_worker(
                server_id, port, master_password
            ),
        )

    def _start_credentials_worker(self, server_id, port, master_password):
        admin_login = self.user_settings.get("admin_login")

        self.busy.start("Получение учётных данных…")

        worker = CredentialsWorker(
            api=self.api,
            server_id=server_id,
            port=port,
            username=admin_login,
            master_password=master_password,
        )

        def on_success(data):
            self.detail_tree.show_credentials(
                server_id,
                port,
                data["username"],
                data["password"],
                data.get("mnemonic", ""),
            )
            del data

        worker.finished.connect(self.busy.stop)
        worker.success.connect(on_success)
        worker.error.connect(self.error_occurred.emit)
        self._launch(worker)

    def run_diagnostic(self, server_id: int, port: int, ip: str, check_key: str):
        if check_key == CUSTOM_CHECK_KEY:
            command = self._ask_custom_command(ip)
            if not command:
                return
            label = "Своя команда"
        else:
            label, command = DIAGNOSTIC_CHECKS[check_key]

        self._ask_master_password(
            ip,
            port,
            "diagnostics",
            lambda mp: self._start_diagnostics_worker(
                server_id, port, ip, mp, command, label
            ),
        )

    def _start_diagnostics_worker(
        self, server_id, port, ip, master_password, command, label
    ):
        admin_login = self.user_settings.get("admin_login")

        self.busy.start(f"Выполнение: {label}…")

        worker = DiagnosticsWorker(
            api=self.api,
            server_id=server_id,
            port=port,
            ip=ip,
            username=admin_login,
            master_password=master_password,
            command=command,
        )

        def on_success(output):
            self._show_diagnostics_result(ip, port, label, output)

        def on_error(stage, exc):
            # "verify" — всегда ApiError (мастер-пароль/троттлинг), остальное
            # (SSH-ошибки) — через generic system_error
            if stage == "verify" and isinstance(exc, ApiError):
                self.error_occurred.emit(exc)
            else:
                self.system_error.emit(exc)

        worker.finished.connect(self.busy.stop)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        self._launch(worker)

    def _has_credentials(self, server_id: int, port: int) -> bool:
        # True если для порта в дереве есть credentials_updated_at — значит пароль сохранён.
        p = self._get_port_data(server_id, port)
        return bool(p and p.get("credentials_updated_at"))

    def connect_protocol(
        self, server_id: int, port: int, ip: str, _unused_protocol: str
    ):
        settings = self.user_settings
        external_apps = settings.get("external_apps") or []
        web_ports = settings.get("web_ports") or []
        has_creds = self._has_credentials(server_id, port)

        if port == 22:
            if has_creds:
                # Есть пароль → запрашиваем мастер-пароль → подключаемся с кредами
                self._ask_master_password(
                    ip,
                    port,
                    "ssh",
                    lambda mp: self._start_protocol_worker(server_id, port, mp, "ssh"),
                )
            else:
                # Нет пароля → сразу открываем SSH без кредов
                self._open_or_report("ssh", None, None, ip, port)
            return

        if port == 3389:
            if has_creds:
                self._ask_master_password(
                    ip,
                    port,
                    "rdp",
                    lambda mp: self._start_protocol_worker(server_id, port, mp, "rdp"),
                )
            else:
                self._open_or_report("rdp", None, None, ip, port)
            return

        for app in external_apps:
            if app.get("port") == port:
                if has_creds:
                    # Сначала мастер-пароль → потом открываем приложение + popup
                    self._ask_then_open(
                        server_id,
                        ip,
                        port,
                        open_fn=lambda: ProtocolLauncher.open_external(app.get("path")),
                    )
                else:
                    try:
                        ProtocolLauncher.open_external(app.get("path"))
                    except Exception as e:
                        self.system_error.emit(e)
                return

        scheme = None
        for entry in web_ports:
            if entry.get("port") == port:
                scheme = entry.get("scheme")
                break

        if not scheme:
            self.system_error.emit(RuntimeError("UNSUPPORTED_PROTOCOL"))
            return

        if has_creds:
            # Сначала мастер-пароль → потом открываем браузер + popup
            self._ask_then_open(
                server_id,
                ip,
                port,
                open_fn=lambda: ProtocolLauncher.open(scheme, None, None, ip, port),
            )
        else:
            # Нет пароля → просто открываем браузер
            self._open_or_report(scheme, None, None, ip, port)

    def _open_or_report(self, protocol, username, password, ip, port):
        try:
            ProtocolLauncher.open(protocol, username, password, ip, port)
        except Exception as e:
            log.exception("Ошибка запуска протокола %s", protocol)
            self.system_error.emit(e)

    def _start_protocol_worker(self, server_id, port, master_password, protocol):
        admin_login = self.user_settings.get("admin_login")
        self.busy.start(f"Получение учётных данных для {protocol.upper()}…")

        worker = CredentialsWorker(
            api=self.api,
            server_id=server_id,
            port=port,
            username=admin_login,
            master_password=master_password,
        )

        def on_success(data):
            username = data["username"]
            password = data["password"]
            del data
            server = self._servers_by_id.get(server_id)
            if server is None:
                return
            self._open_or_report(protocol, username, password, server["ip"], port)

        worker.finished.connect(self.busy.stop)
        worker.success.connect(on_success)
        worker.error.connect(self.error_occurred.emit)
        self._launch(worker)

    def _ask_then_open(self, server_id: int, ip: str, port: int, open_fn):
        # Запрашивает мастер-пароль → получает учётные данные →
        # вызывает open_fn() (открывает браузер/приложение) → показывает popup.
        self._ask_master_password(
            ip,
            port,
            "show",
            lambda mp: self._start_popup_worker(server_id, ip, port, mp, open_fn),
        )

    def _start_popup_worker(
        self, server_id: int, ip: str, port: int, master_password: str, open_fn
    ):
        admin_login = self.user_settings.get("admin_login")
        self.busy.start("Получение учётных данных…")

        worker = CredentialsWorker(
            api=self.api,
            server_id=server_id,
            port=port,
            username=admin_login,
            master_password=master_password,
        )

        def on_success(data):
            # Сначала открываем браузер/приложение, потом показываем popup
            try:
                open_fn()
            except Exception as e:
                self.system_error.emit(e)
            self._show_credential_popup(ip, port, data["username"], data["password"])
            del data

        worker.finished.connect(self.busy.stop)
        worker.success.connect(on_success)
        worker.error.connect(self.error_occurred.emit)
        self._launch(worker)

    def save_comment(self, item_type: str, server_id: int, port: int, comment: str):
        # Сохраняет комментарий в БД в фоновом потоке.
        # Данные и UI обновляются в GUI-потоке через сигнал _comment_saved.
        def _do():
            try:
                if item_type == "server":
                    self.api.servers.update_comment(server_id, comment)
                else:
                    self.api.ports.update_comment(server_id, port, comment)

                now = datetime.now(timezone.utc).isoformat()
                self._comment_saved.emit(item_type, server_id, port, comment, now)

            except Exception as e:
                log.error("Ошибка сохранения комментария: %s", e)

        threading.Thread(target=_do, daemon=True).start()

    def _on_comment_saved(self, item_type, server_id, port, comment, now):
        self._update_comment_in_data(item_type, server_id, port, comment, now)
        self.detail_tree.update_comment_item(item_type, server_id, port, comment, now)

    def _update_comment_in_data(self, item_type, server_id, port, comment, now):
        server = self._servers_by_id.get(server_id)
        if server is None:
            return

        if item_type == "server":
            server["comment"] = comment or None
            server["comment_updated_at"] = now
            return

        for p in server.get("ports", []):
            if p["port"] == port:
                p["comment"] = comment or None
                p["comment_updated_at"] = now
                return
