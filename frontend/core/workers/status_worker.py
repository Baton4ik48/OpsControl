from PyQt6.QtCore import QThread, pyqtSignal
from core.api.base import ApiError


class StatusWorker(QThread):
    success = pyqtSignal(dict)
    error = pyqtSignal(ApiError)

    def __init__(self, api):
        super().__init__()
        self.api = api

    def run(self):
        try:
            data = self.api.status.check()
            self.success.emit(data)

        except ApiError as e:
            self.error.emit(e)

        except Exception as e:
            raise
