from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt


class InfrastructureTree(QTreeWidget):
    def __init__(self):
        super().__init__()

        self.setHeaderLabels(["Infrastructure"])

    # =========================================================
    # RENDER
    # =========================================================
    def render(self, data):
        self.clear()

        for branch in data:
            branch_item = QTreeWidgetItem([branch["name"]])
            branch_item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                ("branch", branch["id"])
            )
            self.addTopLevelItem(branch_item)

            for server in branch["servers"]:
                server_item = QTreeWidgetItem(
                    [f"{server['name']} ({server['ip']})"]
                )
                server_item.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    ("server", server["id"], server)
                )
                branch_item.addChild(server_item)

                for port in server["ports"]:
                    cred_icon = "✔" if port["has_credentials"] else "✖"

                    port_item = QTreeWidgetItem(
                        [f"{port['port']} {cred_icon}"]
                    )

                    port_item.setData(
                        0,
                        Qt.ItemDataRole.UserRole,
                        ("port", server["id"], port)
                    )

                    vault_path = port.get("vault_path")
                    if vault_path:
                        port_item.setToolTip(0, f"Vault path: {vault_path}")

                    server_item.addChild(port_item)

        # self.expandAll()