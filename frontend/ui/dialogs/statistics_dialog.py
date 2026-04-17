import os
import re
from datetime import datetime, timezone

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QWidget,
    QPushButton,
    QLabel,
    QGridLayout,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from core.paths import ICONS_DIR, path_to_file_uri


# ──────────────────────────────────────────────────────────────────────────────
# Данные
# ──────────────────────────────────────────────────────────────────────────────


def _extract_type(name: str) -> str:
    return re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()


def _extract_project(name: str) -> str | None:
    m = re.search(r"\(([^)]+)\)\s*$", name)
    return m.group(1).strip() if m else None


def _build_stats(data: list) -> dict:
    branches: list[str] = []
    total_servers = 0
    by_type: dict[str, int] = {}
    by_project: dict[str, int] = {}
    by_branch: dict[str, list[dict]] = {}

    for branch in data:
        bname = branch["name"]
        branches.append(bname)
        by_branch[bname] = []

        for server in branch.get("servers", []):
            name = server["name"]
            eq_type = _extract_type(name)
            project = _extract_project(name)
            ports = server.get("ports", [])

            total_servers += 1
            by_type[eq_type] = by_type.get(eq_type, 0) + 1
            if project:
                by_project[project] = by_project.get(project, 0) + 1
            by_branch[bname].append(
                {
                    "type": eq_type,
                    "name": name,
                    "ports": ports,
                }
            )

    return {
        "branches": branches,
        "total_servers": total_servers,
        "by_project": dict(sorted(by_project.items())),
        "by_branch": by_branch,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Статус и тултип — тот же формат что в device_tree.py
# ──────────────────────────────────────────────────────────────────────────────


def _fmt_dt(value: str | None) -> str:
    if not value:
        return "нет данных"
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%d.%m.%Y %H:%M")
    except Exception:
        return value


def _icon_img(name: str) -> str:
    path = os.path.join(ICONS_DIR, name)
    return f'<img src="{path_to_file_uri(path)}" width="13" height="13">'


def _port_row(state, last_success, last_failure) -> list[str]:
    """Строки HTML-таблицы для одного порта — идентично device_tree."""
    rows = []
    if state is True:
        rows.append(
            f'<tr><td>{_icon_img("status_up.png")}</td>'
            f"<td>&nbsp;<b>Онлайн</b></td></tr>"
        )
        if last_failure:
            rows.append(
                f'<tr><td>{_icon_img("status_down.png")}</td>'
                f"<td>&nbsp;Последний раз недоступен:&nbsp;{_fmt_dt(last_failure)}</td></tr>"
            )
    elif state is False:
        if last_success:
            rows.append(
                f'<tr><td>{_icon_img("status_down.png")}</td>'
                f"<td>&nbsp;Последний раз был в сети:&nbsp;{_fmt_dt(last_success)}</td></tr>"
            )
        else:
            rows.append(
                f'<tr><td>{_icon_img("status_down.png")}</td>'
                f"<td>&nbsp;В сети не наблюдался</td></tr>"
            )
    else:
        if last_success:
            rows.append(
                f'<tr><td>{_icon_img("status_up.png")}</td>'
                f"<td>&nbsp;Последний раз в сети:&nbsp;{_fmt_dt(last_success)}</td></tr>"
            )
        if last_failure:
            rows.append(
                f'<tr><td>{_icon_img("status_down.png")}</td>'
                f"<td>&nbsp;Последний раз недоступен:&nbsp;{_fmt_dt(last_failure)}</td></tr>"
            )
        if not last_success and not last_failure:
            rows.append('<tr><td colspan="2">Статус неизвестен</td></tr>')
    return rows


def _build_tooltip(server: dict) -> str:
    """HTML-тултип с детализацией по всем портам сервера."""
    rows = [
        f'<tr><td colspan="2"><b>{server["name"]}</b></td></tr>',
        '<tr><td colspan="2"><hr/></td></tr>',
    ]
    for p in server["ports"]:
        port = p.get("port", "?")
        rows.append(
            f'<tr><td colspan="2" style="color:#90a4ae; padding-top:4px;">'
            f"Порт&nbsp;{port}</td></tr>"
        )
        rows.extend(
            _port_row(
                p.get("is_up"),
                p.get("last_success"),
                p.get("last_failure"),
            )
        )
    return f'<table cellspacing="3">{"".join(rows)}</table>'


def _server_status(ports: list) -> str:
    known = [p.get("is_up") for p in ports if p.get("is_up") is not None]
    if not known:
        return "unknown"
    if all(s is True for s in known):
        return "up"
    if all(s is False for s in known):
        return "down"
    return "partial"


# ──────────────────────────────────────────────────────────────────────────────
# Цветовая схема (только динамические — статичные перенесены в statistics.qss)
# ──────────────────────────────────────────────────────────────────────────────

_BG = "#0f1b1e"
_CARD = "#111f25"
_HDR = "#132d37"
_ACCENT = "#4fc3f7"
_ACCENT2 = "#81d4fa"
_TEXT = "#d8d8d8"
_TEXT_DIM = "#90a4ae"
_GREEN = "#80cbc4"
_BORDER = "#1e3a42"
_TAG_BOR = "#2a5566"

# bg / border / text по статусу
_STATUS: dict[str, tuple[str, str, str]] = {
    "up": ("#0d2a1a", "#2e7d52", "#81c995"),
    "down": ("#2a0d0d", "#7d2e2e", "#ef9a9a"),
    "partial": ("#2a1a0d", "#7d5a2e", "#ffcc80"),
    "unknown": ("#1a2e36", "#2a5566", "#90a4ae"),
}


# ──────────────────────────────────────────────────────────────────────────────
# Виджет: сворачиваемая секция
# ──────────────────────────────────────────────────────────────────────────────


class _CollapsibleSection(QFrame):
    def __init__(
        self,
        title: str,
        badge: str = "",
        expanded: bool = False,
        branch: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self._title = title
        self._badge = badge
        self._expanded = expanded

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 2)
        root.setSpacing(0)

        self._btn = QPushButton()
        # objectName → стиль из statistics.qss
        self._btn.setObjectName("StatBranchBtn" if branch else "StatSectionBtn")
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn.clicked.connect(self._toggle)
        self._refresh_btn()
        root.addWidget(self._btn)

        self._body = QWidget()
        self._body.setStyleSheet(f"background: {_CARD};")
        self._body.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )
        body_l = QVBoxLayout(self._body)
        body_l.setContentsMargins(14, 8, 14, 10)
        body_l.setSpacing(6)
        self._body_layout = body_l
        self._body.setVisible(expanded)
        root.addWidget(self._body)

    def _refresh_btn(self):
        arrow = "▼" if self._expanded else "▶"
        badge = f"  ({self._badge})" if self._badge else ""
        self._btn.setText(f"  {arrow}   {self._title}{badge}")

    def _toggle(self):
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        self._refresh_btn()

    def add(self, widget: QWidget):
        self._body_layout.addWidget(widget)


# ──────────────────────────────────────────────────────────────────────────────
# Вспомогательные строители виджетов
# ──────────────────────────────────────────────────────────────────────────────


def _divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color:{_BORDER}; background:{_BORDER}; max-height:1px;")
    return f


def _h_label(text: str, size: int = 11, color: str = _ACCENT2) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color:{color}; font-size:{size}pt; font-weight:bold;"
        f" background:transparent; padding:10px 0 4px 0;"
    )
    return lbl


def _plain_label(text: str, color: str = _TEXT_DIM) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{color}; background:transparent; font-size:9pt;")
    return lbl


def _branch_label(text: str) -> QLabel:
    lbl = QLabel(f"  •  {text}")
    lbl.setStyleSheet(f"color:{_TEXT_DIM}; background:transparent; font-size:9pt;")
    return lbl


def _status_tag(server: dict) -> QLabel:
    """Плашка оборудования: цвет по статусу, тултип с детализацией по портам."""
    status = _server_status(server["ports"])
    bg, bor, txt = _STATUS[status]
    lbl = QLabel(server["type"])
    lbl.setStyleSheet(
        f"""
        QLabel {{
            background-color:{bg}; color:{txt};
            border:1px solid {bor}; border-radius:3px;
            padding:3px 8px; font-size:9pt;
        }}
    """
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if server["ports"]:
        lbl.setToolTip(_build_tooltip(server))
    return lbl


def _equipment_grid(servers: list[dict], cols: int = 3) -> QWidget:
    w = QWidget()
    w.setStyleSheet("background:transparent;")
    grid = QGridLayout(w)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(6)

    for i, srv in enumerate(sorted(servers, key=lambda s: s["type"])):
        row, col = divmod(i, cols)
        grid.addWidget(_status_tag(srv), row, col)

    remainder = len(servers) % cols
    if remainder:
        for col in range(remainder, cols):
            spacer = QLabel()
            spacer.setStyleSheet("background:transparent;")
            grid.addWidget(spacer, len(servers) // cols, col)

    return w


# ──────────────────────────────────────────────────────────────────────────────
# Диалог
# ──────────────────────────────────────────────────────────────────────────────


class StatisticsDialog(QDialog):
    def __init__(self, data: list | None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Статистика инфраструктуры")
        self.setWindowIcon(QIcon(os.path.join(ICONS_DIR, "app_icon.png")))
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.resize(700, 780)
        self.setStyleSheet(f"background-color:{_BG}; color:{_TEXT};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Заголовок
        title_bar = QWidget()
        title_bar.setStyleSheet(
            f"background:{_HDR}; border-bottom:2px solid {_ACCENT};"
        )
        title_bar.setFixedHeight(42)
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(16, 0, 16, 0)
        lbl = QLabel("Статистика инфраструктуры")
        lbl.setStyleSheet(
            f"color:{_ACCENT}; font-size:12pt; font-weight:bold; background:transparent;"
        )
        tb.addWidget(lbl)
        tb.addStretch()
        root.addWidget(title_bar)

        # Скролл
        scroll = QScrollArea()
        scroll.setObjectName("StatScrollArea")  # → statistics.qss
        scroll.setWidgetResizable(True)

        content = QWidget()
        content.setObjectName("ScrollContent")  # → statistics.qss
        cl = QVBoxLayout(content)
        cl.setContentsMargins(16, 12, 16, 16)
        cl.setSpacing(4)

        if not data:
            msg = _plain_label(
                "Топология сети не загружена.\n"
                "Загрузите дерево и откройте статистику повторно.",
                color="#546e7a",
            )
            msg.setContentsMargins(0, 20, 0, 0)
            cl.addWidget(msg)
        else:
            self._fill(cl, _build_stats(data))

        cl.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll)

        # Кнопка
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(12, 6, 12, 8)
        btn_row.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.setFixedWidth(110)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    def _fill(self, layout: QVBoxLayout, stats: dict):
        branches = stats["branches"]
        by_project = stats["by_project"]
        total = stats["total_servers"]
        by_branch = stats["by_branch"]

        # Филиалы
        sec = _CollapsibleSection("Филиалы", badge=str(len(branches)), expanded=False)
        for b in branches:
            sec.add(_branch_label(b))
        layout.addWidget(sec)
        layout.addWidget(_divider())

        # По проектам
        if by_project:
            layout.addWidget(_h_label("По проектам"))
            card = QWidget()
            card.setStyleSheet(
                f"background:{_CARD}; border-left:3px solid {_TAG_BOR};"
                f" border-radius:0 3px 3px 0;"
            )
            card_l = QVBoxLayout(card)
            card_l.setContentsMargins(14, 8, 14, 8)
            card_l.setSpacing(5)
            for proj, cnt in by_project.items():
                row = QHBoxLayout()
                row.setContentsMargins(0, 0, 0, 0)
                n = QLabel(proj)
                n.setStyleSheet(
                    f"color:{_TEXT}; font-size:9pt; background:transparent;"
                )
                d = QLabel("—")
                d.setStyleSheet(
                    f"color:{_BORDER}; background:transparent; padding:0 6px;"
                )
                c = QLabel(f"{cnt} шт.")
                c.setStyleSheet(
                    f"color:{_GREEN}; font-weight:bold; font-size:9pt; background:transparent;"
                )
                row.addWidget(n)
                row.addWidget(d)
                row.addWidget(c)
                row.addStretch()
                card_l.addLayout(row)
            layout.addWidget(card)
            layout.addWidget(_divider())

        # Всего оборудования
        layout.addWidget(_h_label(f"Всего оборудования — {total} шт."))
        layout.addWidget(_divider())

        # Легенда
        legend = QWidget()
        legend.setStyleSheet("background:transparent;")
        leg_l = QHBoxLayout(legend)
        leg_l.setContentsMargins(0, 0, 0, 6)
        leg_l.setSpacing(16)
        for status, label in (
            ("up", "все порты доступны"),
            ("partial", "часть портов"),
            ("down", "нет доступных"),
            ("unknown", "не проверялось"),
        ):
            _, _, txt = _STATUS[status]
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{txt}; background:transparent; font-size:9pt;")
            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"color:{_TEXT_DIM}; background:transparent; font-size:8pt;"
            )
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            row.addWidget(dot)
            row.addWidget(lbl)
            leg_l.addLayout(row)
        leg_l.addStretch()
        layout.addWidget(legend)

        # По филиалам
        layout.addWidget(_h_label("По филиалам"))
        for bname, servers in by_branch.items():
            sec = _CollapsibleSection(
                bname,
                badge=f"{len(servers)} шт.",
                expanded=False,
                branch=True,
            )
            if servers:
                sec.add(_equipment_grid(servers, cols=3))
            else:
                sec.add(_plain_label("Нет оборудования", color="#546e7a"))
            layout.addWidget(sec)
