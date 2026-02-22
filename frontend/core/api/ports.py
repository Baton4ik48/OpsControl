from core.api.base import BaseApi

class PortApi(BaseApi):

    def get_by_server(self, server_id: int):
        return self.get(f"/api/ports/by-server/{server_id}")

    def create(self, server_id: int, port: int):
        return self.post(
            f"/api/ports/{server_id}/{port}"
        )

    def update_port(self, server_id: int, old_port: int, new_port: int):
        return self.put(
            f"/api/ports/{server_id}/{old_port}",
            json={
                "new_port": new_port
            }
        )

    def update_vault_path(self, server_id: int, port: int, vault_path: str):
        return self.put(
            f"/api/ports/{server_id}/{port}/vault-path",
            json={
                "vault_path": vault_path
            }
        )

    def report_result(self, server_id: int, port: int, ok: bool):
        return self.post(
            f"/api/ports/{server_id}/{port}/result",
            json={
                "ok": ok
            }
        )
    
    def delete_port(self, server_id: int, port: int):
        return self.delete(f"/api/ports/{server_id}/{port}")
    
    def delete_credentials(self, server_id: int, port: int):
        return self.delete(f"/api/ports/{server_id}/{port}/credentials")