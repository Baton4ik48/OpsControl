from PyQt6.QtWidgets import QFrame, QVBoxLayout

class Workspace(QFrame):
    def __init__(self, *widgets):
        super().__init__()

        self.setObjectName("Workspace")

        layout = QVBoxLayout(self)
        for w in widgets:
            layout.addWidget(w)
