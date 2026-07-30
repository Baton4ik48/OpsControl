from PyQt6.QtCore import QThread, pyqtSignal

from core.utils.secure import wipe
from core.ssh.diagnostics import run_check


class DiagnosticsWorker(QThread):
    """
    stage передаётся вместе с исключением ("verify"/"ssh"), т.к. первое —
    всегда ApiError (нужен error_occurred/handle_api_error для 403/429 и т.п.),
    а второе — SSHRotateError/сетевые ошибки (нужен generic system_error).
    """

    success = pyqtSignal(str)
    error = pyqtSignal(str, object)  # stage, exception

    def __init__(self, api, server_id, port, ip, username, master_password, command):
        super().__init__()
        self.api = api
        self.server_id = server_id
        self.port = port
        self.ip = ip
        self.username = username
        self.master_password = master_password
        self.command = command

    def run(self):
        try:
            creds = self.api.credentials.show(
                server_id=self.server_id,
                port=self.port,
                username=self.username,
                master_password=self.master_password,
            )
        except Exception as e:
            self.error.emit("verify", e)
            return
        finally:
            wipe(self.master_password)
            self.master_password = ""

        try:
            output = run_check(
                self.ip, self.port, creds["username"], creds["password"], self.command
            )
        except Exception as e:
            self.error.emit("ssh", e)
            return
        finally:
            del creds

        self.success.emit(output)
