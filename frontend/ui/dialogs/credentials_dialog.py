import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIcon

from core.paths import ICONS_DIR
from core.api.base import ApiError
from core.error_handler import handle_api_error

class CredentialsDialog(QDialog):
    credentials_received = pyqtSignal(str, str)

    def __init__(self, api, server_id, port, ip, username):
        super().__init__()

        self.api = api
        self.server_id = server_id
        self.port = port
        self.ip = ip
        self.username = username

        self.setWindowIcon(QIcon(os.path.join(ICONS_DIR, "show_icon.png")))
        self.setWindowTitle(f"Учётные данные {ip}:{port}")
        self.setModal(True)
        self.resize(360, 240)

        layout = QVBoxLayout(self)

        # ---- ввод admin-пароля ----
        layout.addWidget(QLabel("Введите пароль администратора:"))

        self.admin_input = QLineEdit()
        self.admin_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.admin_input)

        self.show_btn = QPushButton("Показать")
        self.show_btn.clicked.connect(self._on_submit)
        layout.addWidget(self.show_btn)

        # ---- результат ----
        self.result_label = QLabel("")
        self.result_label.setTextInteractionFlags(
            self.result_label.textInteractionFlags()
            | self.result_label.textInteractionFlags().TextSelectableByMouse
        )
        layout.addWidget(self.result_label)

    # ==================================
    # SUBMIT
    # ==================================

    def _on_submit(self):
        master_password = self.admin_input.text().strip()

        if not master_password:
            QMessageBox.warning(self, "Ошибка", "Введите пароль администратора")
            return

        try:
            data = self.api.credentials.show(
                server_id=self.server_id,
                port=self.port,
                username=self.username,
                master_password=master_password
            )
        except ApiError as e:
            handle_api_error(self, e)
            return

        self.credentials_received.emit(
            data["username"],
            data["password"]
        )
        self.accept()

