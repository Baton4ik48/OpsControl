from core.workers.function_worker import FunctionWorker


class InfrastructureController:

    def __init__(self, view, busy, api):
        self.view = view
        self.busy = busy

        self.tree_api = api.tree
        self.server_api = api.servers
        self.branch_api = api.branches
        self.port_api = api.ports

        self.current_branch_id = None
        self.current_server_id = None
        self.current_port = None
        self.cached_tree_data = None

        # Ссылки на живые воркеры: перезапись единственного атрибута
        # уничтожала работающий QThread
        self._workers: set = set()

    def _launch(self, worker):
        self._workers.add(worker)
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        worker.start()

    def _run_task(self, message, fn):
        self.busy.show_message(message)

        worker = FunctionWorker(fn)
        worker.success.connect(self._on_success)
        worker.error.connect(self._on_error)
        worker.finished.connect(self.busy.hide_overlay)
        self._launch(worker)

    def _on_success(self, _=None):
        self.load_tree_async()

    def _on_error(self, e):
        self.view.show_error(str(e))

    def load_tree_async(self):

        def task():
            return self.tree_api.load_tree()

        self.busy.show_message("Загрузка инфраструктуры…")

        worker = FunctionWorker(task)
        worker.success.connect(self._on_tree_loaded)
        worker.error.connect(self._on_error)
        worker.finished.connect(self.busy.hide_overlay)
        self._launch(worker)

    def _on_tree_loaded(self, data):
        self.cached_tree_data = data
        self.view.render_tree(data)

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
