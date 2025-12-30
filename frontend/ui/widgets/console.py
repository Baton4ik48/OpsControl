from PyQt6.QtWidgets import QPlainTextEdit

class Console(QPlainTextEdit):
    def log(self, text):
        self.appendPlainText(text)
