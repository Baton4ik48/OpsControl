from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt


class BusyOverlay(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("BusyOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel("Загрузка…")
        self.label.setObjectName("BusyOverlayLabel")

        layout.addWidget(self.label)

    def show_message(self, message: str):
        self.label.setText(message)

        if self.parent():
            self.resize(self.parent().size())

        self.show()
        self.raise_()

    def hide_overlay(self):
        self.hide()
