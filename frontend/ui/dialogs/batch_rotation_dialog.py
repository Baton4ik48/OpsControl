import os
import re

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QProgressBar,
    QListWidget, QListWidgetItem, QMessageBox, QStackedWidget,
    QWidget, QTabWidget, QFormLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QColor

from core.paths import ICONS_DIR
from core.password_generator import generate_password
from core.config.user_settings import UserSettings
from core.workers.batch_rotation_worker import BatchRotationWorker

# Типы устройств с поддержкой автоматической смены пароля по SSH
_SUPPORTED = {"linux", "nateks", "natex", "cisco"}

def _eligible(server: dict) -> bool:
    """Сервер подходит для пакетной смены: поддерживаемый тип + порт 22 с учётными данными."""
    if server.get("device_type") not in _SUPPORTED:
        return False
    for p in server.get("ports", []):
        if p.get("port") == 22 and p.get("credentials_updated_at"):
            return True
    return False

class BatchRotationDialog(QDialog):
    """
    Диалог пакетной смены паролей.

    Фаза 1 — выбор серверов + новый пароль.
    Фаза 2 — прогресс выполнения с результатом по каждому серверу.
    """

    def __init__(self, tree_data: list, parent=None):
        super().__init__(parent)

        self._tree_data = tree_data
        self._worker: BatchRotationWorker | None = None
        self._row_items: dict[int, QListWidgetItem] = {}  # server_id → строка прогресса
        self._total = 0
        self._done = 0
        self._ok = 0
        self._err = 0

        s = UserSettings()
        self._admin_login = s.get("admin_login") or "admin"

        # Собираем подходящие серверы из дерева
        self._eligible: list[dict] = []
        for branch in tree_data:
            for srv in branch.get("servers", []):
                if _eligible(srv):
                    self._eligible.append({**srv, "_branch": branch["name"]})

        self.setWindowTitle("Групповая ротация паролей")
        self.setWindowIcon(QIcon(os.path.join(ICONS_DIR, "key_icon.png")))
        self.setModal(True)
        self.setMinimumWidth(680)
        self.setMinimumHeight(560)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._make_selection_page())
        self._stack.addWidget(self._make_progress_page())

        root = QVBoxLayout(self)
        root.addWidget(self._stack)

        self._refresh_selected_count()
        self._do_generate()

    def _make_selection_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(8)

        lay.addWidget(QLabel("Мастер-пароль:"))
        self._master_input = QLineEdit()
        self._master_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._master_input.setPlaceholderText("Введите мастер-пароль администратора")
        lay.addWidget(self._master_input)

        self._pass_tabs = QTabWidget()
        lay.addWidget(self._pass_tabs)

        # Вкладка 1 — Генерация
        gen_page = QWidget()
        gen_lay = QVBoxLayout(gen_page)
        gen_lay.setContentsMargins(8, 8, 8, 8)
        gen_lay.setSpacing(6)
        gen_pass_row = QHBoxLayout()
        self._pass_input = QLineEdit()
        self._pass_input.setPlaceholderText("Новый пароль")
        btn_gen = QPushButton("Сгенерировать")
        btn_gen.setFixedWidth(130)
        btn_gen.clicked.connect(self._do_generate)
        gen_pass_row.addWidget(self._pass_input)
        gen_pass_row.addWidget(btn_gen)
        gen_lay.addLayout(gen_pass_row)
        self._mnemonic_lbl = QLabel("—")
        self._mnemonic_lbl.setObjectName("settingsDescription")
        self._mnemonic_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._mnemonic_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        gen_lay.addWidget(self._mnemonic_lbl)
        self._pass_tabs.addTab(gen_page, "Генерация")

        # Вкладка 2 — Свой пароль
        custom_page = QWidget()
        custom_vlay = QVBoxLayout(custom_page)
        custom_vlay.setContentsMargins(8, 8, 8, 8)
        custom_vlay.setSpacing(6)
        custom_form = QFormLayout()
        custom_pass_row = QHBoxLayout()
        self._custom_pass_input = QLineEdit()
        self._custom_pass_input.setPlaceholderText("Введите свой пароль")
        self._custom_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._batch_btn_eye = QPushButton("Показать")
        self._batch_btn_eye.setFixedWidth(90)
        self._batch_btn_eye.setCheckable(True)
        self._batch_btn_eye.toggled.connect(self._toggle_batch_pass)
        custom_pass_row.addWidget(self._custom_pass_input)
        custom_pass_row.addWidget(self._batch_btn_eye)
        custom_form.addRow("Новый пароль:", custom_pass_row)
        self._custom_hint_input = QLineEdit()
        self._custom_hint_input.setPlaceholderText("Необязательно — подсказка")
        custom_form.addRow("Подсказка:", self._custom_hint_input)
        custom_vlay.addLayout(custom_form)
        self._batch_stats_lbl = QLabel("")
        self._batch_stats_lbl.setObjectName("settingsDescription")
        self._batch_stats_lbl.setWordWrap(False)
        self._batch_stats_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._batch_stats_lbl.setTextFormat(Qt.TextFormat.RichText)
        custom_vlay.addWidget(self._batch_stats_lbl)
        custom_vlay.addStretch()
        self._custom_pass_input.textChanged.connect(self._update_batch_stats)
        self._pass_tabs.addTab(custom_page, "Свой пароль")

        sel_hdr = QHBoxLayout()
        sel_hdr.addWidget(QLabel("Выберите серверы:"))
        sel_hdr.addStretch()
        btn_all = QPushButton("Выбрать все")
        btn_all.setFixedWidth(110)
        btn_all.clicked.connect(lambda: self._set_all(True))
        btn_none = QPushButton("Снять все")
        btn_none.setFixedWidth(110)
        btn_none.clicked.connect(lambda: self._set_all(False))
        sel_hdr.addWidget(btn_all)
        sel_hdr.addWidget(btn_none)
        lay.addLayout(sel_hdr)

        self._srv_tree = QTreeWidget()
        self._srv_tree.setHeaderHidden(True)
        self._srv_tree.itemChanged.connect(self._on_item_changed)
        self._build_srv_tree()
        self._srv_tree.expandAll()
        lay.addWidget(self._srv_tree)

        footer = QHBoxLayout()
        self._count_lbl = QLabel()
        footer.addWidget(self._count_lbl)
        footer.addStretch()
        self._btn_start = QPushButton("Начать смену паролей")
        self._btn_start.clicked.connect(self._on_start)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        footer.addWidget(self._btn_start)
        footer.addWidget(btn_cancel)
        lay.addLayout(footer)

        return page

    def _build_srv_tree(self):
        self._srv_tree.blockSignals(True)
        self._srv_tree.clear()

        by_branch: dict[str, list] = {}
        for srv in self._eligible:
            by_branch.setdefault(srv["_branch"], []).append(srv)

        for bname, servers in by_branch.items():
            b_item = QTreeWidgetItem([f"{bname}  ({len(servers)} шт.)"])
            b_item.setFlags(b_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            b_item.setCheckState(0, Qt.CheckState.Checked)
            b_item.setData(0, Qt.ItemDataRole.UserRole, None)
            self._srv_tree.addTopLevelItem(b_item)

            for srv in servers:
                s_item = QTreeWidgetItem([f"{srv['name']}   {srv['ip']}"])
                s_item.setFlags(s_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                s_item.setCheckState(0, Qt.CheckState.Checked)
                s_item.setData(0, Qt.ItemDataRole.UserRole, srv["id"])
                b_item.addChild(s_item)

        self._srv_tree.blockSignals(False)

    def _on_item_changed(self, item: QTreeWidgetItem, _col: int):
        self._srv_tree.blockSignals(True)
        srv_id = item.data(0, Qt.ItemDataRole.UserRole)
        state = item.checkState(0)

        if srv_id is None:
            # Ветка — синхронизируем детей
            for i in range(item.childCount()):
                item.child(i).setCheckState(0, state)
        else:
            # Сервер — обновляем состояние ветки
            parent = item.parent()
            if parent:
                states = {parent.child(i).checkState(0) for i in range(parent.childCount())}
                if states == {Qt.CheckState.Checked}:
                    parent.setCheckState(0, Qt.CheckState.Checked)
                elif states == {Qt.CheckState.Unchecked}:
                    parent.setCheckState(0, Qt.CheckState.Unchecked)
                else:
                    parent.setCheckState(0, Qt.CheckState.PartiallyChecked)

        self._srv_tree.blockSignals(False)
        self._refresh_selected_count()

    def _set_all(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self._srv_tree.blockSignals(True)
        for i in range(self._srv_tree.topLevelItemCount()):
            b = self._srv_tree.topLevelItem(i)
            b.setCheckState(0, state)
            for j in range(b.childCount()):
                b.child(j).setCheckState(0, state)
        self._srv_tree.blockSignals(False)
        self._refresh_selected_count()

    def _selected_servers(self) -> list[dict]:
        selected = []
        for i in range(self._srv_tree.topLevelItemCount()):
            b = self._srv_tree.topLevelItem(i)
            for j in range(b.childCount()):
                child = b.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    srv_id = child.data(0, Qt.ItemDataRole.UserRole)
                    for s in self._eligible:
                        if s["id"] == srv_id:
                            selected.append(s)
                            break
        return selected

    def _refresh_selected_count(self):
        n = len(self._selected_servers())
        self._count_lbl.setText(f"Выбрано серверов: {n}")

    def _do_generate(self):
        pwd, mnemonic = generate_password()
        self._pass_input.setText(pwd)
        self._mnemonic_lbl.setText(mnemonic)

    def _toggle_batch_pass(self, checked: bool):
        self._custom_pass_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self._batch_btn_eye.setText("Скрыть" if checked else "Показать")

    def _update_batch_stats(self, text: str):
        if not text:
            self._batch_stats_lbl.setText("")
            return
        length = len(text)
        upper = sum(1 for c in text if c.isupper())
        lower = sum(1 for c in text if c.islower())
        digits = sum(1 for c in text if c.isdigit())
        special = length - upper - lower - digits
        parts = [f"Длина: <b>{length}</b>"]
        if upper:   parts.append(f"заглавных: <b>{upper}</b>")
        if lower:   parts.append(f"строчных: <b>{lower}</b>")
        if digits:  parts.append(f"цифр: <b>{digits}</b>")
        if special: parts.append(f"спецсимволов: <b>{special}</b>")
        if length < 8:
            color, strength = "#ef9a9a", "слабый"
        elif length < 12 or not upper or not digits:
            color, strength = "#ffd54f", "средний"
        else:
            color, strength = "#81c995", "надёжный"
        parts.append(f'<span style="color:{color}">● {strength}</span>')
        self._batch_stats_lbl.setText("  ·  ".join(parts))

    def _get_password_and_hint(self) -> tuple[str, str]:
        if self._pass_tabs.currentIndex() == 0:
            password = self._pass_input.text().strip()
            hint = re.sub(r"<[^>]+>", "", self._mnemonic_lbl.text()).strip()
        else:
            password = self._custom_pass_input.text().strip()
            hint = self._custom_hint_input.text().strip()
        return password, hint

    def _on_start(self):
        master = self._master_input.text().strip()
        new_pass, hint = self._get_password_and_hint()
        selected = self._selected_servers()

        if not master:
            QMessageBox.warning(self, "Ошибка", "Введите мастер-пароль.")
            return
        if not new_pass:
            QMessageBox.warning(self, "Ошибка", "Введите или сгенерируйте новый пароль.")
            return
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один сервер.")
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Сменить пароль на {len(selected)} сервере(ах)?\n\n"
            f"Новый пароль:  {new_pass}\n\n"
            "Операция последовательная — при ошибке на одном сервере "
            "остальные продолжат выполняться.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._launch_progress(selected, master, new_pass, hint)

    def _make_progress_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(8)

        self._prog_label = QLabel("Подготовка…")
        self._prog_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._prog_label)

        self._prog_bar = QProgressBar()
        lay.addWidget(self._prog_bar)

        self._result_list = QListWidget()
        self._result_list.setSpacing(2)
        lay.addWidget(self._result_list)

        self._summary_lbl = QLabel("")
        self._summary_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._summary_lbl.setStyleSheet("font-weight: bold; font-size: 10pt;")
        lay.addWidget(self._summary_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_stop = QPushButton("Остановить")
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_close2 = QPushButton("Закрыть")
        self._btn_close2.setEnabled(False)
        self._btn_close2.clicked.connect(self.accept)
        btn_row.addWidget(self._btn_stop)
        btn_row.addWidget(self._btn_close2)
        lay.addLayout(btn_row)

        return page

    def _launch_progress(self, selected, master, new_pass, mnemonic):
        self._total = len(selected)
        self._done = self._ok = self._err = 0
        self._row_items.clear()
        self._result_list.clear()

        self._prog_bar.setMaximum(self._total)
        self._prog_bar.setValue(0)
        self._prog_label.setText(f"0 / {self._total}")
        self._summary_lbl.setText("")

        # Предзаполняем список серверов со статусом "ожидание"
        for srv in selected:
            item = QListWidgetItem(f"  ⟳   {srv['name']}  —  {srv['ip']}")
            item.setForeground(QColor("#90a4ae"))
            self._result_list.addItem(item)
            self._row_items[srv["id"]] = item

        self._stack.setCurrentIndex(1)

        self._worker = BatchRotationWorker(
            servers=selected,
            master_password=master,
            new_password=new_pass,
            mnemonic=mnemonic,
            admin_login=self._admin_login,
        )
        self._worker.server_done.connect(self._on_server_done)
        self._worker.finished_all.connect(self._on_all_done)
        self._worker.start()

    def _on_server_done(self, server_id: int, status: str, message: str):
        self._done += 1
        self._prog_bar.setValue(self._done)
        self._prog_label.setText(f"{self._done} / {self._total}")

        item = self._row_items.get(server_id)
        if not item:
            return

        srv = next((s for s in self._eligible if s["id"] == server_id), {})
        label = f"{srv.get('name', server_id)}  —  {srv.get('ip', '')}"

        if status == "ok":
            self._ok += 1
            item.setText(f"  ✓   {label}")
            item.setForeground(QColor("#81c995"))
        elif status == "skip":
            item.setText(f"  —   {label}   ({message})")
            item.setForeground(QColor("#ffd54f"))
        elif status == "vault_fail":
            self._err += 1
            item.setText(f"  ⚠   {label}   {message}")
            item.setForeground(QColor("#ffb74d"))
        else:
            self._err += 1
            item.setText(f"  ✗   {label}   {message}")
            item.setForeground(QColor("#ef9a9a"))

        self._result_list.scrollToItem(item)

    def _on_all_done(self):
        self._summary_lbl.setText(
            f"Готово:   ✓ {self._ok} успешно     ✗ {self._err} ошибок"
        )
        self._btn_stop.setEnabled(False)
        self._btn_close2.setEnabled(True)

    def _on_stop(self):
        if self._worker:
            self._worker.stop()
        self._btn_stop.setEnabled(False)

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(3000)
        super().closeEvent(event)
