import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIcon

from core.paths import ICONS_DIR


class CredentialsDialog(QDialog):
    submitted = pyqtSignal(str)

    def __init__(self, ip: str, port: int):
        super().__init__()

        self.setWindowTitle(f"Учётные данные {ip}:{port}")
        self.setModal(True)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Введите пароль администратора:"))

        self.admin_input = QLineEdit()
        self.admin_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.admin_input)

        self.show_btn = QPushButton("Показать")
        self.show_btn.clicked.connect(self._on_submit)
        layout.addWidget(self.show_btn)

    def _on_submit(self):
        password = self.admin_input.text().strip()
        if not password:
            QMessageBox.warning(self, "Ошибка", "Введите пароль администратора")
            return

        self.submitted.emit(password)
        self.accept()

