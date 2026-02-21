from PyQt6.QtWidgets import QMenuBar
from ui.dialogs.firewall_dialog import FirewallDialog
from ui.dialogs.manager_dialog import InfrastructureManagerDialog


class ToolsMenu(QMenuBar):
    def __init__(self, parent=None):
        super().__init__(parent)

        tools_menu = self.addMenu("Инструменты")

        # =========================
        # xFirewall
        # =========================
        xfirewall_menu = tools_menu.addMenu("xFirewall")

        firewall_action = xfirewall_menu.addAction("Сгенерировать правила")
        firewall_action.triggered.connect(self.open_firewall_generator)

        # =========================
        # Infrastructure Manager
        # =========================
        tools_menu.addSeparator()

        infra_action = tools_menu.addAction("Управление инфраструктурой")
        infra_action.triggered.connect(self.open_infrastructure_manager)

    # -------------------------------------

    def open_firewall_generator(self):
        dlg = FirewallDialog(self)
        dlg.setModal(True)
        dlg.exec()

    # -------------------------------------

    def open_infrastructure_manager(self):
        dlg = InfrastructureManagerDialog(self)
        dlg.setModal(True)
        dlg.exec()