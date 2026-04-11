import os

from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit,
    QPushButton, QHBoxLayout
)
from PyQt6.QtGui import QIntValidator, QIcon
from PyQt6.QtCore import pyqtSignal

from core.paths import ICONS_DIR
from ui.dialogs.infrastructureDialog.credential_edit_dialog import CredentialEditDialog


class PortForm(QWidget):
    saved = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self._server_id = None
        self._current_port = None

        layout = QFormLayout(self)

        self.port_input = QLineEdit()
        self.port_input.setValidator(QIntValidator(1, 65535))

        # vault_path — read-only, рядом кнопка-ключ
        vault_row = QHBoxLayout()
        self.vault_label = QLineEdit()
        self.vault_label.setReadOnly(True)
        self.vault_label.setPlaceholderText("не задан")
        self.vault_label.setObjectName("vaultPathLabel")

        self.key_btn = QPushButton()
        self.key_btn.setIcon(QIcon(os.path.join(ICONS_DIR, "key_icon.png")))
        self.key_btn.setFixedSize(28, 28)
        self.key_btn.setToolTip("Задать / изменить учётные данные")
        self.key_btn.clicked.connect(self._open_credential_editor)

        vault_row.addWidget(self.vault_label)
        vault_row.addWidget(self.key_btn)

        layout.addRow("Порт:", self.port_input)
        layout.addRow("Vault path:", vault_row)

        self.save_btn = QPushButton("Сохранить")
        layout.addRow(self.save_btn)

        self.save_btn.clicked.connect(self._on_save)

    def set_data(self, server_id: int, data: dict):
        self._server_id = server_id
        self._current_port = data["port"]

        self.port_input.setText(str(data["port"]))
        self.vault_label.setText(data.get("vault_path") or "")

    def _open_credential_editor(self):
        if not self._server_id or not self._current_port:
            self.error.emit("Сначала выберите порт")
            return

        dlg = CredentialEditDialog(
            server_id=self._server_id,
            port=self._current_port,
            parent=self,
        )
        if dlg.exec():
            # vault_path сгенерирован бэкендом — обновим лейбл
            self.vault_label.setText(
                f"credentials/servers/{self._server_id}/{self._current_port}"
            )

    def _on_save(self):
        if not self.port_input.text():
            self.error.emit("Введите номер порта")
            return

        port = int(self.port_input.text())
        self.saved.emit(port)
