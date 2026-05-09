"""
charts.py
─────────
Shared chart primitives used across all analytics pages.
Import from here to avoid duplication.
"""

from PySide6.QtWidgets import QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (QPainter, QColor, QPen, QFont,
                            QLinearGradient, QPainterPath, QBrush)


# ═══════════════════════════════════════════════════════════
#  CHART WIDGETS
# ═══════════════════════════════════════════════════════════

class LineChart(QWidget):
    """Smooth line chart with axis labels and optional dual series."""

    def __init__(self, series: dict = None, parent=None):
        super().__init__(parent)
        self.series = series or {}
        self.x_labels: list[str] = []
        self.setMinimumHeight(160)

    def set_series(self, series: dict, x_labels: list[str] = None):
        self.series = series
        self.x_labels = x_labels or []
        self.update()

    def paintEvent(self, event):
        if not self.series:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 42, 16, 12, 28

        all_vals = [v for s in self.series.values() for v in s["data"]]
        if not all_vals:
            return
        mn, mx = min(all_vals), max(all_vals)
        rng = mx - mn or 1

        n_pts = max(len(s["data"]) for s in self.series.values())
        if n_pts < 2:
            return

        def px(i):
            return pad_l + i * (w - pad_l - pad_r) / (n_pts - 1)

        def py(v):
            return pad_t + (1 - (v - mn) / rng) * (h - pad_t - pad_b)

        grid_pen = QPen(QColor("#f3f4f6"), 1)
        painter.setPen(grid_pen)
        font = QFont(); font.setPointSize(7)
        painter.setFont(font)
        for i in range(5):
            gy = pad_t + i * (h - pad_t - pad_b) / 4
            painter.setPen(grid_pen)
            painter.drawLine(int(pad_l), int(gy), int(w - pad_r), int(gy))
            val = mx - i * rng / 4
            painter.setPen(QPen(QColor("#9ca3af")))
            painter.drawText(0, int(gy) - 7, int(pad_l) - 4, 16,
                             Qt.AlignRight | Qt.AlignVCenter,
                             f"{val:.0f}")

        if self.x_labels and n_pts > 1:
            step = max(1, n_pts // 6)
            for i, lbl in enumerate(self.x_labels):
                if i % step == 0:
                    painter.setPen(QPen(QColor("#9ca3af")))
                    painter.drawText(int(px(i)) - 20, h - pad_b + 4, 40, 16,
                                     Qt.AlignCenter, lbl)

        for s_data in self.series.values():
            data = s_data["data"]
            color = QColor(s_data["color"])
            if len(data) < 2:
                continue
            pts = [(px(i), py(v)) for i, v in enumerate(data)]

            path = QPainterPath()
            path.moveTo(pts[0][0], h - pad_b)
            for x, y in pts:
                path.lineTo(x, y)
            path.lineTo(pts[-1][0], h - pad_b)
            path.closeSubpath()
            grad = QLinearGradient(0, pad_t, 0, h - pad_b)
            c1 = QColor(color); c1.setAlpha(45)
            c2 = QColor(color); c2.setAlpha(0)
            grad.setColorAt(0, c1); grad.setColorAt(1, c2)
            painter.fillPath(path, QBrush(grad))

            pen = QPen(color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            for i in range(len(pts) - 1):
                painter.drawLine(int(pts[i][0]), int(pts[i][1]),
                                 int(pts[i+1][0]), int(pts[i+1][1]))

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            for x, y in pts:
                painter.drawEllipse(int(x)-3, int(y)-3, 6, 6)


class HBarChart(QWidget):
    """Horizontal bar chart with value labels and optional color per bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.labels: list[str] = []
        self.values: list[float] = []
        self.colors: list[str] = []
        self.default_color = "#6366f1"
        self.setMinimumHeight(60)

    def set_data(self, labels, values, colors=None):
        self.labels = labels
        self.values = values
        self.colors = colors or [self.default_color] * len(labels)
        self.setMinimumHeight(max(60, len(labels) * 38))
        self.update()

    def paintEvent(self, event):
        if not self.values:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        n = len(self.labels)
        row_h = h / n
        label_w = 140
        val_w = 52
        bar_max = w - label_w - val_w - 8
        mx = max(self.values) or 1
        font = QFont(); font.setPointSize(9)
        painter.setFont(font)

        for i, (label, val) in enumerate(zip(self.labels, self.values)):
            y = i * row_h
            bar_w = (val / mx) * bar_max
            color = QColor(self.colors[i] if i < len(self.colors) else self.default_color)

            painter.setPen(QPen(QColor("#374151")))
            painter.drawText(0, int(y), int(label_w), int(row_h),
                             Qt.AlignVCenter | Qt.AlignLeft,
                             label[:20] + ("…" if len(label) > 20 else ""))

            painter.setBrush(QBrush(QColor("#f3f4f6")))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(label_w), int(y + row_h*0.28),
                                    int(bar_max), int(row_h*0.44), 4, 4)
            if bar_w > 0:
                painter.setBrush(QBrush(color))
                painter.drawRoundedRect(int(label_w), int(y + row_h*0.28),
                                        int(bar_w), int(row_h*0.44), 4, 4)

            painter.setPen(QPen(QColor("#6b7280")))
            painter.drawText(int(label_w + bar_max + 6), int(y), int(val_w), int(row_h),
                             Qt.AlignVCenter | Qt.AlignLeft,
                             f"{val:.1f}" if isinstance(val, float) and val % 1 else str(int(val)))


class MultiDonut(QWidget):
    """Multiple donut rings stacked — one per segment."""

    def __init__(self, segments: list = None, parent=None):
        super().__init__(parent)
        self.segments = segments or []
        self.setFixedSize(140, 140)

    def set_segments(self, segments):
        self.segments = segments
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        ring_w = 10
        gap = 4
        outer = min(w, h) - 8

        for i, (label, pct, color) in enumerate(self.segments):
            size = outer - i * (ring_w + gap) * 2
            if size < 10:
                break
            x = (w - size) // 2
            y = (h - size) // 2
            rect = QRectF(x, y, size, size)

            pen = QPen(QColor("#e5e7eb"), ring_w, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)
            painter.drawEllipse(rect)

            span = int(pct / 100 * 360 * 16)
            pen.setColor(QColor(color))
            painter.setPen(pen)
            painter.drawArc(rect, 90 * 16, -span)

        font = QFont(); font.setPointSize(8); font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#111827")))
        painter.drawText(0, 0, w, h, Qt.AlignCenter, "Stock\nMix")


class ScatterDot(QWidget):
    """Price vs Quantity scatter plot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.points: list = []
        self.setMinimumHeight(200)

    def set_points(self, points):
        self.points = points
        self.update()

    def paintEvent(self, event):
        if not self.points:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 44, 16, 12, 28

        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        xmn, xmx = min(xs), max(xs)
        ymn, ymx = min(ys), max(ys)
        xrng = xmx - xmn or 1
        yrng = ymx - ymn or 1

        def px(v): return pad_l + (v - xmn) / xrng * (w - pad_l - pad_r)
        def py(v): return pad_t + (1 - (v - ymn) / yrng) * (h - pad_t - pad_b)

        grid_pen = QPen(QColor("#f3f4f6"), 1)
        font = QFont(); font.setPointSize(7); painter.setFont(font)
        for i in range(5):
            gy = pad_t + i * (h - pad_t - pad_b) / 4
            painter.setPen(grid_pen)
            painter.drawLine(int(pad_l), int(gy), w - pad_r, int(gy))
            val = ymx - i * yrng / 4
            painter.setPen(QPen(QColor("#9ca3af")))
            painter.drawText(0, int(gy)-7, pad_l-4, 16,
                             Qt.AlignRight|Qt.AlignVCenter, f"{val:.0f}")

        painter.setPen(QPen(QColor("#6b7280")))
        painter.drawText(0, h-pad_b+4, w, 20, Qt.AlignCenter, "Price (₱)")

        for x, y, label, color in self.points:
            cx, cy = int(px(x)), int(py(y))
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(QPen(QColor(color).darker(120), 1))
            painter.drawEllipse(cx-6, cy-6, 12, 12)
            painter.setPen(QPen(QColor("#374151")))
            font2 = QFont(); font2.setPointSize(7); painter.setFont(font2)
            painter.drawText(cx+8, cy-6, 80, 14, Qt.AlignLeft|Qt.AlignVCenter,
                             label[:12])


# ═══════════════════════════════════════════════════════════
#  SHARED UI COMPONENTS
# ═══════════════════════════════════════════════════════════

CARD_STYLE = """
    QFrame {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
    }
    QLabel { background: transparent; border: none; }
"""


def _badge(text, bg, fg="#ffffff"):
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setFixedHeight(22)
    lbl.setStyleSheet(f"""
        background-color: {bg};
        color: {fg};
        border-radius: 4px;
        padding: 0 8px;
        font-size: 10px;
        font-weight: 700;
    """)
    return lbl


class KpiCard(QFrame):
    def __init__(self, icon, title, value, sub, color, parent=None):
        super().__init__(parent)
        self.setStyleSheet(CARD_STYLE)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(110)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(3)

        top = QHBoxLayout()
        ico = QLabel(icon)
        ico.setStyleSheet(f"background:{color}22; border-radius:7px; font-size:16px; padding:3px 5px;")
        ico.setFixedSize(32, 32); ico.setAlignment(Qt.AlignCenter)
        t = QLabel(title)
        t.setStyleSheet("color:#6b7280; font-size:11px; font-weight:600;")
        top.addWidget(ico); top.addWidget(t, 1)
        lay.addLayout(top)

        self.val_lbl = QLabel(str(value))
        self.val_lbl.setStyleSheet("color:#111827; font-size:22px; font-weight:800;")
        lay.addWidget(self.val_lbl)

        s = QLabel(str(sub))
        s.setStyleSheet("color:#9ca3af; font-size:11px;")
        lay.addWidget(s)

    def set_value(self, v): self.val_lbl.setText(str(v))


class SectionCard(QFrame):
    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        self.setStyleSheet(CARD_STYLE)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(18, 16, 18, 18)
        self._lay.setSpacing(10)

        hdr = QHBoxLayout()
        t = QLabel(title)
        t.setStyleSheet("font-size:14px; font-weight:700; color:#111827;")
        hdr.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setStyleSheet("font-size:11px; color:#9ca3af;")
            hdr.addWidget(s)
        hdr.addStretch()
        self._hdr = hdr
        self._lay.addLayout(hdr)

        self.body = QVBoxLayout()
        self.body.setSpacing(6)
        self._lay.addLayout(self.body)

    def add(self, w): self.body.addWidget(w)
    def add_layout(self, l): self.body.addLayout(l)
    def add_header_widget(self, w): self._hdr.addWidget(w)


def _divider():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet("background:#f3f4f6; max-height:1px; border:none;")
    return f
