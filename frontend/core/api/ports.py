from core.api.base import BaseApi

class PortApi(BaseApi):
    def get_by_server(self, server_id: int):
        return self.get(f"/api/servers/{server_id}/ports")

    def report_result(self, server_id: int, port: int, ok: bool):
        self.post(
            "/api/ports/result",
            params={
                "server_id": server_id,
                "port": port,
                "ok": ok
            }
        )

    def create(self, server_id: int, port: int, protocol="tcp"):
        return self.post(
            "/api/ports",
            params={
                "server_id": server_id,
                "port": port,
                "protocol": protocol
            }
        )

    def delete_port(self, server_id: int, port: int):
        return super().delete(f"/api/ports/{server_id}/{port}")
    
    def update_port(self, server_id: int, old_port: int, new_port: int):
        return self.put(
            "/api/ports",
            params={
                "server_id": server_id,
                "old_port": old_port,
                "new_port": new_port
            }
        )