from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit, QPushButton
from PyQt6.QtGui import QIntValidator
from PyQt6.QtCore import pyqtSignal


class PortForm(QWidget):
    saved = pyqtSignal(int, str)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        layout = QFormLayout(self)

        self.port_input = QLineEdit()
        self.port_input.setValidator(QIntValidator(1, 65535))

        self.vault_input = QLineEdit()

        layout.addRow("Порт:", self.port_input)
        layout.addRow("Vault path:", self.vault_input)

        self.save_btn = QPushButton("Сохранить")
        layout.addRow(self.save_btn)

        self.save_btn.clicked.connect(self._on_save)

    def set_data(self, data: dict):
        self.port_input.setText(str(data["port"]))
        self.vault_input.setText(data.get("vault_path", ""))

    def _on_save(self):
        if not self.port_input.text():
            self.error.emit("Введите номер порта")
            return

        port = int(self.port_input.text())
        vault = self.vault_input.text().strip()

        self.saved.emit(port, vault)