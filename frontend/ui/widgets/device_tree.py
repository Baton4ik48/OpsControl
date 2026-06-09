import os
from pathlib import Path
from datetime import datetime, timezone

from PyQt6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
)
from PyQt6.QtGui import QIcon, QFont, QColor, QBrush
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QModelIndex

from core.paths import ICONS_DIR, path_to_file_uri
from ui.context_menus.device_tree_context_menu import DeviceTreeContextMenu


ROLE_TYPE = Qt.ItemDataRole.UserRole + 1
ROLE_SERVER_ID = Qt.ItemDataRole.UserRole + 2
ROLE_PORT = Qt.ItemDataRole.UserRole + 3
ROLE_IP = Qt.ItemDataRole.UserRole + 4
ROLE_DEVICE_TYPE = Qt.ItemDataRole.UserRole + 5

CREDENTIALS_SHOW_TIMEOUT_MS = 1 * 60 * 1000


def format_dt(value):
    if not value:
        return "нет данных"

    dt = datetime.fromisoformat(value)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    local = dt.astimezone()
    return local.strftime("%d.%m.%Y %H:%M")


def _icon_img(icon_path, size=13):
    return f'<img src="{path_to_file_uri(icon_path)}" width="{size}" height="{size}">'


def _build_port_tooltip(state, last_success, last_failure):
    icon_up = os.path.join(ICONS_DIR, "status_up.png")
    icon_down = os.path.join(ICONS_DIR, "status_down.png")

    rows = []

    if state is True:
        rows.append(
            f"<tr><td>{_icon_img(icon_up)}</td>" f"<td>&nbsp;<b>Онлайн</b></td></tr>"
        )
        if last_failure:
            rows.append(
                f"<tr><td>{_icon_img(icon_down)}</td>"
                f"<td>&nbsp;Последний раз недоступен:&nbsp;{format_dt(last_failure)}</td></tr>"
            )

    elif state is False:
        if last_success:
            rows.append(
                f"<tr><td>{_icon_img(icon_down)}</td>"
                f"<td>&nbsp;Последний раз был в сети:&nbsp;{format_dt(last_success)}</td></tr>"
            )
        else:
            rows.append(
                f"<tr><td>{_icon_img(icon_down)}</td>"
                f"<td>&nbsp;В сети не наблюдался</td></tr>"
            )

    else:
        if last_success:
            rows.append(
                f"<tr><td>{_icon_img(icon_up)}</td>"
                f"<td>&nbsp;Последний раз в сети:&nbsp;{format_dt(last_success)}</td></tr>"
            )
        if last_failure:
            rows.append(
                f"<tr><td>{_icon_img(icon_down)}</td>"
                f"<td>&nbsp;Последний раз недоступен:&nbsp;{format_dt(last_failure)}</td></tr>"
            )
        if not last_success and not last_failure:
            rows.append('<tr><td colspan="2">Статус неизвестен</td></tr>')

    return f'<table cellspacing="3">{"".join(rows)}</table>'


def _password_age_color(credentials_updated_at, rotation_days):
    """Возвращает QColor для столбца 'Дата обновления пароля' по % оставшегося срока.

    Пороги (от суммарного интервала):
      ≥ 50%  → None  (норма — дефолтный белый, не засоряем)
      ≥ 22%  → жёлтый
      ≥  9%  → оранжевый
       < 9%  → красный (или истёк)
    """
    if not credentials_updated_at or not rotation_days:
        return None
    try:
        dt = datetime.fromisoformat(credentials_updated_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_elapsed = (now - dt).total_seconds() / 86400
        days_remaining = max(0.0, rotation_days - days_elapsed)
        pct = days_remaining / rotation_days
        if pct >= 0.50:
            return None  # всё хорошо — цвет не нужен
        elif pct >= 0.22:
            return QColor(210, 210, 50)  # жёлтый
        elif pct >= 0.09:
            return QColor(210, 130, 30)  # оранжевый
        else:
            return QColor(210, 60, 60)  # красный
    except Exception:
        return None


class _CommentDialog(QDialog):
    """Диалог редактирования комментария с многострочным полем."""

    def __init__(self, title: str, subtitle: str, current_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Комментарий")
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setMinimumHeight(280)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Заголовок ────────────────────────────────────────────
        title_lbl = QLabel(title)
        title_lbl.setObjectName("dialogTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setWordWrap(True)
        lay.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setObjectName("dialogSubtitle")
            sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sub_lbl.setWordWrap(True)
            lay.addWidget(sub_lbl)

        # ── Поле ввода ──────────────────────────────────────────
        body = QVBoxLayout()
        body.setContentsMargins(14, 12, 14, 6)
        body.setSpacing(4)

        self._edit = QTextEdit()
        self._edit.setPlainText(current_text)
        self._edit.setPlaceholderText("Введите комментарий…")
        self._edit.installEventFilter(self)
        body.addWidget(self._edit)

        hint = QLabel("Ctrl+Enter — сохранить")
        hint.setStyleSheet("color:#546e7a; font-size:8pt;")
        hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        body.addWidget(hint)

        lay.addLayout(body)

        # ── Кнопки по центру ───────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(14, 4, 14, 14)
        btn_row.addStretch()
        btn_save = QPushButton("Сохранить")
        btn_save.setFixedWidth(130)
        btn_save.setDefault(True)
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setFixedWidth(100)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_save)
        btn_row.addSpacing(8)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # Курсор в конец
        cursor = self._edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._edit.setTextCursor(cursor)
        self._edit.setFocus()

    def get_text(self) -> str:
        return self._edit.toPlainText().strip()

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj is self._edit and event.type() == QEvent.Type.KeyPress:
            if (event.key() == Qt.Key.Key_Return and
                    event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                self.accept()
                return True
        return super().eventFilter(obj, event)


class DeviceTree(QTreeWidget):

    # делаем роли доступными для context menu
    ROLE_TYPE = ROLE_TYPE
    ROLE_SERVER_ID = ROLE_SERVER_ID
    ROLE_PORT = ROLE_PORT
    ROLE_IP = ROLE_IP
    ROLE_DEVICE_TYPE = ROLE_DEVICE_TYPE

    refresh_branch_requested = pyqtSignal(str)  # branch_name
    refresh_server_requested = pyqtSignal(int, str)
    refresh_port_requested = pyqtSignal(int, int, str)
    open_protocol_requested = pyqtSignal(int, int, str, str)
    show_credentials_requested = pyqtSignal(int, int, str)
    rotate_password_requested = pyqtSignal(int, str, str)  # server_id, ip, device_type
    comment_changed = pyqtSignal(str, int, int, str)        # type, server_id, port, text

    def __init__(self):
        super().__init__()

        self._credential_timers = {}
        self._has_rendered = False
        self.user_settings = None

        self.setHeaderLabels(
            ["Устройство", "IP", "Статус", "Учётные данные", "Дата обновления пароля", "Комментарий"]
        )

        # ===== Icons =====
        self.icon_up = QIcon(os.path.join(ICONS_DIR, "status_up.png"))
        self.icon_down = QIcon(os.path.join(ICONS_DIR, "status_down.png"))
        self.icon_unknown = QIcon(os.path.join(ICONS_DIR, "status_unknown.png"))
        self.icon_update = QIcon(os.path.join(ICONS_DIR, "update_icon.png"))
        self.icon_ssh = QIcon(os.path.join(ICONS_DIR, "ssh_icon.png"))
        self.icon_rdp = QIcon(os.path.join(ICONS_DIR, "rdp_icon.png"))
        self.icon_show = QIcon(os.path.join(ICONS_DIR, "show_icon.png"))
        self.icon_web = QIcon(os.path.join(ICONS_DIR, "web_icon.png"))
        self.icon_external = QIcon(os.path.join(ICONS_DIR, "external_icon.png"))
        self.icon_key = QIcon(os.path.join(ICONS_DIR, "key_icon.png"))

        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)

        self.setColumnWidth(3, 160)
        self.setColumnWidth(5, 220)
        header.setMinimumSectionSize(60)

        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.itemDoubleClicked.connect(self._on_comment_double_click)

        self.headerItem().setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)
        self.headerItem().setTextAlignment(3, Qt.AlignmentFlag.AlignCenter)
        self.headerItem().setTextAlignment(5, Qt.AlignmentFlag.AlignCenter)
        self.headerItem().setToolTip(5, "Двойной клик по ячейке — редактировать комментарий")

        self.setRootIsDecorated(True)
        self.setIndentation(18)
        self.setUniformRowHeights(False)

        # ===== Шрифты =====
        self._font_branch = QFont()
        self._font_branch.setBold(True)
        self._font_branch.setPointSize(10)

        self._font_server = QFont()
        self._font_server.setWeight(QFont.Weight.DemiBold)

        # ===== Цвета фона строк =====
        self._brush_branch_bg = QBrush(QColor(42, 54, 66))  # section header
        self._brush_port_up = QBrush(QColor(18, 48, 30))  # зелёный тинт
        self._brush_port_down = QBrush(QColor(58, 20, 20))  # красный тинт

        # ===== Цвета текста (QSS color убран — красим только программно) =====
        self._brush_text_branch = QBrush(QColor(0xCF, 0xD8, 0xDC))  # ветки / серверы
        self._brush_text_port = QBrush(QColor(0x9F, 0xBF, 0xC2))  # порты (дефолт)
        self._brush_text_down = QBrush(QColor(220, 100, 100))  # имя порта DOWN
        self._brush_text_muted = QBrush(
            QColor(130, 145, 160)
        )  # дата при DOWN без кредов

        # ===== Context menu вынесен =====
        self.context_menu = DeviceTreeContextMenu(self)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu.open)

    def set_user_settings(self, settings):
        self.user_settings = settings

    # ==================================================
    # RENDER
    # ==================================================

    def _save_tree_state(self):
        """Возвращает (expanded_branches, expanded_servers, selected)."""
        expanded_branches: set[str] = set()
        expanded_servers: set[int] = set()
        selected = None  # ("server", server_id, None) | ("port", server_id, port)

        for i in range(self.topLevelItemCount()):
            branch = self.topLevelItem(i)
            if branch.isExpanded():
                expanded_branches.add(branch.text(0))

            for j in range(branch.childCount()):
                server = branch.child(j)
                srv_id = server.data(0, ROLE_SERVER_ID)

                if server.isExpanded():
                    expanded_servers.add(srv_id)
                if server.isSelected():
                    selected = ("server", srv_id, None)

                for k in range(server.childCount()):
                    port_item = server.child(k)
                    if port_item.isSelected():
                        selected = (
                            "port",
                            port_item.data(0, ROLE_SERVER_ID),
                            port_item.data(0, ROLE_PORT),
                        )

        return expanded_branches, expanded_servers, selected

    def _restore_selection(self, selected):
        if not selected:
            return

        item_type, server_id, port = selected

        for i in range(self.topLevelItemCount()):
            branch = self.topLevelItem(i)
            for j in range(branch.childCount()):
                server = branch.child(j)
                if (
                    item_type == "server"
                    and server.data(0, ROLE_SERVER_ID) == server_id
                ):
                    self.setCurrentItem(server)
                    return
                for k in range(server.childCount()):
                    port_item = server.child(k)
                    if (
                        item_type == "port"
                        and port_item.data(0, ROLE_SERVER_ID) == server_id
                        and port_item.data(0, ROLE_PORT) == port
                    ):
                        self.setCurrentItem(port_item)
                        return

    def render(self, branches):
        expanded_branches, expanded_servers, selected = self._save_tree_state()

        self._stop_all_credential_timers()
        self.clear()

        for branch in branches:
            branch_item = QTreeWidgetItem([branch["name"], "", "", "", "", ""])
            branch_item.setFont(0, self._font_branch)
            branch_item.setSizeHint(0, QSize(0, 20))
            for col in range(6):
                branch_item.setBackground(col, self._brush_branch_bg)
                branch_item.setForeground(col, self._brush_text_branch)
            self.addTopLevelItem(branch_item)
            # Растягиваем название филиала на всю ширину — как section header
            self.setFirstColumnSpanned(
                self.topLevelItemCount() - 1, QModelIndex(), True
            )

            for srv in branch.get("servers", []):
                srv_comment = srv.get("comment") or ""
                server_item = QTreeWidgetItem([srv["name"], srv["ip"], "", "", "", srv_comment])
                server_item.setFont(0, self._font_server)
                server_item.setSizeHint(0, QSize(0, 15))
                for col in range(6):
                    server_item.setForeground(col, self._brush_text_branch)

                server_item.setData(0, ROLE_TYPE, "server")
                server_item.setData(0, ROLE_SERVER_ID, srv["id"])
                server_item.setData(0, ROLE_IP, srv["ip"])
                server_item.setData(
                    0, ROLE_DEVICE_TYPE, srv.get("device_type", "linux")
                )

                if srv_comment and srv.get("comment_updated_at"):
                    server_item.setToolTip(5, f"Изменён: {format_dt(srv['comment_updated_at'])}")

                branch_item.addChild(server_item)

                for p in srv.get("ports", []):

                    state = p.get("is_up")

                    if state is True:
                        status_text = "up"
                        icon = self.icon_up
                    elif state is False:
                        status_text = "down"
                        icon = self.icon_down
                    else:
                        status_text = "unknown"
                        icon = self.icon_unknown

                    port = p["port"]

                    port_comment = p.get("comment") or ""
                    port_item = QTreeWidgetItem(
                        [
                            f"port {port}",
                            "",
                            status_text,
                            "********",
                            format_dt(p.get("credentials_updated_at")),
                            port_comment,
                        ]
                    )

                    port_item.setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)
                    port_item.setTextAlignment(3, Qt.AlignmentFlag.AlignCenter)
                    port_item.setIcon(2, icon)
                    port_item.setSizeHint(0, QSize(0, 12))

                    # Дефолтный цвет текста для всех столбцов порта
                    # (QSS больше не задаёт color для item:!has-children,
                    #  поэтому выставляем программно — иначе будет белый)
                    for col in range(5):
                        port_item.setForeground(col, self._brush_text_port)

                    # Цвет фона и текста по статусу
                    if state is True:
                        for col in range(5):
                            port_item.setBackground(col, self._brush_port_up)
                    elif state is False:
                        for col in range(5):
                            port_item.setBackground(col, self._brush_port_down)
                        port_item.setForeground(0, self._brush_text_down)

                    # Подсветка даты смены пароля по % оставшегося срока
                    rotation_days = (
                        self.user_settings.get("password_rotation_days")
                        if self.user_settings
                        else None
                    )
                    age_color = _password_age_color(
                        p.get("credentials_updated_at"), rotation_days
                    )
                    if age_color is not None:
                        port_item.setForeground(4, QBrush(age_color))
                    elif state is False:
                        port_item.setForeground(4, self._brush_text_muted)

                    port_item.setData(0, ROLE_TYPE, "port")
                    port_item.setData(0, ROLE_SERVER_ID, srv["id"])
                    port_item.setData(0, ROLE_PORT, port)
                    port_item.setData(0, ROLE_IP, srv["ip"])

                    if port_comment and p.get("comment_updated_at"):
                        port_item.setToolTip(5, f"Изменён: {format_dt(p['comment_updated_at'])}")

                    tooltip = _build_port_tooltip(
                        state,
                        p.get("last_success"),
                        p.get("last_failure"),
                    )
                    port_item.setToolTip(0, tooltip)
                    port_item.setToolTip(2, tooltip)

                    server_item.addChild(port_item)

                expand_srv = not self._has_rendered or srv["id"] in expanded_servers
                server_item.setExpanded(expand_srv)

            expand_branch = (
                not self._has_rendered or branch["name"] in expanded_branches
            )
            branch_item.setExpanded(expand_branch)

        self._has_rendered = True
        self._restore_selection(selected)

    # ==================================================
    # CREDENTIALS
    # ==================================================

    def _find_port_item(self, server_id: int, port: int):
        for i in range(self.topLevelItemCount()):
            branch = self.topLevelItem(i)

            for j in range(branch.childCount()):
                server = branch.child(j)

                if server.data(0, ROLE_SERVER_ID) != server_id:
                    continue

                for k in range(server.childCount()):
                    port_item = server.child(k)

                    if port_item.data(0, ROLE_PORT) == port:
                        return port_item

        return None

    def update_port_item(self, server_id: int, port: int, port_data: dict):
        """Точечно обновляет строку порта без полного rebuild дерева."""
        item = self._find_port_item(server_id, port)
        if not item:
            return

        state = port_data.get("is_up")

        if state is True:
            item.setText(2, "up")
            item.setIcon(2, self.icon_up)
            for col in range(5):
                item.setBackground(col, self._brush_port_up)
                item.setForeground(col, self._brush_text_port)
        elif state is False:
            item.setText(2, "down")
            item.setIcon(2, self.icon_down)
            for col in range(5):
                item.setBackground(col, self._brush_port_down)
                item.setForeground(col, self._brush_text_port)
            item.setForeground(0, self._brush_text_down)
        else:
            item.setText(2, "unknown")
            item.setIcon(2, self.icon_unknown)
            for col in range(5):
                item.setBackground(col, QBrush())
                item.setForeground(col, self._brush_text_port)

        # Подсветка даты по % срока
        rotation_days = (
            self.user_settings.get("password_rotation_days")
            if self.user_settings
            else None
        )
        age_color = _password_age_color(
            port_data.get("credentials_updated_at"), rotation_days
        )
        if age_color is not None:
            item.setForeground(4, QBrush(age_color))
        elif state is False:
            item.setForeground(4, self._brush_text_muted)
        else:
            item.setForeground(4, self._brush_text_port)

        tooltip = _build_port_tooltip(
            state,
            port_data.get("last_success"),
            port_data.get("last_failure"),
        )
        item.setToolTip(0, tooltip)
        item.setToolTip(2, tooltip)

    def show_credentials(
        self,
        server_id: int,
        port: int,
        username: str,
        password: str,
        mnemonic: str = "",
    ):
        item = self._find_port_item(server_id, port)
        if not item:
            return

        key = (server_id, port)

        if key in self._credential_timers:
            timer = self._credential_timers.pop(key)
            timer.stop()
            timer.deleteLater()

        item.setText(3, f"{username}:{password}")
        self.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        if mnemonic:
            item.setToolTip(3, f'<span style="color:#4CAF50">{mnemonic}</span>')

        timer = QTimer(self)
        timer.setSingleShot(True)

        # Запоминаем что положили в буфер — чтобы очистить его при сбросе
        _shown_value = f"{username}:{password}"

        def clear():
            item.setText(3, "********")
            item.setToolTip(3, "")
            self.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(3, 160)
            # Очищаем буфер если там ещё наш пароль
            from PyQt6.QtGui import QGuiApplication
            cb = QGuiApplication.clipboard()
            if cb.text() in (_shown_value, username, password):
                cb.clear()
            timer.deleteLater()
            self._credential_timers.pop(key, None)

        timer.timeout.connect(clear)
        timer.start(CREDENTIALS_SHOW_TIMEOUT_MS)

        self._credential_timers[key] = timer

    def _stop_all_credential_timers(self):
        for timer in self._credential_timers.values():
            timer.stop()
            timer.deleteLater()
        self._credential_timers.clear()
        self.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(3, 160)

    # ==================================================
    # INLINE COMMENT EDITING
    # ==================================================

    def _on_comment_double_click(self, item, column):
        if column != 5:
            return
        item_type = item.data(0, ROLE_TYPE)
        if item_type not in ("server", "port"):
            return

        server_id = item.data(0, ROLE_SERVER_ID)
        port = item.data(0, ROLE_PORT) or 0
        current_comment = item.text(5)

        if item_type == "server":
            title = item.text(0)
            subtitle = item.text(1)          # IP
        else:
            parent_item = item.parent()
            title = parent_item.text(0) if parent_item else ""
            subtitle = f"{parent_item.text(1)}  ·  порт {port}" if parent_item else f"порт {port}"

        dlg = _CommentDialog(title, subtitle, current_comment, self.window())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_comment = dlg.get_text()
            item.setText(5, new_comment)
            self.comment_changed.emit(item_type, server_id, port, new_comment)

    def update_comment_item(self, item_type: str, server_id: int, port: int,
                            comment: str, updated_at: str):
        """Обновляет ячейку комментария и тултип после сохранения в БД."""
        for i in range(self.topLevelItemCount()):
            branch = self.topLevelItem(i)
            for j in range(branch.childCount()):
                server = branch.child(j)
                if item_type == "server" and server.data(0, ROLE_SERVER_ID) == server_id:
                    server.setText(5, comment)
                    server.setToolTip(5, f"Изменён: {format_dt(updated_at)}" if updated_at else "")
                    return
                if item_type == "port":
                    if server.data(0, ROLE_SERVER_ID) != server_id:
                        continue
                    for k in range(server.childCount()):
                        p_item = server.child(k)
                        if p_item.data(0, ROLE_PORT) == port:
                            p_item.setText(5, comment)
                            p_item.setToolTip(5, f"Изменён: {format_dt(updated_at)}" if updated_at else "")
                            return
