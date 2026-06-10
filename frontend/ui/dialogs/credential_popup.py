import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QFrame,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QGuiApplication, QFont

from core.paths import ICONS_DIR

_POPUP_SECONDS = 30

_STYLE = """
QDialog {
    background-color: #1a2530;
}
QLabel {
    background: transparent;
    color: #cfd8dc;
}
QLabel#host_label {
    color: #4fc3f7;
    font-size: 12pt;
    font-weight: bold;
    padding: 6px 0 10px 0;
}
QLabel#field_label {
    color: #90a4ae;
    font-size: 9pt;
}
QLabel#countdown_label {
    color: #546e7a;
    font-size: 8pt;
    padding-top: 4px;
}
QLineEdit {
    background-color: #0f1b1e;
    color: #eceff1;
    border: 1px solid #1e3a42;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 10pt;
    selection-background-color: #4fc3f7;
}
QPushButton {
    background-color: #1e3a42;
    color: #81d4fa;
    border: 1px solid #2a5566;
    border-radius: 4px;
    padding: 5px 14px;
    font-size: 9pt;
    min-height: 28px;
}
QPushButton:hover {
    background-color: #2a5566;
    color: #e1f5fe;
}
QPushButton:pressed {
    background-color: #4fc3f7;
    color: #0d1f26;
}
QPushButton#btn_copy {
    min-width: 90px;
}
QPushButton#btn_eye {
    min-width: 36px;
    max-width: 36px;
    padding: 5px 6px;
    font-size: 11pt;
}
QPushButton#btn_close {
    background-color: #263238;
    color: #90a4ae;
    border: 1px solid #37474f;
    min-height: 30px;
}
QPushButton#btn_close:hover {
    background-color: #37474f;
    color: #cfd8dc;
}
QFrame#separator {
    color: #1e3a42;
    background-color: #1e3a42;
    max-height: 1px;
}
"""

class CredentialPopup(QDialog):
    """
    Компактное окно с учётными данными для веб / внешних приложений.
    Закрывается через 30 сек, очищает буфер обмена.
    """

    def __init__(self, ip: str, port: int, username: str, password: str, parent=None):
        super().__init__(parent)

        self._username = username
        self._password = password
        self._clipboard_token: str | None = None
        self._seconds_left = _POPUP_SECONDS

        self.setWindowTitle(f"{ip}  :  {port}")
        self.setWindowIcon(QIcon(os.path.join(ICONS_DIR, "key_icon.png")))
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setModal(False)
        self.setFixedWidth(400)
        self.setStyleSheet(_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 14)
        root.setSpacing(0)

        host_lbl = QLabel(f"{ip}  :  {port}")
        host_lbl.setObjectName("host_label")
        host_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(host_lbl)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)
        root.addSpacing(10)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)

        lbl_user = QLabel("Логин")
        lbl_user.setObjectName("field_label")
        self._user_field = QLineEdit(username)
        self._user_field.setReadOnly(True)

        btn_copy_user = QPushButton("Копировать")
        btn_copy_user.setObjectName("btn_copy")
        btn_copy_user.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_user.clicked.connect(lambda: self._copy(self._username, btn_copy_user))

        grid.addWidget(lbl_user,       0, 0)
        grid.addWidget(self._user_field, 0, 1)
        grid.addWidget(btn_copy_user,  0, 2)

        lbl_pass = QLabel("Пароль")
        lbl_pass.setObjectName("field_label")
        self._pass_field = QLineEdit(password)
        self._pass_field.setReadOnly(True)
        self._pass_field.setEchoMode(QLineEdit.EchoMode.Password)

        pass_btns = QHBoxLayout()
        pass_btns.setSpacing(6)

        btn_eye = QPushButton("👁")
        btn_eye.setObjectName("btn_eye")
        btn_eye.setCheckable(True)
        btn_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye.setToolTip("Показать / скрыть")
        btn_eye.toggled.connect(self._toggle_visibility)

        btn_copy_pass = QPushButton("Копировать")
        btn_copy_pass.setObjectName("btn_copy")
        btn_copy_pass.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_pass.clicked.connect(lambda: self._copy(self._password, btn_copy_pass))

        pass_btns.addWidget(btn_eye)
        pass_btns.addWidget(btn_copy_pass)

        grid.addWidget(lbl_pass,        1, 0)
        grid.addWidget(self._pass_field, 1, 1)
        grid.addLayout(pass_btns,        1, 2)

        root.addLayout(grid)
        root.addSpacing(10)

        sep2 = QFrame()
        sep2.setObjectName("separator")
        sep2.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep2)
        root.addSpacing(6)

        self._countdown_lbl = QLabel()
        self._countdown_lbl.setObjectName("countdown_label")
        self._countdown_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._countdown_lbl)
        root.addSpacing(8)

        btn_close = QPushButton("Закрыть")
        btn_close.setObjectName("btn_close")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        root.addWidget(btn_close)

        self._refresh_countdown()
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start(1000)

    def _toggle_visibility(self, checked: bool):
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self._pass_field.setEchoMode(mode)

    def _copy(self, value: str, btn: QPushButton):
        QGuiApplication.clipboard().setText(value)
        self._clipboard_token = value
        original = btn.text()
        btn.setText("✓ Скопировано")
        QTimer.singleShot(1500, lambda: btn.setText(original))

    def _refresh_countdown(self):
        self._countdown_lbl.setText(
            f"Закроется через {self._seconds_left} сек.  ·  буфер будет очищен"
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
        self._pass_field.setText("•" * 10)
        self._user_field.setText("")
        self._password = None
        self._username = None

    def closeEvent(self, event):
        self._tick_timer.stop()
        self._clear_clipboard()
        self._wipe()
        super().closeEvent(event)
