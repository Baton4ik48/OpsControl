from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import pyqtSignal

from ui.widgets.branch_card import BranchCard

_CARD_W = 220
_CARD_GAP = 12
_MARGIN = 16


class DashboardView(QScrollArea):
    branch_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)

        self._container = QWidget()
        self._vbox = QVBoxLayout(self._container)
        self._vbox.setContentsMargins(_MARGIN, _MARGIN, _MARGIN, _MARGIN)
        self._vbox.setSpacing(_CARD_GAP)
        self.setWidget(self._container)

        self._cards: dict[str, BranchCard] = {}
        self._row_widgets: list[QWidget] = []
        self._branches: list[dict] = []
        self._current_cols: int = 0

    def _calc_cols(self) -> int:
        w = self.viewport().width() - _MARGIN * 2
        return max(1, (w + _CARD_GAP) // (_CARD_W + _CARD_GAP))

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
        self._branches = branches
        cols = self._calc_cols()
        self._current_cols = cols

        cards: list[BranchCard] = []
        for branch in branches:
            name = branch["name"]
            card = BranchCard(name)
            card.double_clicked.connect(self.branch_selected)
            card.update_data(branch)
            self._cards[name] = card
            cards.append(card)

        self._vbox.addStretch(1)

        for row_start in range(0, len(cards), cols):
            row_cards = cards[row_start : row_start + cols]
            row_w = QWidget(self._container)
            row_layout = QHBoxLayout(row_w)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(_CARD_GAP)
            row_layout.addStretch()
            for card in row_cards:
                card.setParent(row_w)
                row_layout.addWidget(card)
            row_layout.addStretch()
            self._vbox.addWidget(row_w)
            self._row_widgets.append(row_w)

        self._vbox.addStretch(1)

    def update_branch(self, branch: dict):
        card = self._cards.get(branch["name"])
        if card:
            card.update_data(branch)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._branches:
            new_cols = self._calc_cols()
            if new_cols != self._current_cols:
                self.render(self._branches)
