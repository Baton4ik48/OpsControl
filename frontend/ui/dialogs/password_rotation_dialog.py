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
        btn_generate.setFixedWidth(130)
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

        self.mnemonic_label.setTextFormat(Qt.TextFormat.RichText)

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

        # Ширина окна — title bar использует системный шрифт, считаем по символам
        min_w = max(460, len(self.windowTitle()) * 11 + 160)
        self.setMinimumWidth(min_w)

        # Флаг: SSH уже выполнен, но Vault не обновился — при повторном нажатии
        # пропускаем SSH и идём сразу к записи в Vault
        self._vault_retry_mode = False

        # Сразу генерируем пароль
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
            word_count=s.get("password_word_count"),
            letters_per_word=s.get("password_letters_per_word"),
            digit_count=s.get("password_digit_count"),
        )
        self.new_password_input.setText(password)
        self.mnemonic_label.setText(mnemonic)

    def _on_apply(self):
        master = self.master_input.text().strip()
        # Читаем из виджета: даже если предыдущий Python-объект был затёрт _wipe,
        # Qt хранит свою копию в QLineEdit и возвращает правильное значение
        new_pass = self.new_password_input.text().strip()

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
            self._save_to_vault(master, new_pass)
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

            # Шаг 3: сохраняем новый пароль в Vault
            self._save_to_vault(master, new_pass)

        finally:
            _wipe(master)
            _wipe(new_pass)
            if current_password is not None:
                _wipe(current_password)
            self.master_input.clear()

    def _save_to_vault(self, master: str, new_pass: str):
        """
        Шаг 3: записывает новый пароль в Vault.
        Вызывается как из полного цикла, так и при повторной попытке
        (когда SSH уже выполнен, но Vault ранее не ответил).
        """
        current_password = None
        try:
            self.apply_btn.setText("Сохраняю в хранилище...")
            mnemonic_plain = re.sub(r"<[^>]+>", "", self.mnemonic_label.text()).strip()
            try:
                self._api.rotate(
                    server_id=self.server_id,
                    ssh_port=22,
                    new_password=new_pass,
                    username=self.admin_login,
                    master_password=master,
                    mnemonic=mnemonic_plain,
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
            msg.setText(
                f"Пароль успешно изменён на сервере <b>{self.host}</b><br><br>"
                f"Подсказка:<br>{self.mnemonic_label.text()}"
            )
            msg.exec()
            self.accept()

        finally:
            _wipe(master)
            _wipe(new_pass)
            if current_password is not None:
                _wipe(current_password)
            self.master_input.clear()
