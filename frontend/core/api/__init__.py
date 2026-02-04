from core.api.branches import BranchApi
from core.api.servers import ServerApi
from core.api.ports import PortApi
from core.api.tree import TreeApi
from core.api.credentials import CredentialsApi


class ApiClient:
    def __init__(self):
        self.branches = BranchApi()
        self.servers = ServerApi()
        self.ports = PortApi()
        self.tree = TreeApi()
        self.credentials = CredentialsApi()
