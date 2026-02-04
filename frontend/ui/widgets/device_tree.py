import os
from datetime import datetime, timezone

from PyQt6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from core.paths import ICONS_DIR
from core.port_checker import get_label

ROLE_TYPE = Qt.ItemDataRole.UserRole + 1
ROLE_SERVER_ID = Qt.ItemDataRole.UserRole + 2
ROLE_PORT = Qt.ItemDataRole.UserRole + 3
ROLE_IP = Qt.ItemDataRole.UserRole + 4

CREDENTIALS_SHOW_TIMEOUT_MS = 2 * 60 * 1000  # 2 минуты


def format_dt(value):
    if not value:
        return "нет данных"

    dt = datetime.fromisoformat(value)
    local = dt.replace(tzinfo=timezone.utc).astimezone()
    return local.strftime("%d.%m.%Y %H:%M")


class DeviceTree(QTreeWidget):
    refresh_server_requested = pyqtSignal(int)
    refresh_port_requested = pyqtSignal(int, int)
    open_ssh_requested = pyqtSignal(int)
    show_credentials_requested = pyqtSignal(int, int, str)

    def __init__(self):
        super().__init__()
        self._credential_timers = {}

        self.setHeaderLabels(["Устройство", "IP", "Статус", "Учётные данные", "Дата обновления пароля"])

        self.icon_up = QIcon(os.path.join(ICONS_DIR, "status_up.png"))
        self.icon_down = QIcon(os.path.join(ICONS_DIR, "status_down.png"))
        self.icon_unknown = QIcon(os.path.join(ICONS_DIR, "status_unknown.png"))
        self.icon_update = QIcon(os.path.join(ICONS_DIR, "update_icon.png"))
        self.icon_ssh = QIcon(os.path.join(ICONS_DIR, "ssh_icon.png"))
        self.icon_show = QIcon(os.path.join(ICONS_DIR, "show_icon.png"))

        
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(3, 140)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setMinimumSectionSize(60)

        self.headerItem().setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)
        self.headerItem().setTextAlignment(3, Qt.AlignmentFlag.AlignCenter)



        self.setRootIsDecorated(True)
        self.setIndentation(18)
        self.setUniformRowHeights(True)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)

    # ==================================================
    # RENDER
    # ==================================================
    
    def render(self, branches):
        self.clear()

        for branch in branches:
            branch_item = QTreeWidgetItem([branch["name"], "", "", "", ""])
            self.addTopLevelItem(branch_item)

            for srv in branch.get("servers", []):
                server_item = QTreeWidgetItem([srv["name"], srv["ip"], "", "", ""])

                server_item.setData(0, ROLE_TYPE, "server")
                server_item.setData(0, ROLE_SERVER_ID, srv["id"])
                server_item.setData(0, ROLE_IP, srv["ip"])



                branch_item.addChild(server_item)

                for p in srv.get("ports", []):
                    state = p.get("is_up")

                    if state is True:
                        status_text, icon = "up", self.icon_up
                    elif state is False:
                        status_text, icon = "down", self.icon_down
                    else:
                        status_text, icon = "unknown", self.icon_unknown

                    has_creds = p.get("has_credentials", False)
                    creds_text = "********"
                    creds_date = format_dt(p.get("credentials_updated_at"))

                    port = p["port"]
                    label = get_label(port)

                    if state is True:
                        tooltip = (
                            f"<b>Порт:</b> {port} ({label})<br><br>"
                            f"<b>Статус:</b> UP<br><br>"
                            f"<b>Последний разрыв связи:</b><br>"
                            f"{format_dt(p.get('last_failure'))}"
                        )
                    elif state is False:
                        tooltip = (
                            f"<b>Порт:</b> {port} ({label})<br><br>"
                            f"<b>Статус:</b> DOWN<br><br>"
                            f"<b>Последний сеанс связи:</b><br>"
                            f"{format_dt(p.get('last_success'))}"
                        )
                    else:
                        tooltip = (
                            f"<b>Порт:</b> {port} ({label})<br><br>"
                            f"<b>Статус:</b> неизвестно"
                        )

                    port_item = QTreeWidgetItem([
                        f"port {port}",
                        "",
                        status_text,
                        creds_text,
                        creds_date
                    ])
                    port_item.setTextAlignment(3, Qt.AlignmentFlag.AlignCenter)

                    port_item.setIcon(2, icon)

                    port_item.setData(0, ROLE_TYPE, "port")
                    port_item.setData(0, ROLE_SERVER_ID, srv["id"])
                    port_item.setData(0, ROLE_PORT, port)
                    port_item.setData(0, ROLE_IP, srv["ip"])



                    port_item.setToolTip(0, tooltip)
                    port_item.setToolTip(2, tooltip)

                    server_item.addChild(port_item)

                server_item.setExpanded(True)

            branch_item.setExpanded(True)

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

    def _open_context_menu(self, pos):
        item = self.itemAt(pos)
        if not item:
            return

        item_type = item.data(0, ROLE_TYPE)
        if not item_type:
            return

        menu = QMenu(self)

        # ===== SERVER =====
        if item_type == "server":
            server_id = item.data(0, ROLE_SERVER_ID)
            
            ssh_action = menu.addAction(self.icon_ssh, "SSH (Терминал)")
            ssh_action.triggered.connect(
                lambda: self.open_ssh_requested.emit(server_id)
            )

            refresh_action = menu.addAction(self.icon_update, "Обновить сервер")
            refresh_action.triggered.connect(
                lambda: self.refresh_server_requested.emit(server_id)
            )

        # ===== PORT =====
        elif item_type == "port":
            server_id = item.data(0, ROLE_SERVER_ID)
            port = item.data(0, ROLE_PORT)
            ip = item.data(0, ROLE_IP)

            refresh_port_action = menu.addAction(
                self.icon_update,
                "Обновить порт"
            )
            refresh_port_action.triggered.connect(
                lambda: self.refresh_port_requested.emit(server_id, port)
            )

            show_creds_action = menu.addAction(self.icon_show, "Показать учётные данные")
            show_creds_action.triggered.connect(
                lambda: self.show_credentials_requested.emit(server_id, port, ip)
            )
            menu.addSeparator()

        menu.exec(self.viewport().mapToGlobal(pos))

    def show_credentials(self, server_id: int, port: int, username: str, password: str):
        item = self._find_port_item(server_id, port)
        if not item:
            return

        key = (server_id, port)

        # если уже был показ — сбрасываем таймер
        if key in self._credential_timers:
            timer = self._credential_timers.pop(key)
            timer.stop()
            timer.deleteLater()

        # показываем креды
        item.setText(3, f"{username}:{password}")

        timer = QTimer(self)
        timer.setSingleShot(True)

        def clear():
            item.setText(3, "********")
            timer.deleteLater()
            self._credential_timers.pop(key, None)

        timer.timeout.connect(clear)
        timer.start(CREDENTIALS_SHOW_TIMEOUT_MS)

        self._credential_timers[key] = timer
