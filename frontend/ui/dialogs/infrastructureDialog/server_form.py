import ipaddress
import re

from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit, QPushButton, QComboBox
from PyQt6.QtCore import pyqtSignal

# метка домена: буквы, цифры, дефис (не в начале/конце), 1–63 символа
_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)


def is_valid_host(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        pass
    return bool(_DOMAIN_RE.match(value))


DEVICE_TYPES = [
    ("Linux-сервер", "linux"),
    ("Windows-сервер", "windows"),
    ("Коммутатор Nateks", "nateks"),
    ("Коммутатор Cisco", "cisco"),
]


class ServerForm(QWidget):
    saved = pyqtSignal(str, str, str)  # name, ip, device_type
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Например: 192.168.0.1 или server.example.ru")

        self.device_type_combo = QComboBox()
        for label, value in DEVICE_TYPES:
            self.device_type_combo.addItem(label, userData=value)

        layout.addRow("Название:", self.name_input)
        layout.addRow("IP / Домен:", self.ip_input)
        layout.addRow("Тип устройства:", self.device_type_combo)

        self.save_btn = QPushButton("Сохранить")
        layout.addRow(self.save_btn)

        self.save_btn.clicked.connect(self._on_save)

    def set_data(self, data: dict):
        self.name_input.setText(data["name"])
        self.ip_input.setText(data["ip"])

        device_type = data.get("device_type", "linux")
        for i, (_, value) in enumerate(DEVICE_TYPES):
            if value == device_type:
                self.device_type_combo.setCurrentIndex(i)
                break

    def _on_save(self):
        name = self.name_input.text().strip()
        host = self.ip_input.text().strip()
        device_type = self.device_type_combo.currentData()

        if not name:
            self.error.emit("Название сервера не может быть пустым")
            return

        if not is_valid_host(host):
            self.error.emit("Введите корректный IP-адрес или доменное имя")
            return

        self.saved.emit(name, host, device_type)
