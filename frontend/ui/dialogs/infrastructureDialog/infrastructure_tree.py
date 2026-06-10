from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QAbstractItemView
from PyQt6.QtCore import Qt

class InfrastructureTree(QTreeWidget):
    def __init__(self):
        super().__init__()

        self.setHeaderLabels(["Infrastructure"])
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def get_selected_ports(self) -> list[tuple[int, int]]:
        """Возвращает список (server_id, port) для всех выделенных портов."""
        result = []
        for item in self.selectedItems():
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data[0] == "port":
                _, server_id, port_data = data
                result.append((server_id, port_data["port"]))
        return result

    def _save_tree_state(self):
        expanded_branches: set[int] = set()
        expanded_servers: set[int] = set()
        selected = None  # ("branch", branch_id) | ("server", server_id) | ("port", server_id, port_num)

        for i in range(self.topLevelItemCount()):
            branch = self.topLevelItem(i)
            d = branch.data(0, Qt.ItemDataRole.UserRole)
            if not d:
                continue
            branch_id = d[1]

            if branch.isExpanded():
                expanded_branches.add(branch_id)
            if branch.isSelected():
                selected = ("branch", branch_id)

            for j in range(branch.childCount()):
                server = branch.child(j)
                sd = server.data(0, Qt.ItemDataRole.UserRole)
                if not sd:
                    continue
                server_id = sd[1]

                if server.isExpanded():
                    expanded_servers.add(server_id)
                if server.isSelected():
                    selected = ("server", server_id)

                for k in range(server.childCount()):
                    port_item = server.child(k)
                    pd = port_item.data(0, Qt.ItemDataRole.UserRole)
                    if pd and port_item.isSelected():
                        selected = ("port", pd[1], pd[2]["port"])

        return expanded_branches, expanded_servers, selected

    def _restore_tree_state(self, expanded_branches, expanded_servers, selected):
        for i in range(self.topLevelItemCount()):
            branch = self.topLevelItem(i)
            d = branch.data(0, Qt.ItemDataRole.UserRole)
            if not d:
                continue
            branch_id = d[1]

            if branch_id in expanded_branches:
                branch.setExpanded(True)
            if selected and selected[0] == "branch" and selected[1] == branch_id:
                self.setCurrentItem(branch)

            for j in range(branch.childCount()):
                server = branch.child(j)
                sd = server.data(0, Qt.ItemDataRole.UserRole)
                if not sd:
                    continue
                server_id = sd[1]

                if server_id in expanded_servers:
                    server.setExpanded(True)
                if selected and selected[0] == "server" and selected[1] == server_id:
                    self.setCurrentItem(server)

                for k in range(server.childCount()):
                    port_item = server.child(k)
                    pd = port_item.data(0, Qt.ItemDataRole.UserRole)
                    if (
                        pd
                        and selected
                        and selected[0] == "port"
                        and pd[1] == selected[1]
                        and pd[2]["port"] == selected[2]
                    ):
                        self.setCurrentItem(port_item)

    def render(self, data):
        expanded_branches, expanded_servers, selected = self._save_tree_state()

        self.clear()

        for branch in data:
            branch_item = QTreeWidgetItem([branch["name"]])
            branch_item.setData(0, Qt.ItemDataRole.UserRole, ("branch", branch["id"]))
            self.addTopLevelItem(branch_item)

            for server in branch["servers"]:
                server_item = QTreeWidgetItem([f"{server['name']} ({server['ip']})"])
                server_item.setData(
                    0, Qt.ItemDataRole.UserRole, ("server", server["id"], server)
                )
                branch_item.addChild(server_item)

                for port in server["ports"]:
                    cred_icon = "✔" if port["has_credentials"] else "✖"

                    port_item = QTreeWidgetItem([f"{port['port']} {cred_icon}"])

                    port_item.setData(
                        0, Qt.ItemDataRole.UserRole, ("port", server["id"], port)
                    )

                    vault_path = port.get("vault_path")
                    if vault_path:
                        port_item.setToolTip(0, f"Vault path: {vault_path}")

                    server_item.addChild(port_item)

        self._restore_tree_state(expanded_branches, expanded_servers, selected)
