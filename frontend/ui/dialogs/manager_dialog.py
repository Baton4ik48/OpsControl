from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QWidget, QFormLayout, QLineEdit, QPushButton,
    QSplitter, QLabel, QStackedWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator
import ipaddress

from controllers.infrastructure_controller import InfrastructureController


class InfrastructureManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Управление инфраструктурой")
        self.resize(1100, 600)

        # Контроллер
        self.controller = InfrastructureController(self)

        # ===== UI =====
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # TREE
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Infrastructure"])
        splitter.addWidget(self.tree)

        # RIGHT PANEL
        self.stack = QStackedWidget()
        splitter.addWidget(self.stack)

        self.empty_widget = QLabel("Выберите элемент")
        self.empty_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.empty_widget)

        self.branch_form = self.create_branch_form()
        self.stack.addWidget(self.branch_form)

        self.server_form = self.create_server_form()
        self.stack.addWidget(self.server_form)

        self.port_form = self.create_port_form()
        self.stack.addWidget(self.port_form)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        self.tree.itemClicked.connect(self.on_item_selected)

        # Загружаем данные через контроллер
        self.controller.load_tree()

    # =========================================================
    # VIEW API (используется контроллером)
    # =========================================================

    def render_tree(self, data):
        self.tree.clear()

        for branch in data:
            branch_item = QTreeWidgetItem([branch["name"]])
            branch_item.setData(0, Qt.ItemDataRole.UserRole, ("branch", branch["id"]))
            self.tree.addTopLevelItem(branch_item)

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

        self.tree.expandAll()

    def show_server_form(self, server_data):
        self.server_name_input.setText(server_data["name"])
        self.server_ip_input.setText(server_data["ip"])
        self.stack.setCurrentWidget(self.server_form)

    def show_port_form(self, port_data):
        self.port_number_input.setText(str(port_data["port"]))
        self.port_vault_input.setText(port_data.get("vault_path", ""))
        self.stack.setCurrentWidget(self.port_form)

    def show_branch_form(self, branch_data):
        self.branch_name_input.setText(branch_data["name"])
        self.stack.setCurrentWidget(self.branch_form)

    def show_api_error(self, message):
        QMessageBox.critical(self, "Ошибка API", message)

    def show_error(self, message):
        QMessageBox.critical(self, "Ошибка", message)

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

        else:
            self.stack.setCurrentWidget(self.empty_widget)

    # =========================================================
    # SERVER FORM
    # =========================================================

    def create_server_form(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        self.server_name_input = QLineEdit()
        self.server_ip_input = QLineEdit()
        self.server_ip_input.setPlaceholderText("Например: 192.168.0.1")

        layout.addRow("Название:", self.server_name_input)
        layout.addRow("IP:", self.server_ip_input)

        self.server_save_btn = QPushButton("Сохранить")
        layout.addRow(self.server_save_btn)

        self.server_save_btn.clicked.connect(self.save_server)

        return widget

    def save_server(self):
        name = self.server_name_input.text().strip()
        ip = self.server_ip_input.text().strip()

        if not name:
            self.show_error("Название сервера не может быть пустым")
            return

        try:
            ipaddress.ip_address(ip)
        except ValueError:
            self.show_error("Введите корректный IP-адрес")
            return

        self.controller.save_server(name, ip)

    # =========================================================
    # PORT FORM
    # =========================================================

    def create_port_form(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        self.port_number_input = QLineEdit()
        self.port_number_input.setValidator(QIntValidator(1, 65535))

        self.port_vault_input = QLineEdit()

        layout.addRow("Порт:", self.port_number_input)
        layout.addRow("Vault path:", self.port_vault_input)

        self.port_save_btn = QPushButton("Сохранить")
        layout.addRow(self.port_save_btn)

        self.port_save_btn.clicked.connect(self.save_port)

        return widget

    def save_port(self):
        if not self.port_number_input.text():
            self.show_error("Введите номер порта")
            return

        new_port = int(self.port_number_input.text())
        vault_path = self.port_vault_input.text().strip()

        self.controller.save_port(new_port, vault_path)

    # =========================================================
    # BRANCH FORM
    # =========================================================

    def create_branch_form(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        self.branch_name_input = QLineEdit()

        layout.addRow("Название филиала:", self.branch_name_input)

        self.branch_save_btn = QPushButton("Сохранить")
        layout.addRow(self.branch_save_btn)

        self.branch_save_btn.clicked.connect(self.save_branch)

        return widget

    def save_branch(self):
        name = self.branch_name_input.text().strip()

        if not name:
            self.show_error("Название не может быть пустым")
            return

        self.controller.save_branch(name)