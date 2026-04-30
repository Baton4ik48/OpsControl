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
            },
        )

    def verify_admin(self, username: str, master_password: str):
        return self.post(
            "/api/credentials/verify-admin",
            json={
                "username": username,
                "master_password": master_password,
            },
        )

    def upsert(self, server_id: int, port: int, username: str, password: str):
        return self.post(
            "/api/credentials/upsert",
            json={
                "server_id": server_id,
                "port": port,
                "username": username,
                "password": password,
            },
        )

    def rotate(
        self,
        server_id: int,
        ssh_port: int,
        new_password: str,
        username: str,
        master_password: str,
        mnemonic: str = "",
    ):
        return self.post(
            "/api/credentials/rotate",
            json={
                "server_id": server_id,
                "ssh_port": ssh_port,
                "new_password": new_password,
                "username": username,
                "master_password": master_password,
                "mnemonic": mnemonic,
            },
        )

    def export_all(self, username: str, master_password: str):
        return self.post(
            "/api/credentials/export-all",
            json={"username": username, "master_password": master_password},
        )
