from PyQt6.QtCore import QThread, pyqtSignal


class InfrastructureWorker(QThread):
    success = pyqtSignal(object)
    error = pyqtSignal(Exception)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.success.emit(result)
        except Exception as e:
            self.error.emit(e)
