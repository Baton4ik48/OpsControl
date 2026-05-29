import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QGuiApplication

from core.paths import ICONS_DIR

_POPUP_SECONDS = 30


class CredentialPopup(QDialog):
    """
    Всплывающее окно с учётными данными для веб/внешних портов.
    Автоматически закрывается через 30 секунд.
    При закрытии очищает буфер обмена, если туда были скопированы наши данные.
    """

    def __init__(self, ip: str, port: int, username: str, password: str, parent=None):
        super().__init__(parent)

        self._username = username
        self._password = password
        self._clipboard_token = None   # последнее значение, которое мы положили в буфер
        self._seconds_left = _POPUP_SECONDS

        self.setWindowTitle(f"Учётные данные — {ip}:{port}")
        self.setWindowIcon(QIcon(os.path.join(ICONS_DIR, "key_icon.png")))
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setModal(False)
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Заголовок ──────────────────────────────────────────────
        hdr = QLabel(f"<b>{ip} : {port}</b>")
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.setStyleSheet("font-size: 11pt; padding: 4px 0;")
        layout.addWidget(hdr)

        # ── Логин ──────────────────────────────────────────────────
        user_row = QHBoxLayout()
        lbl_user = QLabel("Логин:")
        lbl_user.setFixedWidth(56)
        self._user_field = QLineEdit(username)
        self._user_field.setReadOnly(True)
        btn_copy_user = QPushButton("Копировать")
        btn_copy_user.setFixedWidth(110)
        btn_copy_user.clicked.connect(lambda: self._copy(self._username))
        user_row.addWidget(lbl_user)
        user_row.addWidget(self._user_field)
        user_row.addWidget(btn_copy_user)
        layout.addLayout(user_row)

        # ── Пароль ─────────────────────────────────────────────────
        pass_row = QHBoxLayout()
        lbl_pass = QLabel("Пароль:")
        lbl_pass.setFixedWidth(56)
        self._pass_field = QLineEdit(password)
        self._pass_field.setReadOnly(True)
        self._pass_field.setEchoMode(QLineEdit.EchoMode.Password)

        btn_eye = QPushButton("👁")
        btn_eye.setFixedWidth(32)
        btn_eye.setCheckable(True)
        btn_eye.setToolTip("Показать / скрыть пароль")
        btn_eye.toggled.connect(self._toggle_password_visibility)

        btn_copy_pass = QPushButton("Копировать")
        btn_copy_pass.setFixedWidth(110)
        btn_copy_pass.clicked.connect(lambda: self._copy(self._password))

        pass_row.addWidget(lbl_pass)
        pass_row.addWidget(self._pass_field)
        pass_row.addWidget(btn_eye)
        pass_row.addWidget(btn_copy_pass)
        layout.addLayout(pass_row)

        # ── Таймер ─────────────────────────────────────────────────
        self._countdown_label = QLabel()
        self._countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._countdown_label.setStyleSheet("color: #90a4ae; font-size: 9pt;")
        self._refresh_countdown()
        layout.addWidget(self._countdown_label)

        # ── Кнопка закрыть ─────────────────────────────────────────
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        # ── Таймер обратного отсчёта ───────────────────────────────
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start(1000)

    # ──────────────────────────────────────────────────────────────
    # Private
    # ──────────────────────────────────────────────────────────────

    def _toggle_password_visibility(self, checked: bool):
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self._pass_field.setEchoMode(mode)

    def _copy(self, value: str):
        QGuiApplication.clipboard().setText(value)
        self._clipboard_token = value

    def _refresh_countdown(self):
        self._countdown_label.setText(
            f"Окно закроется через {self._seconds_left} сек. · Буфер обмена будет очищен"
        )

    def _on_tick(self):
        self._seconds_left -= 1
        self._refresh_countdown()
        if self._seconds_left <= 0:
            self.close()

    def _clear_clipboard(self):
        if self._clipboard_token is not None:
            cb = QGuiApplication.clipboard()
            if cb.text() == self._clipboard_token:
                cb.clear()
            self._clipboard_token = None

    def _wipe(self):
        self._pass_field.setText("*" * 10)
        self._user_field.setText("")
        self._password = None
        self._username = None

    # ──────────────────────────────────────────────────────────────
    # Qt overrides
    # ──────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._tick_timer.stop()
        self._clear_clipboard()
        self._wipe()
        super().closeEvent(event)
