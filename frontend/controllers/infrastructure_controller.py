from core.api.tree import TreeApi
from core.api.servers import ServerApi
from core.api.ports import PortApi
from core.api.branches import BranchApi
from core.api.base import ApiError

from core.workers.infrastructure_worker import InfrastructureWorker


class InfrastructureController:

    def __init__(self, view, busy):
        self.view = view
        self.busy = busy

        self.tree_api = TreeApi()
        self.server_api = ServerApi()
        self.branch_api = BranchApi()
        self.port_api = PortApi()

        self.current_branch_id = None
        self.current_server_id = None
        self.current_port = None
        self.cached_tree_data = None

        self._worker = None

    # =========================================================
    # Универсальный запуск worker
    # =========================================================

    def _run_task(self, message, fn):
        self.busy.show_message(message)

        self._worker = InfrastructureWorker(fn)
        self._worker.success.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self.busy.hide_overlay)
        self._worker.start()

    def _on_success(self, _=None):
        self.load_tree()

    def _on_error(self, e):
        self.view.show_error(str(e))

    def load_tree_async(self):

        def task():
            return self.tree_api.load_tree()

        self.busy.show_message("Загрузка инфраструктуры…")

        self._worker = InfrastructureWorker(task)
        self._worker.success.connect(self._on_tree_loaded)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self.busy.hide_overlay)
        self._worker.start()

    def _on_tree_loaded(self, data):
        self.cached_tree_data = data
        self.view.render_tree(data)

    # =========================================================
    # LOAD TREE
    # =========================================================

    def load_tree(self):
        try:
            data = self.tree_api.load_tree()
            self.cached_tree_data = data
            self.view.render_tree(data)
        except ApiError as e:
            self.view.show_api_error(e.message)

    # =========================================================
    # SERVER
    # =========================================================

    def select_server(self, server_id, server_data):
        self.current_server_id = server_id
        self.current_port = None
        self.view.show_server_form(server_data)

    def save_server(self, name, ip, device_type="linux"):
        def task():
            self.server_api.update(
                self.current_server_id,
                name,
                ip,
                device_type,
            )

        self._run_task("Сохранение сервера…", task)

    # =========================================================
    # PORT
    # =========================================================

    def select_port(self, server_id, port_data):
        self.current_server_id = server_id
        self.current_port = port_data["port"]
        self.view.show_port_form(server_id, port_data)

    def save_port(self, new_port):

        def task():
            if new_port != self.current_port:
                self.port_api.update_port(
                    self.current_server_id, self.current_port, new_port
                )
                self.current_port = new_port

        self._run_task("Сохранение порта…", task)

    # =========================================================
    # BRANCH
    # =========================================================

    def create_branch(self, name):
        def task():
            self.branch_api.create(name)

        self._run_task("Создание филиала…", task)

    def select_branch(self, branch_id):
        self.current_branch_id = branch_id

        for branch in self.cached_tree_data:
            if branch["id"] == branch_id:
                self.view.show_branch_form(branch)
                break

    def save_branch(self, name):
        def task():
            self.branch_api.update_branch(self.current_branch_id, name)

        self._run_task("Сохранение филиала…", task)

    def create_server(self, branch_id, name, ip):
        def task():
            self.server_api.create(branch_id, name, ip)

        self._run_task("Создание сервера…", task)

    def create_port(self, server_id, port):
        def task():
            self.port_api.create(server_id, port)

        self._run_task("Создание порта…", task)

    # =========================================================
    # DELETE
    # =========================================================

    def delete_branch(self, branch_id):
        def task():
            self.branch_api.delete_branch(branch_id)

        self.current_branch_id = None
        self.current_server_id = None
        self.current_port = None

        self._run_task("Удаление филиала…", task)

    def delete_server(self, server_id):
        def task():
            self.server_api.delete_server(server_id)

        self.current_server_id = None
        self.current_port = None

        self._run_task("Удаление сервера…", task)

    def delete_port(self, server_id, port):
        def task():
            self.port_api.delete_port(server_id, port)

        self.current_port = None

        self._run_task("Удаление порта…", task)
