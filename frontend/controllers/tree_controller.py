from datetime import datetime, timezone

from PyQt6.QtCore import QObject, pyqtSignal

from core.port_check_manager import PortCheckManager
from core.workers.tree_loader_worker import TreeLoaderWorker
from core.protocol_launcher import ProtocolLauncher

from core.logger import get_logger
from core.api.base import ApiError
from core.workers.credentials_worker import CredentialsWorker
from ui.dialogs.credentials_dialog import CredentialsDialog

from ui.error_handler import handle_system_error


log = get_logger(__name__)


class TreeController(QObject):
    loaded = pyqtSignal()
    error_occurred = pyqtSignal(ApiError)
    checking_started = pyqtSignal()
    checking_finished = pyqtSignal()

    def __init__(self, api, tree, user_settings, busy):
        super().__init__()
        self.api = api
        self.tree = tree
        self.user_settings = user_settings
        self.busy = busy
        self.tree.set_user_settings(self.user_settings)

        self._data = None
        self._runtime_status = {}
        self.checker = PortCheckManager(max_threads=10)
        self._worker = None
        self._check_count = 0

    # =========================
    # ЗАГРУЗКА ДЕРЕВА
    # =========================
    def start_load(self):
        self._worker = TreeLoaderWorker(self.api)
        self._worker.success.connect(self._on_loaded)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_loaded(self, data):
        self._data = data
        self._runtime_status.clear()
        self.tree.render(self._data)
        self.loaded.emit()

    def _on_error(self, message):
        error = ApiError(message, status_code=None)
        self.error_occurred.emit(error)

    # =========================
    # ПРОВЕРКА ПОРТОВ
    # =========================
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
        if not self._data:
            return

        servers = [s for b in self._data for s in b["servers"]]
        n = sum(len(s["ports"]) for s in servers)
        self._begin_check(n)
        self.checker.check_ports(servers, self._on_port_checked, self.api)

    def _on_port_checked(self, server_id, port, ok):
        self._runtime_status[(server_id, port)] = ok

        self._update_port_status(server_id, port)

        port_data = self._get_port_data(server_id, port)
        if port_data is not None:
            self.tree.update_port_item(server_id, port, port_data)

        self._end_one()

    def _get_port_data(self, server_id, port):
        for b in self._data:
            for s in b["servers"]:
                if s["id"] != server_id:
                    continue
                for p in s["ports"]:
                    if p["port"] == port:
                        return p
        return None

    def _update_port_status(self, server_id, port):
        now = datetime.now(timezone.utc).isoformat()

        for b in self._data:
            for s in b["servers"]:
                if s["id"] != server_id:
                    continue

                for p in s["ports"]:
                    if p["port"] != port:
                        continue

                    ok = self._runtime_status[(server_id, port)]
                    p["is_up"] = ok

                    if ok:
                        p["last_success"] = now
                    else:
                        p["last_failure"] = now

                    return

    # =========================
    # ФИЛЬТРЫ
    # =========================
    def show_all(self):
        if self._data:
            self.tree.render(self._data)

    def show_problem(self):
        if not self._data:
            return

        result = []

        for b in self._data:
            bad = [
                s
                for s in b["servers"]
                if any(p.get("is_up") is False for p in s["ports"])
            ]
            if bad:
                result.append({"name": b["name"], "servers": bad})

        self.tree.render(result)

    # =========================
    # Контекст меню
    # =========================

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
        for b in self._data:
            for s in b["servers"]:
                if s["id"] != server_id:
                    continue

                if not s["ports"]:
                    return

                self._begin_check(len(s["ports"]))
                self.checker.check_ports([s], self._on_port_checked, self.api)
                return

    def refresh_port(self, server_id: int, port: int, ip: str):
        for b in self._data:
            for s in b["servers"]:
                if s["id"] != server_id:
                    continue

                for p in s["ports"]:
                    if p["port"] != port:
                        continue

                    self._begin_check(1)
                    self.checker.check_ports(
                        [{"id": server_id, "ip": s["ip"], "ports": [p]}],
                        self._on_port_checked,
                        self.api,
                    )
                    return

    def show_credentials(self, server_id: int, port: int, ip: str):
        dlg = CredentialsDialog(ip, port)

        dlg.submitted.connect(
            lambda master_password: self._start_credentials_worker(
                server_id, port, master_password
            )
        )

        dlg.exec()

    def _start_credentials_worker(self, server_id, port, master_password):
        admin_login = self.user_settings.get("admin_login")

        self.busy.start("Получение учётных данных…")

        self._credentials_worker = CredentialsWorker(
            api=self.api,
            server_id=server_id,
            port=port,
            username=admin_login,
            master_password=master_password,
        )

        def on_success(data):
            self.tree.show_credentials(
                server_id,
                port,
                data["username"],
                data["password"],
                data.get("mnemonic", ""),
            )
            del data

        def on_error(e: ApiError):
            self.error_occurred.emit(e)

        self._credentials_worker.finished.connect(self.busy.stop)
        self._credentials_worker.success.connect(on_success)
        self._credentials_worker.error.connect(on_error)
        self._credentials_worker.start()

    def connect_protocol(
        self, server_id: int, port: int, ip: str, _unused_protocol: str
    ):
        settings = self.user_settings
        external_apps = settings.get("external_apps") or []
        web_ports = settings.get("web_ports") or []
        # =========================
        # SSH
        # =========================
        if port == 22:
            protocol = "ssh"

        # =========================
        # RDP
        # =========================
        elif port == 3389:
            protocol = "rdp"

        else:
            protocol = None

            # =========================
            # EXTERNAL APP (приоритет)
            # =========================
            for app in external_apps:
                if app.get("port") == port:
                    try:
                        ProtocolLauncher.open_external(app.get("path"))
                    except Exception as e:
                        handle_system_error(None, e)
                    return

            # =========================
            # WEB
            # =========================
            for entry in web_ports:
                if entry.get("port") == port:
                    protocol = entry.get("scheme")
                    break

        # =========================
        # Если ничего не найдено
        # =========================
        if not protocol:
            handle_system_error(None, RuntimeError("UNSUPPORTED_PROTOCOL"))
            return

        # =========================
        # WEB — без мастер-пароля
        # =========================
        if protocol in ("http", "https"):
            try:
                ProtocolLauncher.open(protocol, None, None, ip, port)
            except Exception as e:
                log.exception("Ошибка запуска WEB протокола")
                handle_system_error(None, e)
            return

        # =========================
        # SSH / RDP — с мастер-паролем
        # =========================
        dlg = CredentialsDialog(ip, port, mode=protocol)

        dlg.submitted.connect(
            lambda master_password: self._start_protocol_worker(
                server_id, port, master_password, protocol
            )
        )

        dlg.exec()

    def _start_protocol_worker(self, server_id, port, master_password, protocol):
        admin_login = self.user_settings.get("admin_login")

        self.busy.start(f"Получение учётных данных для {protocol.upper()}…")

        self._credentials_worker = CredentialsWorker(
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

            host = self._get_ip_by_server_id(server_id)

            if not host:
                self.busy.stop()
                return

            try:
                ProtocolLauncher.open(protocol, username, password, host, port)
            except Exception as e:
                handle_system_error(None, e)

        def on_error(e: ApiError):
            self.error_occurred.emit(e)

        self._credentials_worker.finished.connect(self.busy.stop)
        self._credentials_worker.success.connect(on_success)
        self._credentials_worker.error.connect(on_error)
        self._credentials_worker.start()

    def _get_ip_by_server_id(self, server_id):
        for b in self._data:
            for s in b["servers"]:
                if s["id"] == server_id:
                    return s["ip"]
