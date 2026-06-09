import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QColor

from core.paths import ICONS_DIR
from core.api.credentials import CredentialsApi
from core.api.base import ApiError


class _UpsertWorker(QThread):
    """Последовательно записывает учётные данные для каждого порта в Vault."""
    port_done = pyqtSignal(int, int, str, str)  # server_id, port, status("ok"/"error"), message
    finished_all = pyqtSignal()

    def __init__(self, ports: list[tuple[int, int]], username: str, password: str):
        super().__init__()
        self._ports = ports          # [(server_id, port), ...]
        self._username = username
        self._password = password
        self._api = CredentialsApi()

    def run(self):
        for server_id, port in self._ports:
            try:
                self._api.upsert(
                    server_id=server_id,
                    port=port,
                    username=self._username,
                    password=self._password,
                )
                self.port_done.emit(server_id, port, "ok", "")
            except ApiError as e:
                self.port_done.emit(server_id, port, "error", e.message)
            except Exception as e:
                self.port_done.emit(server_id, port, "error", str(e))
        self.finished_all.emit()


class BulkCredentialsDialog(QDialog):
    """
    Пакетное обновление учётных данных в Vault для нескольких портов.
    Вводишь логин + пароль один раз — сохраняется во все выбранные порты.
    """

    def __init__(self, ports: list[tuple[int, int]], parent=None):
        """
        ports — список (server_id, port_number)
        """
        super().__init__(parent)

        self._ports = ports
        self._worker: _UpsertWorker | None = None
        self._done = 0
        self._ok = 0
        self._err = 0

        self.setWindowTitle(f"Обновление учётных данных — {len(ports)} портов")
        self.setWindowIcon(QIcon(os.path.join(ICONS_DIR, "key_icon.png")))
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(420)

        root = QVBoxLayout(self)
        root.setSpacing(10)

        # ── Описание ───────────────────────────────────────────
        info = QLabel(
            f"Введите учётные данные, которые будут сохранены "
            f"в Vault для <b>{len(ports)}</b> выбранных портов."
        )
        info.setWordWrap(True)
        info.setObjectName("settingsDescription")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(info)

        # ── Форма ввода ────────────────────────────────────────
        form = QFormLayout()
        form.setContentsMargins(0, 4, 0, 4)

        self._user_input = QLineEdit()
        self._user_input.setPlaceholderText("Логин")
        form.addRow("Логин:", self._user_input)

        pass_row = QHBoxLayout()
        self._pass_input = QLineEdit()
        self._pass_input.setPlaceholderText("Пароль")
        self._pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        btn_eye = QPushButton("Показать")
        btn_eye.setFixedWidth(90)
        btn_eye.setCheckable(True)
        btn_eye.toggled.connect(self._toggle_pass)
        pass_row.addWidget(self._pass_input)
        pass_row.addWidget(btn_eye)
        form.addRow("Пароль:", pass_row)
        root.addLayout(form)

        # ── Прогресс (скрыт до старта) ─────────────────────────
        self._prog_bar = QProgressBar()
        self._prog_bar.setMaximum(len(ports))
        self._prog_bar.setValue(0)
        self._prog_bar.setVisible(False)
        root.addWidget(self._prog_bar)

        # ── Список результатов ─────────────────────────────────
        self._result_list = QListWidget()
        self._result_list.setSpacing(1)
        self._result_list.setVisible(False)
        root.addWidget(self._result_list)

        # Заполняем список портов заранее (статус "ожидание")
        self._items: dict[tuple[int, int], QListWidgetItem] = {}
        for server_id, port in ports:
            item = QListWidgetItem(f"  ·  server {server_id}  —  порт {port}")
            item.setForeground(QColor("#546e7a"))
            self._result_list.addItem(item)
            self._items[(server_id, port)] = item

        # ── Итог ──────────────────────────────────────────────
        self._summary_lbl = QLabel("")
        self._summary_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._summary_lbl.setStyleSheet("font-weight: bold;")
        self._summary_lbl.setVisible(False)
        root.addWidget(self._summary_lbl)

        # ── Кнопки ────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_save = QPushButton("Сохранить")
        self._btn_save.clicked.connect(self._on_save)
        self._btn_close = QPushButton("Отмена")
        self._btn_close.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_save)
        btn_row.addWidget(self._btn_close)
        root.addLayout(btn_row)

    # ──────────────────────────────────────────────────────────

    def _toggle_pass(self, checked: bool):
        self._pass_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def _on_save(self):
        username = self._user_input.text().strip()
        password = self._pass_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль.")
            return

        # Переключаемся в режим прогресса
        self._user_input.setEnabled(False)
        self._pass_input.setEnabled(False)
        self._btn_save.setEnabled(False)
        self._btn_close.setText("Подождите…")
        self._btn_close.setEnabled(False)
        self._prog_bar.setVisible(True)
        self._result_list.setVisible(True)

        self._worker = _UpsertWorker(self._ports, username, password)
        self._worker.port_done.connect(self._on_port_done)
        self._worker.finished_all.connect(self._on_all_done)
        self._worker.start()

    def _on_port_done(self, server_id: int, port: int, status: str, message: str):
        self._done += 1
        self._prog_bar.setValue(self._done)

        item = self._items.get((server_id, port))
        if not item:
            return

        if status == "ok":
            self._ok += 1
            item.setText(f"  ✓  server {server_id}  —  порт {port}")
            item.setForeground(QColor("#81c995"))
        else:
            self._err += 1
            item.setText(f"  ✗  server {server_id}  —  порт {port}  ({message})")
            item.setForeground(QColor("#ef9a9a"))

        self._result_list.scrollToItem(item)

    def _on_all_done(self):
        self._summary_lbl.setText(
            f"Готово:   ✓ {self._ok} сохранено   ✗ {self._err} ошибок"
        )
        self._summary_lbl.setVisible(True)
        self._btn_close.setText("Закрыть")
        self._btn_close.setEnabled(True)
        if self._err == 0:
            self._btn_close.clicked.disconnect()
            self._btn_close.clicked.connect(self.accept)
