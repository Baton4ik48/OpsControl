from core.api.base import BaseApi

class PortApi(BaseApi):
    def get_by_server(self, server_id: int):
        return self.get(f"/api/servers/{server_id}/ports")

