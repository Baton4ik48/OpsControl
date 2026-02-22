from core.api.base import BaseApi


class CredentialsApi(BaseApi):

    def show(self, server_id: int, port: int, username: str, master_password: str):
        return self.post(
            "/api/credentials/show",
            json={
                "server_id": server_id,
                "port": port,
                "username": username,
                "master_password": master_password,
            }
        )
