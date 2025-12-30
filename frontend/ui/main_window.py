from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from core.api import ApiClient
from controllers.tree_controller import TreeController

from ui.widgets.sidebar import Sidebar
from ui.widgets.device_tree import DeviceTree
from ui.widgets.console import Console
from ui.widgets.workspace import Workspace


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PortPass Manager")
        self.resize(1200, 700)

        main_layout = QVBoxLayout(self)


        # # ===== MENU =====
        # menu = QMenuBar()
        # menu.addMenu("Файл")
        # menu.addMenu("Вид")
        # menu.addMenu("Помощь")
        # main_layout.addWidget(menu)


        # ===== BODY =====
        body = QHBoxLayout()

        self.sidebar = Sidebar()
        self.tree = DeviceTree()
        self.console = Console()
        self.api = ApiClient()

        self.controller = TreeController(self.api, self.tree)

        workspace = Workspace(self.tree, self.console)

        body.addWidget(self.sidebar)
        body.addWidget(workspace)

        main_layout.addLayout(body)

        # ===== SIGNALS =====
        self.sidebar.refresh_all_clicked.connect(self.on_refresh_all)
        self.sidebar.show_all_clicked.connect(self.on_show_all)
        self.sidebar.show_problem_clicked.connect(self.on_show_problem)

        self.reload()

    def reload(self):
        self.console.log("Загрузка данных…")
        self.controller.load()

    def on_refresh_all(self):
        self.controller.refresh_all()

    def on_show_all(self):
        self.controller.show_all()

    def on_show_problem(self):
        self.controller.show_problem()
