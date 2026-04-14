from core.api.base import BaseApi

class ServerApi(BaseApi):

    def get_by_branch(self, branch_id: int):
        return self.get(f"/api/servers/by-branch/{branch_id}")

    def create(self, branch_id: int, name: str, ip: str, device_type: str = "linux"):
        return self.post(
            "/api/servers",
            json={
                "branch_id": branch_id,
                "name": name,
                "ip": ip,
                "device_type": device_type,
            }
        )

    def update(self, server_id: int, name: str, ip: str, device_type: str = "linux"):
        return self.put(
            f"/api/servers/{server_id}",
            json={
                "name": name,
                "ip": ip,
                "device_type": device_type,
            }
        )

    def delete_server(self, server_id: int):
        return self.delete(f"/api/servers/{server_id}")