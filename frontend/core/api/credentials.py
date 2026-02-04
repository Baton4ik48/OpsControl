from core.api.base import BaseApi


class CredentialsApi(BaseApi):
    def show(self, server_id: int, port: int, username: str, master_password: str):
        print(
            "[API] POST /api/credentials/show",
            f"server_id={server_id}",
            f"port={port}",
            f"username={username}"
        )
        return self.post(
            "/api/credentials/show",
            json={
                "server_id": server_id,
                "port": port,
                "username": username,
                "master_password": master_password,
            }
        )
