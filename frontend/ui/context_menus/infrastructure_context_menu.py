from PyQt6.QtWidgets import QMenu
from PyQt6.QtCore import Qt


class InfrastructureContextMenu:
    def __init__(self, parent_dialog):
        """
        parent_dialog — это InfrastructureManagerDialog
        Нужен для вызова методов add/delete
        """
        self.dialog = parent_dialog
        self.tree = parent_dialog.tree
        self.controller = parent_dialog.controller

    # =========================================================
    # OPEN
    # =========================================================
    def open(self, position):
        item = self.tree.itemAt(position)
        menu = QMenu(self.dialog)

        # ===== ПУСТОЕ МЕСТО =====
        if item is None:
            action = menu.addAction("Добавить филиал")

            if menu.exec(self.tree.viewport().mapToGlobal(position)) == action:
                self.dialog.add_branch_dialog()
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        # ===== BRANCH =====
        if data[0] == "branch":
            _, branch_id = data

            add_server = menu.addAction("Добавить сервер")
            delete_branch = menu.addAction("Удалить филиал")

            action = menu.exec(self.tree.viewport().mapToGlobal(position))

            if action == add_server:
                self.dialog.add_server_dialog(branch_id)

            elif action == delete_branch:
                self.dialog.confirm_delete_branch(branch_id)

        # ===== SERVER =====
        elif data[0] == "server":
            _, server_id, _ = data

            add_port = menu.addAction("Добавить порт")
            delete_server = menu.addAction("Удалить сервер")

            action = menu.exec(self.tree.viewport().mapToGlobal(position))

            if action == add_port:
                self.dialog.add_port_dialog(server_id)

            elif action == delete_server:
                self.dialog.confirm_delete_server(server_id)

        # ===== PORT =====
        elif data[0] == "port":
            _, server_id, port_data = data

            delete_port = menu.addAction("Удалить порт")

            if menu.exec(self.tree.viewport().mapToGlobal(position)) == delete_port:
                self.dialog.confirm_delete_port(server_id, port_data["port"])