from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton
from PyQt6.QtGui import QFont


class DiagnosticsResultDialog(QDialog):
    """Показывает текстовый результат одной диагностической команды."""

    def __init__(self, title: str, output: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(title))

        text_area = QPlainTextEdit()
        text_area.setReadOnly(True)
        text_area.setPlainText(output or "(пустой вывод)")
        text_area.setFont(QFont("Monospace"))
        layout.addWidget(text_area)

        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
