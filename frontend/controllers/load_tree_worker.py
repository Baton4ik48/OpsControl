from PyQt6.QtCore import QThread, pyqtSignal


class LoadTreeWorker(QThread):
    success = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api):
        super().__init__()
        self.api = api

    def run(self):
        try:
            data = self.api.tree.load_tree()
            self.success.emit(data)
        except Exception as e:
            self.error.emit(str(e))
