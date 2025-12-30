#from core.port_checker import check_port
from controllers.port_check_manager import PortCheckManager

class TreeController:
    def __init__(self, api, tree):
        self.api = api
        self.tree = tree
        self._data = None
        self._runtime_status = {}
        self.checker = PortCheckManager(max_threads=10)

    def load(self):
        self._data = self.api.tree.load_tree()

        self._clear_runtime_status()
        self._apply_runtime_status()

        self.tree.render(self._data)

    def _clear_runtime_status(self):
        self._runtime_status.clear()

    def refresh_all(self):
        if not self._data:
            return

        servers = []
        for b in self._data:
            servers.extend(b["servers"])
        self.checker.check_ports(servers, self._on_port_checked)

    def _on_port_checked(self, server_id, port, ok):
        self._runtime_status[(server_id, port)] = ok
        self._apply_runtime_status()
        self.tree.render(self._data)

    # def _check_server_ports(self, server):
    #     ip = server["ip"]
    #     server_id = server["id"]

    #     for p in server["ports"]:
    #         port = p["port"]
    #         ok = check_port(ip, port)

    #         self._runtime_status[(server_id, port)] = ok

    def _apply_runtime_status(self):
        for branch in self._data:
            for server in branch["servers"]:
                sid = server["id"]

                for p in server["ports"]:
                    p["is_up"] = self._runtime_status.get(
                        (sid, p["port"])
                    )

    def show_all(self):
        if self._data:
            self.tree.render(self._data)

    def show_problem(self):
        if not self._data:
            return

        result = []

        for branch in self._data:
            bad_servers = []

            for server in branch["servers"]:
                for p in server["ports"]:
                    if p.get("is_up") is False:
                        bad_servers.append(server)
                        break

            if bad_servers:
                result.append({
                    "name": branch["name"],
                    "servers": bad_servers
                })

        self.tree.render(result)