"""Cursor overlay effects: halo, trail, click pulse, target highlight, arrow."""
import time
import math
import ctypes
import ctypes.wintypes
from collections import deque
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QPoint, QRectF, QPointF
from PySide6.QtGui import (QPainter, QColor, QPen, QRadialGradient,
                            QFont, QPainterPath)

from ahh.ui.theme import T


class CursorOverlay(QWidget):
    """Full-screen transparent overlay for cursor effects."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # Cursor tracking
        self._cursor_pos = QPoint(0, 0)
        self._trail: deque[tuple[QPoint, float]] = deque(maxlen=20)
        self._show_halo = False

        # Click pulse
        self._click_pulses: list[dict] = []

        # Target highlight
        self._highlight_rect: QRectF | None = None
        self._highlight_label: str = ""

        # Arrow
        self._arrow_target: QPoint | None = None
        self._arrow_label: str = ""

        # Update timer
        self._timer = QTimer()
        self._timer.setInterval(16)  # ~60fps
        self._timer.timeout.connect(self._tick)

    def start_tracking(self):
        self._show_halo = True
        self._timer.start()

    def stop_tracking(self):
        self._show_halo = False
        self._timer.stop()
        self._trail.clear()
        self._click_pulses.clear()
        self._highlight_rect = None
        self._arrow_target = None
        self.update()

    def _tick(self):
        try:
            point = ctypes.wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
            self._cursor_pos = QPoint(point.x, point.y)
        except Exception:
            pass

        now = time.time()
        self._trail.append((QPoint(self._cursor_pos), now))

        while self._trail and now - self._trail[0][1] > 0.8:
            self._trail.popleft()

        self._click_pulses = [p for p in self._click_pulses if now - p["start_time"] < 0.5]

        self.update()

    def add_click_pulse(self, pos: QPoint):
        self._click_pulses.append({"pos": pos, "start_time": time.time()})

    def set_highlight(self, rect: QRectF, label: str = ""):
        self._highlight_rect = rect
        self._highlight_label = label
        self.update()

    def clear_highlight(self):
        self._highlight_rect = None
        self._highlight_label = ""
        self.update()

    def set_arrow(self, target: QPoint, label: str = ""):
        self._arrow_target = target
        self._arrow_label = label
        self.update()

    def clear_arrow(self):
        self._arrow_target = None
        self._arrow_label = ""
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        now = time.time()

        if self._highlight_rect:
            self._draw_highlight(painter)

        if self._arrow_target:
            self._draw_arrow(painter)

        if self._show_halo and len(self._trail) > 1:
            self._draw_trail(painter, now)

        if self._show_halo:
            self._draw_halo(painter)

        for pulse in self._click_pulses:
            self._draw_click_pulse(painter, pulse, now)

        painter.end()

    def _draw_halo(self, painter: QPainter):
        center = self._cursor_pos
        gradient = QRadialGradient(QPointF(center), 24)
        gradient.setColorAt(0, QColor(123, 184, 212, 50))
        gradient.setColorAt(0.6, QColor(123, 184, 212, 15))
        gradient.setColorAt(1.0, QColor(123, 184, 212, 0))
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, 24, 24)

    def _draw_trail(self, painter: QPainter, now: float):
        points = list(self._trail)
        for i in range(1, len(points)):
            age = now - points[i][1]
            alpha = max(0, int(55 * (1.0 - age / 0.8)))
            width = max(1, 3 * (1.0 - age / 0.8))
            pen = QPen(QColor(123, 184, 212, alpha), width)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(points[i - 1][0], points[i][0])

    def _draw_click_pulse(self, painter: QPainter, pulse: dict, now: float):
        elapsed = now - pulse["start_time"]
        progress = min(1.0, elapsed / 0.5)
        radius = 8 + 30 * progress
        alpha = int(110 * (1.0 - progress))

        pen = QPen(QColor(123, 184, 212, alpha), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(pulse["pos"], int(radius), int(radius))

        if progress < 0.3:
            inner_alpha = int(70 * (1.0 - progress / 0.3))
            painter.setBrush(QColor(123, 184, 212, inner_alpha))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(pulse["pos"], 5, 5)

    def _draw_highlight(self, painter: QPainter):
        rect = self._highlight_rect

        # Soft blue accent border — rounded corners
        pen = QPen(QColor(123, 184, 212, 120), 1.5)
        painter.setPen(pen)
        painter.setBrush(QColor(123, 184, 212, 14))
        painter.drawRoundedRect(rect, T.RADIUS_MD, T.RADIUS_MD)

        # Label
        if self._highlight_label:
            painter.setFont(QFont(T.FONT_FAMILY, T.FONT_XS, QFont.Medium))
            painter.setPen(QColor(T.TEXT_WHITE))
            label_rect = QRectF(rect.left(), rect.top() - 28, rect.width(), 24)
            bg_path = QPainterPath()
            bg_path.addRoundedRect(label_rect, T.RADIUS_MD, T.RADIUS_MD)
            painter.fillPath(bg_path, QColor(87, 148, 176, 200))
            painter.drawText(label_rect, Qt.AlignCenter, self._highlight_label)

    def _draw_arrow(self, painter: QPainter):
        target = self._arrow_target
        start = QPoint(target.x() + 50, target.y() - 50)

        pen = QPen(QColor(123, 184, 212, 170), 1.5)
        painter.setPen(pen)
        painter.drawLine(start, target)

        # Arrowhead
        angle = math.atan2(target.y() - start.y(), target.x() - start.x())
        arrow_size = 10
        p1 = QPoint(
            int(target.x() - arrow_size * math.cos(angle - 0.4)),
            int(target.y() - arrow_size * math.sin(angle - 0.4))
        )
        p2 = QPoint(
            int(target.x() - arrow_size * math.cos(angle + 0.4)),
            int(target.y() - arrow_size * math.sin(angle + 0.4))
        )

        path = QPainterPath()
        path.moveTo(QPointF(target))
        path.lineTo(QPointF(p1))
        path.lineTo(QPointF(p2))
        path.closeSubpath()
        painter.fillPath(path, QColor(123, 184, 212, 170))

        # Label
        if self._arrow_label:
            painter.setFont(QFont(T.FONT_FAMILY, T.FONT_XS, QFont.Medium))
            painter.setPen(QColor(T.TEXT_WHITE))
            label_pos = QPointF(start.x() + 5, start.y() - 8)
            bg_rect = QRectF(label_pos.x() - 4, label_pos.y() - 16, len(self._arrow_label) * 7 + 12, 24)
            bg_path = QPainterPath()
            bg_path.addRoundedRect(bg_rect, T.RADIUS_MD, T.RADIUS_MD)
            painter.fillPath(bg_path, QColor(87, 148, 176, 200))
            painter.drawText(bg_rect, Qt.AlignCenter, self._arrow_label)
