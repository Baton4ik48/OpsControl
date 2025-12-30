from PyQt6.QtWidgets import QFrame, QVBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal

class Sidebar(QFrame):
    refresh_all_clicked = pyqtSignal()
    show_all_clicked = pyqtSignal()
    show_problem_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setObjectName("Sidebar")
        self.setFixedWidth(150)

        layout = QVBoxLayout(self)

        btn_all = QPushButton("Все сервера")
        btn_problem = QPushButton("Проблемные")
        btn_refresh = QPushButton("Обновить всё")

        layout.addWidget(btn_all)
        layout.addWidget(btn_problem)
        layout.addWidget(btn_refresh)

        layout.addStretch()
        layout.addWidget(QPushButton("Настройки"))
        layout.addWidget(QPushButton("Выход"))

        # связываем кнопки с сигналами
        btn_all.clicked.connect(self.show_all_clicked.emit)
        btn_problem.clicked.connect(self.show_problem_clicked.emit)
        btn_refresh.clicked.connect(self.refresh_all_clicked.emit)
