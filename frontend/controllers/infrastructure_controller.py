from core.api.tree import TreeApi
from core.api.servers import ServerApi
from core.api.credentials import CredentialsApi
from core.api.ports import PortApi
from core.api.branches import BranchApi
from core.api.base import ApiError


class InfrastructureController:
    def __init__(self, view):
        self.view = view

        self.tree_api = TreeApi()
        self.server_api = ServerApi()
        self.credentials_api = CredentialsApi()
        self.branch_api = BranchApi()
        self.port_api = PortApi()

        self.current_branch_id = None
        self.current_server_id = None
        self.current_port = None
        self.cached_tree_data = None

    # ==============================
    # LOAD TREE
    # ==============================

    def load_tree(self):
        try:
            data = self.tree_api.load_tree()
            self.cached_tree_data = data
            self.view.render_tree(data)
        except ApiError as e:
            self.view.show_api_error(e.message)
        except Exception as e:
            self.view.show_error(str(e))

    # ==============================
    # SERVER
    # ==============================

    def select_server(self, server_id, server_data):
        self.current_server_id = server_id
        self.current_port = None
        self.view.show_server_form(server_data)

    def save_server(self, name, ip):
        try:
            self.server_api.update_name(self.current_server_id, name)
            self.server_api.update_ip(self.current_server_id, ip)
            self.load_tree()
        except ApiError as e:
            self.view.show_api_error(e.message)

    # ==============================
    # PORT
    # ==============================

    def select_port(self, server_id, port_data):
        self.current_server_id = server_id
        self.current_port = port_data["port"]
        self.view.show_port_form(port_data)

    def save_port(self, new_port, vault_path):
        try:
            if new_port != self.current_port:
                self.port_api.update_port(
                    self.current_server_id,
                    self.current_port,
                    new_port
                )
                self.current_port = new_port

            self.credentials_api.update_vault_path(
                self.current_server_id,
                self.current_port,
                vault_path
            )

            self.load_tree()

        except ApiError as e:
            self.view.show_api_error(e.message)

    # ==============================
    # BRANCH
    # ==============================

    def select_branch(self, branch_id):
        self.current_branch_id = branch_id

        for branch in self.cached_tree_data:
            if branch["id"] == branch_id:
                self.view.show_branch_form(branch)
                break

    def save_branch(self, name):
        try:
            self.branch_api.update_branch(
                self.current_branch_id,
                name
            )
            self.load_tree()
        except ApiError as e:
            self.view.show_api_error(e.message)