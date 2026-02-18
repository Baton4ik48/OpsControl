from PyQt6.QtWidgets import QMenuBar
from ui.dialogs.firewall_dialog import FirewallDialog


class ToolsMenu(QMenuBar):
    def __init__(self, parent=None):
        super().__init__(parent)

        tools_menu = self.addMenu("Инструменты")

        firewall_action = tools_menu.addAction("Генератор firewall правил")
        firewall_action.triggered.connect(self.open_firewall_generator)

    def open_firewall_generator(self):
        dlg = FirewallDialog(self)
        dlg.setModal(True)
        dlg.exec()

