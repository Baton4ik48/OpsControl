from PyQt6.QtCore import QObject, QRunnable, pyqtSignal
from core.port_checker import check_port


class PortCheckSignals(QObject):
    result = pyqtSignal(int, int, bool)


class PortCheckWorker(QRunnable):
    def __init__(self, server_id, ip, port, api):
        super().__init__()
        self.server_id = server_id
        self.ip = ip
        self.port = port
        self.api = api
        self.signals = PortCheckSignals()

    def run(self):
        ok = check_port(self.ip, self.port)
        try:
            self.api.ports.report_result(self.server_id, self.port, ok)
        except Exception:
            pass
        self.signals.result.emit(self.server_id, self.port, ok)
