from controllers.port_check_manager import PortCheckManager
from controllers.load_tree_worker import LoadTreeWorker
from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime, timezone
from controllers.ssh_launcher import SshLauncher
from ui.dialogs.credentials_dialog import CredentialsDialog
from core.api.base import ApiError

class TreeController(QObject):
    loaded = pyqtSignal()
    load_failed = pyqtSignal(ApiError)

    def __init__(self, api, tree, user_settings):
        super().__init__()
        self.api = api
        self.tree = tree
        self.user_settings = user_settings

        self._data = None
        self._runtime_status = {}
        self.checker = PortCheckManager(max_threads=10)
        self._worker = None


    # =========================
    # ЗАГРУЗКА ДЕРЕВА
    # =========================
    def start_load(self):
        self._worker = LoadTreeWorker(self.api)
        self._worker.success.connect(self._on_loaded)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_loaded(self, data):
        self._data = data
        self._runtime_status.clear()
        self.tree.render(self._data)
        self.loaded.emit()

    def _on_error(self, message):
        self.load_failed.emit(
            ApiError(message, status_code=None)
        )

    # =========================
    # ПРОВЕРКА ПОРТОВ
    # =========================
    def refresh_all(self):
        if not self._data:
            return

        servers = [
            s
            for b in self._data
            for s in b["servers"]
        ]

        self.checker.check_ports(
            servers,
            self._on_port_checked,
            self.api
        )

    def _on_port_checked(self, server_id, port, ok):
        self._runtime_status[(server_id, port)] = ok

        # обновляем ТОЛЬКО нужный порт
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

    def refresh_server(self, server_id: int):
        for b in self._data:
            for s in b["servers"]:
                if s["id"] == server_id:
                    self.checker.check_ports(
                        [s],
                        self._on_port_checked,
                        self.api
                    )
                    return

    def refresh_port(self, server_id: int, port: int):
        for b in self._data:
            for s in b["servers"]:
                if s["id"] == server_id:
                    for p in s["ports"]:
                        if p["port"] == port:
                            self.checker.check_ports(
                                [{
                                    "id": server_id,
                                    "ip": s["ip"],
                                    "ports": [p]
                                }],
                                self._on_port_checked,
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
        admin_login = self.user_settings.get("admin_login")

        dlg = CredentialsDialog(
            api=self.api,
            server_id=server_id,
            port=port,
            ip=ip,
            username=admin_login
        )
        dlg.exec()



