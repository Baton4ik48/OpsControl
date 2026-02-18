from datetime import datetime, timezone

from PyQt6.QtCore import QObject, pyqtSignal

from controllers.port_check_manager import PortCheckManager
from controllers.load_tree_worker import LoadTreeWorker
from controllers.ssh_launcher import SshLauncher

from core.logger import get_logger
from core.api.base import ApiError

from ui.dialogs.credentials_dialog import CredentialsDialog
from ui.dialogs.workers.credentials_worker import CredentialsWorker

log = get_logger(__name__)

class TreeController(QObject):
    loaded = pyqtSignal()
    error_occurred = pyqtSignal(ApiError)

    def __init__(self, api, tree, user_settings, busy):
        super().__init__()
        self.api = api
        self.tree = tree
        self.user_settings = user_settings
        self.busy = busy    

        self._data = None
        self._runtime_status = {}
        self.checker = PortCheckManager(max_threads=10)
        self._worker = None

    # =========================
    # ЗАГРУЗКА ДЕРЕВА
    # =========================
    def start_load(self):
        self.busy.start("Загрузка топологии сети...")

        self._worker = LoadTreeWorker(self.api)
        self._worker.success.connect(self._on_loaded)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self.busy.stop)
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
    def refresh_all(self):
        if not self._data:
            return

        self.busy.start("Проверка портов…")

        self._pending_ports = 0

        servers = [s for b in self._data for s in b["servers"]]
        for s in servers:
            self._pending_ports += len(s["ports"])

        def on_checked(server_id, port, ok):
            self._on_port_checked(server_id, port, ok)
            self._pending_ports -= 1
            if self._pending_ports == 0:
                self.busy.stop()

        self.checker.check_ports(servers, on_checked, self.api)


    def _on_port_checked(self, server_id, port, ok):
        self._runtime_status[(server_id, port)] = ok

        self._update_port_status(server_id, port)

        self.tree.render(self._data)

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
                s for s in b["servers"]
                if any(p.get("is_up") is False for p in s["ports"])
            ]
            if bad:
                result.append({
                    "name": b["name"],
                    "servers": bad
                })

        self.tree.render(result)
    
    # =========================
    # Контекст меню
    # =========================

    def refresh_server(self, server_id: int, ip: str):
        for b in self._data:
            for s in b["servers"]:
                if s["id"] != server_id:
                    continue

                ports_count = len(s["ports"])
                if ports_count == 0:
                    return

                self.busy.start(f"Проверка доступности портов на сервере {ip}…")
                self._pending_ports = ports_count

                def on_checked(sid, port, ok):
                    self._on_port_checked(sid, port, ok)

                    self._pending_ports -= 1
                    if self._pending_ports == 0:
                        self.busy.stop()

                self.checker.check_ports(
                    [s],
                    on_checked,
                    self.api
                )
                return


    def refresh_port(self, server_id: int, port: int, ip: str):
        for b in self._data:
            for s in b["servers"]:
                if s["id"] != server_id:
                    continue

                for p in s["ports"]:
                    if p["port"] != port:
                        continue

                    self.busy.start(f"Проверка порта {port} сервера {ip}…")

                    def on_checked(sid, port, ok):
                        self._on_port_checked(sid, port, ok)
                        self.busy.stop()

                    self.checker.check_ports(
                        [{
                            "id": server_id,
                            "ip": s["ip"],
                            "ports": [p]
                        }],
                        on_checked,
                        self.api
                    )
                    return



    def open_ssh_terminal(self, server_id: int):
        for b in self._data:
            for s in b["servers"]:
                if s["id"] == server_id:
                    SshLauncher.open("user", s["ip"])
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
            master_password=master_password
        )

        def on_success(data):
            self.tree.show_credentials(
                server_id,
                port,
                data["username"],
                data["password"]
            )

        def on_error(e: ApiError):
            self.error_occurred.emit(e)

        self._credentials_worker.finished.connect(self.busy.stop)
        self._credentials_worker.success.connect(on_success)
        self._credentials_worker.error.connect(on_error)
        self._credentials_worker.start()









