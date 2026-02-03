import os
from datetime import datetime, timezone

from PyQt6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal

from core.paths import ICONS_DIR
from core.port_checker import get_label

ROLE_TYPE = Qt.ItemDataRole.UserRole + 1
ROLE_SERVER_ID = Qt.ItemDataRole.UserRole + 2
ROLE_PORT = Qt.ItemDataRole.UserRole + 3

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

    def __init__(self):
        super().__init__()

        self.setHeaderLabels(["Устройство", "IP", "Статус"])

        self.icon_up = QIcon(os.path.join(ICONS_DIR, "status_up.png"))
        self.icon_down = QIcon(os.path.join(ICONS_DIR, "status_down.png"))
        self.icon_unknown = QIcon(os.path.join(ICONS_DIR, "status_unknown.png"))
        self.icon_update = QIcon(os.path.join(ICONS_DIR, "update_icon.png"))
        self.icon_ssh = QIcon(os.path.join(ICONS_DIR, "ssh_icon.png"))

        
        self.setColumnWidth(0, 240)
        self.setColumnWidth(1, 150)

        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        self.setRootIsDecorated(True)
        self.setIndentation(18)
        self.setUniformRowHeights(True)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)

    def render(self, branches):
        self.clear()

        for branch in branches:
            branch_item = QTreeWidgetItem([branch["name"], "", ""])
            self.addTopLevelItem(branch_item)

            for srv in branch.get("servers", []):
                server_item = QTreeWidgetItem([
                    srv["name"],
                    srv["ip"],
                    ""
                ])

                server_item.setData(0, ROLE_TYPE, "server")
                server_item.setData(0, ROLE_SERVER_ID, srv["id"])


                branch_item.addChild(server_item)

                for p in srv.get("ports", []):
                    state = p.get("is_up")

                    if state is True:
                        text, icon = "up", self.icon_up
                    elif state is False:
                        text, icon = "down", self.icon_down
                    else:
                        text, icon = "unknown", self.icon_unknown

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
                        text
                    ])
                    port_item.setIcon(2, icon)

                    port_item.setData(0, ROLE_TYPE, "port")
                    port_item.setData(0, ROLE_SERVER_ID, srv["id"])
                    port_item.setData(0, ROLE_PORT, port)


                    port_item.setToolTip(0, tooltip)
                    port_item.setToolTip(2, tooltip)

                    server_item.addChild(port_item)

                server_item.setExpanded(True)

            branch_item.setExpanded(True)

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
            # print(f"ROLE_SERVER_ID",server_id)
            
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
            # print(f"ROLE_SERVER_ID",server_id)
            # print(f"ROLE_PORT",port)

            refresh_port_action = menu.addAction(
                self.icon_update,
                "Обновить порт"
            )
            refresh_port_action.triggered.connect(
                lambda: self.refresh_port_requested.emit(server_id, port)
            )

        menu.exec(self.viewport().mapToGlobal(pos))

