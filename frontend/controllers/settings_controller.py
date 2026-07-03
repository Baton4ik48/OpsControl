from PyQt6.QtCore import QObject, pyqtSignal
from core.workers.status_worker import StatusWorker


class SettingsController(QObject):
    status_changed = pyqtSignal(str)

    def __init__(self, api):
        super().__init__()
        self.api = api
        # Ссылки на живые воркеры — защита от уничтожения работающего QThread
        self._workers: set = set()

    def check_backend_status(self):
        worker = StatusWorker(self.api)
        worker.success.connect(self._on_success)
        worker.error.connect(self._on_error)
        self._workers.add(worker)
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        worker.start()

    def _on_success(self, data: dict):
        if not data.get("success"):
            self.status_changed.emit("backend_offline")
            return

        status = data.get("data", {}).get("status", "unknown")
        self.status_changed.emit(status)

    def _on_error(self, _):
        self.status_changed.emit("backend_offline")
