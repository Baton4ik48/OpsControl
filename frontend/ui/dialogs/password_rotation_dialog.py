import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QHBoxLayout, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from core.paths import ICONS_DIR
from core.api.credentials import CredentialsApi
from core.api.base import ApiError
from core.password_generator import generate_password


class PasswordRotationDialog(QDialog):
    def __init__(self, server_id: int, host: str, admin_login: str, parent=None):
        super().__init__(parent)

        self.server_id = server_id
        self.host = host
        self.admin_login = admin_login
        self._api = CredentialsApi()

        self.setWindowTitle(f"Смена пароля — {host}")
        self.setWindowIcon(QIcon(os.path.join(ICONS_DIR, "key_icon.png")))
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Подсказка
        hint = QLabel(f"Сервер: <b>{host}</b>  ·  Порт: <b>22</b>")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setObjectName("settingsDescription")
        layout.addWidget(hint)

        form = QFormLayout()
        form.setContentsMargins(0, 8, 0, 4)

        # Мастер-пароль
        self.master_input = QLineEdit()
        self.master_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.master_input.setPlaceholderText("Мастер-пароль администратора")
        form.addRow("Мастер-пароль:", self.master_input)

        # Новый пароль
        new_pass_row = QHBoxLayout()
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("Новый пароль")

        btn_generate = QPushButton("Сгенерировать")
        btn_generate.setFixedWidth(120)
        btn_generate.clicked.connect(self._generate)

        new_pass_row.addWidget(self.new_password_input)
        new_pass_row.addWidget(btn_generate)
        form.addRow("Новый пароль:", new_pass_row)

        # Мнемоника
        self.mnemonic_label = QLabel("—")
        self.mnemonic_label.setObjectName("settingsDescription")
        self.mnemonic_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        form.addRow("Подсказка:", self.mnemonic_label)

        layout.addLayout(form)

        # Кнопки
        buttons = QHBoxLayout()
        self.apply_btn = QPushButton("Применить")
        btn_cancel = QPushButton("Отмена")

        self.apply_btn.clicked.connect(self._on_apply)
        btn_cancel.clicked.connect(self.reject)

        buttons.addStretch()
        buttons.addWidget(self.apply_btn)
        buttons.addWidget(btn_cancel)
        layout.addLayout(buttons)

        # Сразу генерируем пароль
        self._generate()

    def _generate(self):
        password, mnemonic = generate_password(length=16, min_digits=4)
        self.new_password_input.setText(password)
        self.mnemonic_label.setText(mnemonic)

    def _on_apply(self):
        master = self.master_input.text().strip()
        new_pass = self.new_password_input.text().strip()

        if not master:
            QMessageBox.warning(self, "Ошибка", "Введите мастер-пароль")
            return

        if not new_pass:
            QMessageBox.warning(self, "Ошибка", "Новый пароль не может быть пустым")
            return

        self.apply_btn.setEnabled(False)
        self.apply_btn.setText("Выполняется...")

        try:
            self._api.rotate(
                server_id=self.server_id,
                host=self.host,
                ssh_port=22,
                new_password=new_pass,
                username=self.admin_login,
                master_password=master,
            )
            QMessageBox.information(
                self,
                "Готово",
                f"Пароль успешно изменён на сервере {self.host}\n\n"
                f"Запомните подсказку: {self.mnemonic_label.text()}"
            )
            self.accept()

        except ApiError as e:
            if e.status_code == 403:
                QMessageBox.warning(self, "Ошибка", "Неверный мастер-пароль")
            elif e.status_code == 429:
                QMessageBox.warning(self, "Заблокировано", f"Попробуйте через {e.retry_after} сек.")
            elif e.status_code == 422:
                QMessageBox.critical(self, "Ошибка ротации", e.message)
            else:
                QMessageBox.critical(self, "Ошибка", e.message)

            self.apply_btn.setEnabled(True)
            self.apply_btn.setText("Применить")
