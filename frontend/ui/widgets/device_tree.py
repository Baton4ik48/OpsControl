import os
from datetime import datetime, timezone

from PyQt6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from core.paths import ICONS_DIR
from ui.context_menus.device_tree_context_menu import DeviceTreeContextMenu


ROLE_TYPE = Qt.ItemDataRole.UserRole + 1
ROLE_SERVER_ID = Qt.ItemDataRole.UserRole + 2
ROLE_PORT = Qt.ItemDataRole.UserRole + 3
ROLE_IP = Qt.ItemDataRole.UserRole + 4

CREDENTIALS_SHOW_TIMEOUT_MS = 1 * 60 * 1000


def format_dt(value):
    if not value:
        return "нет данных"

    dt = datetime.fromisoformat(value)
    local = dt.replace(tzinfo=timezone.utc).astimezone()
    return local.strftime("%d.%m.%Y %H:%M")


def _icon_img(icon_path, size=13):
    return f'<img src="file://{icon_path}" width="{size}" height="{size}">'


def _build_port_tooltip(state, last_success, last_failure):
    icon_up   = os.path.join(ICONS_DIR, "status_up.png")
    icon_down = os.path.join(ICONS_DIR, "status_down.png")

    rows = []

    if state is True:
        rows.append(
            f'<tr><td>{_icon_img(icon_up)}</td>'
            f'<td>&nbsp;<b>Онлайн</b></td></tr>'
        )
        if last_failure:
            rows.append(
                f'<tr><td>{_icon_img(icon_down)}</td>'
                f'<td>&nbsp;Последний раз недоступен:&nbsp;{format_dt(last_failure)}</td></tr>'
            )

    elif state is False:
        if last_success:
            rows.append(
                f'<tr><td>{_icon_img(icon_down)}</td>'
                f'<td>&nbsp;Последний раз был в сети:&nbsp;{format_dt(last_success)}</td></tr>'
            )
        else:
            rows.append(
                f'<tr><td>{_icon_img(icon_down)}</td>'
                f'<td>&nbsp;В сети не наблюдался</td></tr>'
            )

    else:
        if last_success:
            rows.append(
                f'<tr><td>{_icon_img(icon_up)}</td>'
                f'<td>&nbsp;Последний раз в сети:&nbsp;{format_dt(last_success)}</td></tr>'
            )
        if last_failure:
            rows.append(
                f'<tr><td>{_icon_img(icon_down)}</td>'
                f'<td>&nbsp;Последний раз недоступен:&nbsp;{format_dt(last_failure)}</td></tr>'
            )
        if not last_success and not last_failure:
            rows.append('<tr><td colspan="2">Статус неизвестен</td></tr>')

    return f'<table cellspacing="3">{"".join(rows)}</table>'


class DeviceTree(QTreeWidget):

    # делаем роли доступными для context menu
    ROLE_TYPE = ROLE_TYPE
    ROLE_SERVER_ID = ROLE_SERVER_ID
    ROLE_PORT = ROLE_PORT
    ROLE_IP = ROLE_IP

    refresh_server_requested = pyqtSignal(int, str)
    refresh_port_requested = pyqtSignal(int, int, str)
    open_protocol_requested = pyqtSignal(int, int, str, str)
    show_credentials_requested = pyqtSignal(int, int, str)
    rotate_password_requested = pyqtSignal(int, str)  # server_id, ip

    def __init__(self):
        super().__init__()

        self._credential_timers = {}
        self._has_rendered = False

        self.setHeaderLabels([
            "Устройство",
            "IP",
            "Статус",
            "Учётные данные",
            "Дата обновления пароля"
        ])

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

        self.setColumnWidth(3, 160)
        header.setMinimumSectionSize(60)

        self.headerItem().setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)
        self.headerItem().setTextAlignment(3, Qt.AlignmentFlag.AlignCenter)

        self.setRootIsDecorated(True)
        self.setIndentation(18)
        self.setUniformRowHeights(True)

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
                if item_type == "server" and server.data(0, ROLE_SERVER_ID) == server_id:
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
            branch_item = QTreeWidgetItem([branch["name"], "", "", "", ""])
            self.addTopLevelItem(branch_item)

            for srv in branch.get("servers", []):
                server_item = QTreeWidgetItem([
                    srv["name"],
                    srv["ip"],
                    "",
                    "",
                    ""
                ])

                server_item.setData(0, ROLE_TYPE, "server")
                server_item.setData(0, ROLE_SERVER_ID, srv["id"])
                server_item.setData(0, ROLE_IP, srv["ip"])

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

                    port_item = QTreeWidgetItem([
                        f"port {port}",
                        "",
                        status_text,
                        "********",
                        format_dt(p.get("credentials_updated_at"))
                    ])

                    port_item.setTextAlignment(3, Qt.AlignmentFlag.AlignCenter)
                    port_item.setIcon(2, icon)

                    port_item.setData(0, ROLE_TYPE, "port")
                    port_item.setData(0, ROLE_SERVER_ID, srv["id"])
                    port_item.setData(0, ROLE_PORT, port)
                    port_item.setData(0, ROLE_IP, srv["ip"])

                    tooltip = _build_port_tooltip(
                        state,
                        p.get("last_success"),
                        p.get("last_failure"),
                    )
                    port_item.setToolTip(0, tooltip)
                    port_item.setToolTip(2, tooltip)

                    server_item.addChild(port_item)

                expand_srv = (
                    not self._has_rendered or srv["id"] in expanded_servers
                )
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

    def show_credentials(self, server_id: int, port: int, username: str, password: str):
        item = self._find_port_item(server_id, port)
        if not item:
            return

        key = (server_id, port)

        if key in self._credential_timers:
            timer = self._credential_timers.pop(key)
            timer.stop()
            timer.deleteLater()

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

    def _stop_all_credential_timers(self):
        for timer in self._credential_timers.values():
            timer.stop()
            timer.deleteLater()
        self._credential_timers.clear()