import os
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIcon

from core.paths import ICONS_DIR


class Sidebar(QFrame):
    reload_clicked = pyqtSignal()
    refresh_all_clicked = pyqtSignal()
    show_all_clicked = pyqtSignal()
    show_problem_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    exit_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.icon_settings = QIcon(os.path.join(ICONS_DIR, "settings_icon.png"))
        self.icon_exit = QIcon(os.path.join(ICONS_DIR, "exit_icon.png"))
        self.icon_tree = QIcon(os.path.join(ICONS_DIR, "tree_icon.png"))
        self.icon_full = QIcon(os.path.join(ICONS_DIR, "full_icon.png"))
        self.icon_update_all = QIcon(os.path.join(ICONS_DIR, "update_icon_all.png"))
        self.icon_down_all = QIcon(os.path.join(ICONS_DIR, "status_down_all.png"))

        self.setObjectName("Sidebar")
        self.setFixedWidth(170)

        layout = QVBoxLayout(self)

        self.reload_btn = QPushButton(self.icon_tree, "Топология сети")
        self.show_all_btn = QPushButton(self.icon_full, "Все устройства")
        self.show_problem_btn = QPushButton(self.icon_down_all, "Недоступные")
        self.refresh_btn = QPushButton(self.icon_update_all, "Опросить все")

        layout.addWidget(self.reload_btn)
        layout.addWidget(self.show_all_btn)
        layout.addWidget(self.show_problem_btn)
        layout.addWidget(self.refresh_btn)

        layout.addStretch()

        self.settings_btn = QPushButton(self.icon_settings, "Настройки")
        self.exit_btn = QPushButton(self.icon_exit, "Выход")

        layout.addWidget(self.settings_btn)
        layout.addWidget(self.exit_btn)

        self.reload_btn.clicked.connect(self.reload_clicked.emit)
        self.show_all_btn.clicked.connect(self.show_all_clicked.emit)
        self.show_problem_btn.clicked.connect(self.show_problem_clicked.emit)
        self.refresh_btn.clicked.connect(self.refresh_all_clicked.emit)
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        self.exit_btn.clicked.connect(self.exit_clicked.emit)

        # по умолчанию действия недоступны, кроме кнопки загрузки топологии
        self.set_actions_enabled(False)
        self.reload_btn.setEnabled(True)

    def set_actions_enabled(self, enabled: bool):
        self.reload_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)
        self.show_all_btn.setEnabled(enabled)
        self.show_problem_btn.setEnabled(enabled)
