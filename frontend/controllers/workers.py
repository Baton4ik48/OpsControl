from PyQt6.QtCore import QObject, QRunnable, pyqtSignal
from core.port_checker import check_port


class PortCheckSignals(QObject):
    result = pyqtSignal(int, int, bool)  
    # server_id, port, ok


class PortCheckTask(QRunnable):
    def __init__(self, server_id, ip, port):
        super().__init__()
        self.server_id = server_id
        self.ip = ip
        self.port = port
        self.signals = PortCheckSignals()

    def run(self):
        ok = check_port(self.ip, self.port)
        self.signals.result.emit(self.server_id, self.port, ok)


