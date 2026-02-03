from PyQt6.QtWidgets import QFrame, QVBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal


class Sidebar(QFrame):
    reload_clicked = pyqtSignal()
    refresh_all_clicked = pyqtSignal()
    show_all_clicked = pyqtSignal()
    show_problem_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    exit_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setObjectName("Sidebar")
        self.setFixedWidth(150)

        layout = QVBoxLayout(self)

        # ===== ОСНОВНЫЕ ДЕЙСТВИЯ =====
        self.reload_btn = QPushButton("Загрузка древа")
        self.show_all_btn = QPushButton("Все сервера")
        self.show_problem_btn = QPushButton("Проблемные")
        self.refresh_btn = QPushButton("Обновить всё")

        layout.addWidget(self.reload_btn)
        layout.addWidget(self.show_all_btn)
        layout.addWidget(self.show_problem_btn)
        layout.addWidget(self.refresh_btn)

        layout.addStretch()

        # ===== СИСТЕМНЫЕ =====
        self.settings_btn = QPushButton("Настройки")
        self.exit_btn = QPushButton("Выход")

        layout.addWidget(self.settings_btn)
        layout.addWidget(self.exit_btn)

        # ===== СИГНАЛЫ =====
        self.reload_btn.clicked.connect(self.reload_clicked.emit)
        self.show_all_btn.clicked.connect(self.show_all_clicked.emit)
        self.show_problem_btn.clicked.connect(self.show_problem_clicked.emit)
        self.refresh_btn.clicked.connect(self.refresh_all_clicked.emit)
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        self.exit_btn.clicked.connect(self.exit_clicked.emit)

        # по умолчанию действия недоступны
        self.set_actions_enabled(False)

    def set_actions_enabled(self, enabled: bool):
        self.refresh_btn.setEnabled(enabled)
        self.show_all_btn.setEnabled(enabled)
        self.show_problem_btn.setEnabled(enabled)
