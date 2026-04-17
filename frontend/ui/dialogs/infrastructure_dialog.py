from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QSplitter,
    QLabel,
    QStackedWidget,
    QMessageBox,
    QInputDialog,
    QWidget,
)
from PyQt6.QtCore import Qt
from controllers.infrastructure_controller import InfrastructureController
from ui.widgets.busy_overlay import BusyOverlay
from ui.dialogs.infrastructureDialog.infrastructure_tree import InfrastructureTree
from ui.dialogs.infrastructureDialog.server_form import is_valid_host
from ui.context_menus.infrastructure_context_menu import InfrastructureContextMenu
from ui.dialogs.infrastructureDialog.server_form import ServerForm
from ui.dialogs.infrastructureDialog.port_form import PortForm
from ui.dialogs.infrastructureDialog.branch_form import BranchForm


class InfrastructureManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Управление инфраструктурой")
        self.resize(1100, 600)

        self.busy = BusyOverlay(self)
        self.controller = InfrastructureController(self, self.busy)

        # ===== MAIN LAYOUT =====
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # =========================================================
        # LEFT SIDE (TREE)
        # =========================================================

        self.tree = InfrastructureTree()
        splitter.addWidget(self.tree)

        self.context_menu = InfrastructureContextMenu(self)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.context_menu.open)
        self.tree.itemClicked.connect(self.on_item_selected)

        # =========================================================
        # RIGHT SIDE (REAL CENTER)
        # =========================================================

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addStretch()

        self.stack = QStackedWidget()
        self.stack.setMaximumWidth(420)
        self.stack.setSizePolicy(
            self.stack.sizePolicy().horizontalPolicy(),
            self.stack.sizePolicy().verticalPolicy(),
        )

        right_layout.addWidget(self.stack, alignment=Qt.AlignmentFlag.AlignHCenter)

        right_layout.addStretch()

        splitter.addWidget(right_container)

        splitter.setSizes([750, 350])

        # =========================================================
        # STACK CONTENT
        # =========================================================

        self.empty_widget = QLabel("Выберите элемент")
        self.empty_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.empty_widget)

        self.branch_form = BranchForm()
        self.server_form = ServerForm()
        self.port_form = PortForm()

        self.stack.addWidget(self.branch_form)
        self.stack.addWidget(self.server_form)
        self.stack.addWidget(self.port_form)

        # =========================================================
        # FORM SIGNALS
        # =========================================================

        self.server_form.saved.connect(self.controller.save_server)
        self.server_form.error.connect(self.show_error)

        self.port_form.saved.connect(self.controller.save_port)
        self.port_form.error.connect(self.show_error)

        self.branch_form.saved.connect(self.controller.save_branch)
        self.branch_form.error.connect(self.show_error)

    # =========================================================
    # LOAD ONCE
    # =========================================================

    def showEvent(self, event):
        super().showEvent(event)

        if not hasattr(self, "_loaded"):
            self._loaded = True
            self.controller.load_tree_async()

    # =========================================================
    # VIEW API (для контроллера)
    # =========================================================

    def render_tree(self, data):
        self.tree.render(data)

    def show_server_form(self, server_data):
        self.server_form.set_data(server_data)
        self.stack.setCurrentWidget(self.server_form)

    def show_port_form(self, server_id, port_data):
        self.port_form.set_data(server_id, port_data)
        self.stack.setCurrentWidget(self.port_form)

    def show_branch_form(self, branch_data):
        self.branch_form.set_data(branch_data)
        self.stack.setCurrentWidget(self.branch_form)

    def show_api_error(self, message):
        QMessageBox.critical(self, "Ошибка API", message)

    def show_error(self, message):
        QMessageBox.critical(self, "Ошибка", message)

    def reset_selection(self):
        self.tree.clearSelection()
        self.stack.setCurrentWidget(self.empty_widget)

    # =========================================================
    # TREE EVENTS
    # =========================================================

    def on_item_selected(self, item):
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if not data:
            self.stack.setCurrentWidget(self.empty_widget)
            return

        if data[0] == "server":
            _, server_id, server_data = data
            self.controller.select_server(server_id, server_data)

        elif data[0] == "port":
            _, server_id, port_data = data
            self.controller.select_port(server_id, port_data)

        elif data[0] == "branch":
            _, branch_id = data
            self.controller.select_branch(branch_id)

    # =========================================================
    # ADD / DELETE (используются ContextMenu)
    # =========================================================

    def add_server_dialog(self, branch_id):
        name, ok1 = QInputDialog.getText(self, "Новый сервер", "Название сервера:")
        if not ok1 or not name.strip():
            return

        ip, ok2 = QInputDialog.getText(self, "Новый сервер", "IP сервера:")
        if not ok2 or not ip.strip():
            return

        if not is_valid_host(ip.strip()):
            self.show_error("Введите корректный IP-адрес или доменное имя")
            return

        self.controller.create_server(branch_id, name.strip(), ip.strip())

    def add_port_dialog(self, server_id):
        port_text, ok = QInputDialog.getText(self, "Новый порт", "Номер порта:")
        if not ok or not port_text.strip():
            return

        if not port_text.isdigit():
            self.show_error("Порт должен быть числом")
            return

        port = int(port_text)
        if not (1 <= port <= 65535):
            self.show_error("Порт должен быть от 1 до 65535")
            return

        self.controller.create_port(server_id, port)

    def add_branch_dialog(self):
        name, ok = QInputDialog.getText(self, "Новый филиал", "Название филиала:")
        if ok and name.strip():
            self.controller.create_branch(name.strip())

    def confirm_delete_branch(self, branch_id):
        if (
            QMessageBox.question(
                self,
                "Удаление филиала",
                "Вы уверены? Будут удалены все серверы, порты и учетные данные.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.controller.delete_branch(branch_id)

    def confirm_delete_server(self, server_id):
        if (
            QMessageBox.question(
                self,
                "Удаление сервера",
                "Вы уверены? Будут удалены все порты и учетные данные.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.controller.delete_server(server_id)

    def confirm_delete_port(self, server_id, port):
        if (
            QMessageBox.question(
                self,
                "Удаление порта",
                "Вы уверены?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.controller.delete_port(server_id, port)
