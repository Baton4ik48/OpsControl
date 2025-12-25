# project/gui/table_menu.py
from PyQt6.QtWidgets import QMenu
from PyQt6.QtWidgets import QApplication

class TableContextMenu:
    def __init__(self, parent):
        """
        parent — экземпляр MainWindow
        """
        self.parent = parent

    def create_menu(self, qtree_item):
        """
        Принимаем сам QTreeWidgetItem (branch или server).
        qtree_item.row_data должен быть dict с ключом 'type'.
        """
        menu = QMenu()

        row_data = getattr(qtree_item, "row_data", None)
        if not row_data:
            # если нет метаданных — ничего не делаем
            return menu

        t = row_data.get("type")
        if t == "branch":
            menu.addAction("Обновить все сервера", lambda: self.update_branch(qtree_item))
            #menu.addAction("Загрузить конфиг филиала (редактировать)", lambda: self.edit_branch(qtree_item))
        elif t == "server":
            menu.addAction("Обновить сервер", lambda: self.update_server(qtree_item))
            #menu.addAction("Копировать IP", lambda: self.copy_ip(qtree_item))

        return menu

    def update_branch(self, branch_item):
        # branch_item — QTreeWidgetItem
        self.parent.update_branch(branch_item)

    def update_server(self, server_item):
        # server_item — QTreeWidgetItem
        self.parent.update_device(server_item)

    def edit_branch(self, branch_item):
        # заглушка — можно сделать диалог редактирования
        print("edit branch:", branch_item.row_data.get("name"))

    def copy_ip(self, server_item):
        ip = server_item.row_data.get("ip", "")

        if not ip:
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(ip)

