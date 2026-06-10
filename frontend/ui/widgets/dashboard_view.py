from PyQt6.QtWidgets import QScrollArea, QWidget, QGridLayout
from PyQt6.QtCore import pyqtSignal, Qt

from ui.widgets.branch_card import BranchCard

_COLS = 5


class DashboardView(QScrollArea):
    branch_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(16, 16, 16, 16)
        self._grid.setSpacing(12)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setWidget(self._container)

        self._cards: dict[str, BranchCard] = {}
        self._order: list[str] = []

    def render(self, branches: list[dict]):
        new_names = {b["name"] for b in branches}

        for name in list(self._cards):
            if name not in new_names:
                card = self._cards.pop(name)
                self._grid.removeWidget(card)
                card.deleteLater()

        for card in self._cards.values():
            self._grid.removeWidget(card)

        self._order = [b["name"] for b in branches]

        for i, branch in enumerate(branches):
            name = branch["name"]
            if name not in self._cards:
                card = BranchCard(name, self._container)
                card.double_clicked.connect(self.branch_selected)
                self._cards[name] = card
            self._cards[name].update_data(branch)
            row, col = divmod(i, _COLS)
            self._grid.addWidget(self._cards[name], row, col)

    def update_branch(self, branch: dict):
        card = self._cards.get(branch["name"])
        if card:
            card.update_data(branch)
