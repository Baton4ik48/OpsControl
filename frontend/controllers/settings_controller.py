from PyQt6.QtCore import QObject, pyqtSignal
from controllers.status_worker import StatusWorker


class SettingsController(QObject):
    status_changed = pyqtSignal(str)

    def __init__(self, api):
        super().__init__()
        self.api = api

    def check_backend_status(self):
        self._worker = StatusWorker(self.api)
        self._worker.success.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_success(self, data: dict):
        status = data.get("status", "unknown")
        self.status_changed.emit(status)

    def _on_error(self, _):
        self.status_changed.emit("offline")
