from PyQt6.QtCore import QThread, pyqtSignal
from core.ssh_rotate_linux import _wipe


class CredentialsWorker(QThread):
    success = pyqtSignal(dict)
    error = pyqtSignal(Exception)

    def __init__(self, api, server_id, port, username, master_password):
        super().__init__()
        self.api = api
        self.server_id = server_id
        self.port = port
        self.username = username
        self.master_password = master_password

    def run(self):
        try:
            data = self.api.credentials.show(
                server_id=self.server_id,
                port=self.port,
                username=self.username,
                master_password=self.master_password,
            )
        except Exception as e:
            self.error.emit(e)
            return
        finally:
            # Перезаписываем мастер-пароль нулями сразу после запроса
            _wipe(self.master_password)
            self.master_password = ""

        self.success.emit(data)
