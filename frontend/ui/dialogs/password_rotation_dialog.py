import os
import re

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSpacerItem,
    QSizePolicy,
    QTabWidget,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from core.paths import ICONS_DIR
from core.api.credentials import CredentialsApi
from core.api.base import ApiError
from core.password_generator import generate_password
from core.config.user_settings import UserSettings
from core.ssh_rotate_linux import rotate_linux_password, SSHRotateError, _wipe
from core.ssh_rotate_nateks import rotate_nateks_password
from core.ssh_rotate_cisco import rotate_cisco_password

_ROTATE_FN = {
    "linux": rotate_linux_password,
    "nateks": rotate_nateks_password,
    "natex": rotate_nateks_password,  # backward compat для старых записей в БД
    "cisco": rotate_cisco_password,
}


class PasswordRotationDialog(QDialog):
    def __init__(
        self,
        server_id: int,
        host: str,
        admin_login: str,
        device_type: str = "linux",
        parent=None,
    ):
        super().__init__(parent)

        self.server_id = server_id
        self.host = host
        self._rotate_fn = _ROTATE_FN.get(device_type, rotate_linux_password)
        self.admin_login = admin_login
        self._api = CredentialsApi()

        self.setWindowTitle(f"Смена пароля — {host}")
        self.setWindowIcon(QIcon(os.path.join(ICONS_DIR, "key_icon.png")))
        self.setModal(True)

        layout = QVBoxLayout(self)

        # ── Шапка ──────────────────────────────────────────────
        header = QLabel(f"Сервер: <b>{host}</b>  ·  Порт: <b>22</b>")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setObjectName("settingsDescription")
        layout.addWidget(header)

        # ── Мастер-пароль (общий для обеих вкладок) ────────────
        master_form = QFormLayout()
        master_form.setContentsMargins(0, 6, 0, 4)
        self.master_input = QLineEdit()
        self.master_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.master_input.setPlaceholderText("Мастер-пароль администратора")
        master_form.addRow("Мастер-пароль:", self.master_input)
        layout.addLayout(master_form)

        # ── Вкладки: Генерация / Свой пароль ───────────────────
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # ── Вкладка 1: Генерация ────────────────────────────────
        gen_page = QWidget()
        gen_layout = QFormLayout(gen_page)
        gen_layout.setContentsMargins(8, 10, 8, 10)

        new_pass_row = QHBoxLayout()
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("Новый пароль")
        btn_generate = QPushButton("Сгенерировать")
        btn_generate.setFixedWidth(130)
        btn_generate.clicked.connect(self._generate)
        new_pass_row.addWidget(self.new_password_input)
        new_pass_row.addWidget(btn_generate)
        gen_layout.addRow("Новый пароль:", new_pass_row)

        self.mnemonic_label = QLabel("—")
        self.mnemonic_label.setObjectName("settingsDescription")
        self.mnemonic_label.setTextFormat(Qt.TextFormat.RichText)
        self.mnemonic_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        gen_layout.addRow("Мнемоника:", self.mnemonic_label)

        self._tabs.addTab(gen_page, "Генерация")

        # ── Вкладка 2: Свой пароль ──────────────────────────────
        custom_page = QWidget()
        custom_vlay = QVBoxLayout(custom_page)
        custom_vlay.setContentsMargins(8, 10, 8, 10)
        custom_vlay.setSpacing(8)

        custom_form = QFormLayout()
        custom_form.setContentsMargins(0, 0, 0, 0)

        custom_pass_row = QHBoxLayout()
        self.custom_pass_input = QLineEdit()
        self.custom_pass_input.setPlaceholderText("Введите свой пароль")
        self.custom_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._btn_eye = QPushButton("Показать")
        self._btn_eye.setFixedWidth(90)
        self._btn_eye.setCheckable(True)
        self._btn_eye.toggled.connect(self._toggle_custom_pass)
        custom_pass_row.addWidget(self.custom_pass_input)
        custom_pass_row.addWidget(self._btn_eye)
        custom_form.addRow("Новый пароль:", custom_pass_row)

        self.custom_hint_input = QLineEdit()
        self.custom_hint_input.setPlaceholderText("Необязательно — подсказка для пароля")
        custom_form.addRow("Подсказка:", self.custom_hint_input)

        custom_vlay.addLayout(custom_form)

        # Строка статистики — на всю ширину, по центру, без переноса
        self._pass_stats_label = QLabel("")
        self._pass_stats_label.setObjectName("settingsDescription")
        self._pass_stats_label.setWordWrap(False)
        self._pass_stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pass_stats_label.setTextFormat(Qt.TextFormat.RichText)
        custom_vlay.addWidget(self._pass_stats_label)
        custom_vlay.addStretch()

        self.custom_pass_input.textChanged.connect(self._update_pass_stats)

        self._tabs.addTab(custom_page, "Свой пароль")

        # ── Кнопки ─────────────────────────────────────────────
        buttons = QHBoxLayout()
        self.apply_btn = QPushButton("Применить")
        btn_cancel = QPushButton("Отмена")
        self.apply_btn.clicked.connect(self._on_apply)
        btn_cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(self.apply_btn)
        buttons.addWidget(btn_cancel)
        layout.addLayout(buttons)

        self.setMinimumWidth(680)
        self.setMinimumHeight(380)

        # Флаг: SSH уже выполнен, но Vault не обновился
        self._vault_retry_mode = False
        self._saved_hint = ""   # запоминаем hint для retry-режима

        self._generate()

    def _msgbox(self, icon, title: str, text: str):
        """QMessageBox с гарантированной шириной под заголовок."""
        msg = QMessageBox(self)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(text)
        min_w = max(320, len(title) * 11 + 160)
        msg.layout().addItem(
            QSpacerItem(
                min_w, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
            ),
            msg.layout().rowCount(),
            0,
            1,
            msg.layout().columnCount(),
        )
        msg.exec()

    def _generate(self):
        s = UserSettings()
        password, mnemonic = generate_password(
            word_count=s.get("password_word_count") or 3,
            digit_count=s.get("password_digit_count") or 2,
        )
        self.new_password_input.setText(password)
        self.mnemonic_label.setText(mnemonic)

    def _toggle_custom_pass(self, checked: bool):
        self.custom_pass_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self._btn_eye.setText("Скрыть" if checked else "Показать")

    def _update_pass_stats(self, text: str):
        if not text:
            self._pass_stats_label.setText("")
            return
        length = len(text)
        upper = sum(1 for c in text if c.isupper())
        lower = sum(1 for c in text if c.islower())
        digits = sum(1 for c in text if c.isdigit())
        special = length - upper - lower - digits

        parts = [f"Длина: <b>{length}</b>"]
        if upper:
            parts.append(f"заглавных: <b>{upper}</b>")
        if lower:
            parts.append(f"строчных: <b>{lower}</b>")
        if digits:
            parts.append(f"цифр: <b>{digits}</b>")
        if special:
            parts.append(f"спецсимволов: <b>{special}</b>")

        if length < 8:
            color = "#ef9a9a"
            strength = "слабый"
        elif length < 12 or (upper == 0 or digits == 0):
            color = "#ffd54f"
            strength = "средний"
        else:
            color = "#81c995"
            strength = "надёжный"

        parts.append(f'<span style="color:{color}">● {strength}</span>')
        self._pass_stats_label.setText("  ·  ".join(parts))

    def _get_password_and_hint(self) -> tuple[str, str]:
        """Возвращает (пароль, подсказка_plain) из активной вкладки."""
        if self._tabs.currentIndex() == 0:
            password = self.new_password_input.text().strip()
            hint = re.sub(r"<[^>]+>", "", self.mnemonic_label.text()).strip()
        else:
            password = self.custom_pass_input.text().strip()
            hint = self.custom_hint_input.text().strip()
        return password, hint

    def _on_apply(self):
        master = self.master_input.text().strip()
        new_pass, hint = self._get_password_and_hint()

        if not master:
            self._msgbox(QMessageBox.Icon.Warning, "Ошибка", "Введите мастер-пароль")
            return

        if not new_pass:
            self._msgbox(
                QMessageBox.Icon.Warning, "Ошибка", "Новый пароль не может быть пустым"
            )
            return

        self.apply_btn.setEnabled(False)

        # ── Режим повтора: SSH уже выполнен, пробуем снова записать в Vault ──
        if self._vault_retry_mode:
            self._save_to_vault(master, new_pass, self._saved_hint)
            return

        # ── Полный цикл ───────────────────────────────────────────────────────
        current_password = None
        try:
            # Шаг 1: получаем текущие SSH-креды из Vault (заодно проверяет мастер-пароль)
            self.apply_btn.setText("Проверка доступа...")
            try:
                creds = self._api.show(
                    server_id=self.server_id,
                    port=22,
                    username=self.admin_login,
                    master_password=master,
                )
            except ApiError as e:
                if e.status_code == 403:
                    self._msgbox(
                        QMessageBox.Icon.Warning, "Ошибка", "Неверный мастер-пароль"
                    )
                elif e.status_code == 429:
                    self._msgbox(
                        QMessageBox.Icon.Warning,
                        "Заблокировано",
                        f"Попробуйте через {e.retry_after} сек.",
                    )
                else:
                    self._msgbox(QMessageBox.Icon.Critical, "Ошибка", e.message)
                self.apply_btn.setEnabled(True)
                self.apply_btn.setText("Применить")
                return

            current_username = creds["username"]
            current_password = creds["password"]

            # Шаг 2: меняем пароль на сервере по SSH с машины фронтенда
            self.apply_btn.setText("Меняю пароль по SSH...")
            try:
                self._rotate_fn(
                    host=self.host,
                    username=current_username,
                    current_password=current_password,
                    new_password=new_pass,
                    port=22,
                )
            except SSHRotateError as e:
                self._msgbox(QMessageBox.Icon.Critical, "Ошибка SSH", str(e))
                self.apply_btn.setEnabled(True)
                self.apply_btn.setText("Применить")
                return

            # SSH прошёл — устанавливаем флаг до попытки записи в Vault.
            # Если Vault упадёт ниже, повторное нажатие пропустит SSH.
            self._vault_retry_mode = True
            self._saved_hint = hint

            # Шаг 3: сохраняем новый пароль в Vault
            self._save_to_vault(master, new_pass, hint)

        finally:
            _wipe(master)
            _wipe(new_pass)
            if current_password is not None:
                _wipe(current_password)
            self.master_input.clear()

    def _save_to_vault(self, master: str, new_pass: str, hint: str = ""):
        """
        Шаг 3: записывает новый пароль в Vault.
        Вызывается как из полного цикла, так и при повторной попытке
        (когда SSH уже выполнен, но Vault ранее не ответил).
        """
        current_password = None
        try:
            self.apply_btn.setText("Сохраняю в хранилище...")
            try:
                self._api.rotate(
                    server_id=self.server_id,
                    ssh_port=22,
                    new_password=new_pass,
                    username=self.admin_login,
                    master_password=master,
                    mnemonic=hint,
                )
            except ApiError as e:
                # Пароль уже сменён на сервере, но не записан в Vault.
                # Кнопка меняет текст — следующее нажатие пойдёт сразу в Vault,
                # минуя SSH (который уже сделал своё дело).
                self._msgbox(
                    QMessageBox.Icon.Critical,
                    "Ошибка записи в хранилище",
                    f"Пароль на сервере <b>{self.host}</b> уже изменён, "
                    f"но записать в хранилище не удалось.\n\n"
                    f"Новый пароль: {new_pass}\n\n"
                    f"Введите мастер-пароль и нажмите «Повторить запись» "
                    f"или сохраните пароль вручную.\n\n"
                    f"Ошибка: {e.message}",
                )
                self.apply_btn.setText("Повторить запись в Vault")
                self.apply_btn.setEnabled(True)
                return

            # Успех — сбрасываем флаг режима повтора
            self._vault_retry_mode = False

            msg = QMessageBox(self)
            msg.setWindowTitle("Готово")
            msg.setTextFormat(Qt.TextFormat.RichText)
            hint_display = hint if hint else "—"
            msg.setText(
                f"Пароль успешно изменён на сервере <b>{self.host}</b><br><br>"
                f"Подсказка:&nbsp; {hint_display}"
            )
            msg.exec()
            self.accept()

        finally:
            _wipe(master)
            _wipe(new_pass)
            if current_password is not None:
                _wipe(current_password)
            self.master_input.clear()
