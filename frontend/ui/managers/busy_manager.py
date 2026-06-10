from PyQt6.QtCore import QObject, pyqtSignal

class BusyManager(QObject):
    started = pyqtSignal(str)
    finished = pyqtSignal()

    def start(self, message: str):
        self.started.emit(message)

    def stop(self):
        self.finished.emit()
