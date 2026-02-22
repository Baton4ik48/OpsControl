from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit, QPushButton
from PyQt6.QtCore import pyqtSignal
import ipaddress


class ServerForm(QWidget):
    saved = pyqtSignal(str, str)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Например: 192.168.0.1")

        layout.addRow("Название:", self.name_input)
        layout.addRow("IP:", self.ip_input)

        self.save_btn = QPushButton("Сохранить")
        layout.addRow(self.save_btn)

        self.save_btn.clicked.connect(self._on_save)

    def set_data(self, data: dict):
        self.name_input.setText(data["name"])
        self.ip_input.setText(data["ip"])

    def _on_save(self):
        name = self.name_input.text().strip()
        ip = self.ip_input.text().strip()

        if not name:
            self.error.emit("Название сервера не может быть пустым")
            return

        try:
            ipaddress.ip_address(ip)
        except ValueError:
            self.error.emit("Введите корректный IP-адрес")
            return

        self.saved.emit(name, ip)