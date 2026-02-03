from PyQt6.QtWidgets import QFrame, QVBoxLayout, QSplitter
from PyQt6.QtCore import Qt


class Workspace(QFrame):
    def __init__(self, tree, console):
        super().__init__()

        self.setObjectName("Workspace")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Vertical)

        splitter.addWidget(tree)
        splitter.addWidget(console)

        # дефолтные размеры (дерево больше логов)
        splitter.setSizes([500, 200])

        layout.addWidget(splitter)
