import os
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QHeaderView
from PyQt6.QtGui import QIcon
from core.paths import ICONS_DIR


class DeviceTree(QTreeWidget):
    def __init__(self):
        super().__init__()

        self.setHeaderLabels(["Устройство", "IP", "Статус"])

        self.icon_up = QIcon(os.path.join(ICONS_DIR, "status_up.png"))
        self.icon_down = QIcon(os.path.join(ICONS_DIR, "status_down.png"))
        self.icon_unknown = QIcon(os.path.join(ICONS_DIR, "status_unknown.png"))

        self.setColumnWidth(0, 240)
        self.setColumnWidth(1, 150)

        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        self.setRootIsDecorated(True)
        self.setIndentation(18)
        self.setUniformRowHeights(True)

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
                branch_item.addChild(server_item)

                for p in srv.get("ports", []):
                    state = p.get("is_up")

                    if state is True:
                        text, icon = "up", self.icon_up
                    elif state is False:
                        text, icon = "down", self.icon_down
                    else:
                        text, icon = "unkown", self.icon_unknown

                    port_item = QTreeWidgetItem([
                        f"port {p['port']}",
                        "",
                        text
                    ])
                    port_item.setIcon(2, icon)

                    server_item.addChild(port_item)

                server_item.setExpanded(True)

            branch_item.setExpanded(True)
