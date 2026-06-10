from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QHBoxLayout
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
        self._vbox = QVBoxLayout(self._container)
        self._vbox.setContentsMargins(16, 16, 16, 16)
        self._vbox.setSpacing(12)
        self.setWidget(self._container)

        self._cards: dict[str, BranchCard] = {}
        self._row_widgets: list[QWidget] = []

    def _clear_layout(self):
        while self._vbox.count():
            item = self._vbox.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._row_widgets.clear()
        self._cards.clear()

    def render(self, branches: list[dict]):
        self._clear_layout()

        cards: list[BranchCard] = []
        for branch in branches:
            name = branch["name"]
            card = BranchCard(name)
            card.double_clicked.connect(self.branch_selected)
            card.update_data(branch)
            self._cards[name] = card
            cards.append(card)

        for row_start in range(0, len(cards), _COLS):
            row_cards = cards[row_start : row_start + _COLS]
            row_w = QWidget(self._container)
            row_layout = QHBoxLayout(row_w)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)
            row_layout.addStretch()
            for card in row_cards:
                card.setParent(row_w)
                row_layout.addWidget(card)
            row_layout.addStretch()
            self._vbox.addWidget(row_w)
            self._row_widgets.append(row_w)

        # Прижимаем строки к верху
        self._vbox.addStretch(1)

    def update_branch(self, branch: dict):
        card = self._cards.get(branch["name"])
        if card:
            card.update_data(branch)
