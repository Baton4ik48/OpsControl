from core.api.base import BaseApi

class ServerApi(BaseApi):
    def get_by_branch(self, branch_id: int):
        return self.get(f"/api/branches/{branch_id}/servers")

    def update_name(self, server_id: int, new_name: str):
        self.put(f"/api/servers/{server_id}/name", params={"new_name": new_name})

    def update_ip(self, server_id: int, new_ip: str):
        self.put(f"/api/servers/{server_id}/ip", params={"new_ip": new_ip})
