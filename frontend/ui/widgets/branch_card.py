from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont


def _server_status(server: dict) -> str:
    ports = server.get("ports", [])
    checked = [p for p in ports if p.get("is_up") is not None]
    if not checked:
        return "unknown"
    ups = sum(1 for p in checked if p["is_up"])
    downs = len(checked) - ups
    if ups and downs:
        return "partial"
    return "up" if ups else "down"


class BranchCard(QFrame):
    double_clicked = pyqtSignal(str)

    _BG = {
        "ok": "#0d2218",
        "partial": "#252000",
        "down": "#280d0d",
        "unknown": "#1a2730",
    }
    _BORDER = {
        "ok": "#1a4a30",
        "partial": "#4a3800",
        "down": "#4a1515",
        "unknown": "#263545",
    }

    def __init__(self, branch_name: str, parent=None):
        super().__init__(parent)
        self._name = branch_name
        self.setFixedSize(220, 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("branchCard")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        self._lbl_name = QLabel(branch_name)
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        self._lbl_name.setFont(font)
        self._lbl_name.setWordWrap(True)
        self._lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._lbl_name)

        self._lbl_stats = QLabel()
        self._lbl_stats.setTextFormat(Qt.TextFormat.RichText)
        self._lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_stats.setStyleSheet("font-size: 9pt; background: transparent;")
        root.addWidget(self._lbl_stats)

        self._apply_style("unknown")

    def update_data(self, branch: dict):
        servers = branch.get("servers", [])
        counts = {"up": 0, "partial": 0, "down": 0, "unknown": 0}
        for s in servers:
            counts[_server_status(s)] += 1

        up = counts["up"]
        partial = counts["partial"]
        down = counts["down"]
        unknown = counts["unknown"]

        parts = []
        if up:
            parts.append(f'<span style="color:#4caf50">● {up}</span>')
        if partial:
            parts.append(f'<span style="color:#ffc107">◑ {partial}</span>')
        if down:
            parts.append(f'<span style="color:#ef5350">✗ {down}</span>')
        if not parts:
            parts.append(f'<span style="color:#607d8b">{unknown}</span>')

        self._lbl_stats.setText("&nbsp;&nbsp;".join(parts))

        if down > 0 and up == 0 and partial == 0:
            state = "down"
        elif down > 0 or partial > 0:
            state = "partial"
        elif up > 0:
            state = "ok"
        else:
            state = "unknown"

        self._apply_style(state)

    def _apply_style(self, state: str):
        bg = self._BG[state]
        border = self._BORDER[state]
        self.setStyleSheet(f"""
            QFrame#branchCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QFrame#branchCard:hover {{
                border: 1px solid #2fa4a9;
            }}
            QLabel {{
                background: transparent;
                color: #cfd8dc;
            }}
        """)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(self._name)
        super().mouseDoubleClickEvent(event)
