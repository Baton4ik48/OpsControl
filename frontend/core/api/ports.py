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
