from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QHBoxLayout, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
import os

from core.paths import ICONS_DIR
from core.api.credentials import CredentialsApi
from core.api.base import ApiError


class CredentialEditDialog(QDialog):
    def __init__(self, server_id: int, port: int, parent=None):
        super().__init__(parent)

        self.server_id = server_id
        self.port = port
        self._api = CredentialsApi()

        self.setWindowTitle(f"Учётные данные — порт {port}")
        self.setWindowIcon(QIcon(os.path.join(ICONS_DIR, "key_icon.png")))
        self.setModal(True)
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)

        hint = QLabel(f"Сервер ID: {server_id}  ·  Порт: {port}")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setObjectName("settingsDescription")
        layout.addWidget(hint)

        form = QFormLayout()
        form.setContentsMargins(0, 8, 0, 8)

        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Логин:", self.username_input)
        form.addRow("Пароль:", self.password_input)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        btn_cancel = QPushButton("Отмена")

        self.save_btn.clicked.connect(self._on_save)
        btn_cancel.clicked.connect(self.reject)

        buttons.addStretch()
        buttons.addWidget(self.save_btn)
        buttons.addWidget(btn_cancel)
        layout.addLayout(buttons)

    def _on_save(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните логин и пароль")
            return

        self.save_btn.setEnabled(False)
        self.save_btn.setText("Сохранение...")

        try:
            self._api.upsert(
                server_id=self.server_id,
                port=self.port,
                username=username,
                password=password,
            )
            self.accept()

        except ApiError as e:
            QMessageBox.critical(self, "Ошибка", e.message)
            self.save_btn.setEnabled(True)
            self.save_btn.setText("Сохранить")
