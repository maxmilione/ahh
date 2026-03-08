"""Caption strip - shows what + why for each action."""
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont, QColor, QPainter, QPainterPath


class CaptionStrip(QWidget):
    """Bottom-of-screen caption showing current action explanation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(48)
        self._opacity = 1.0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(30, 30)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setFont(QFont("DM Sans", 16))
        self._icon_label.setStyleSheet("color: #E8B860;")
        layout.addWidget(self._icon_label)

        self._text_label = QLabel()
        self._text_label.setFont(QFont("DM Sans", 11))
        self._text_label.setWordWrap(True)
        self._text_label.setStyleSheet("color: #5A5445;")
        layout.addWidget(self._text_label, 1)

        self._fade_timer = QTimer()
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self._start_fade)

        self.hide()

    def _get_opacity(self):
        return self._opacity

    def _set_opacity(self, val):
        self._opacity = val
        self.update()

    opacity_prop = Property(float, _get_opacity, _set_opacity)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)

        path = QPainterPath()
        path.addRoundedRect(self.rect().toRectF(), 999, 999)
        # Warm cream pill with subtle border
        painter.fillPath(path, QColor(252, 249, 242, 240))
        painter.setPen(QColor(237, 232, 220, 180))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        painter.end()
        super().paintEvent(event)

    def show_caption(self, text: str, icon: str = "", duration_ms: int = 5000):
        """Show a caption with optional icon. Auto-fades after duration."""
        icon_map = {
            "click": "\U0001f5b1\ufe0f",
            "type": "\u2328\ufe0f",
            "navigate": "\U0001f310",
            "scroll": "\U0001f4dc",
            "search": "\U0001f50d",
            "wait": "\u23f3",
        }
        self._icon_label.setText(icon_map.get(icon, "\U0001f4a1"))
        self._text_label.setText(text)
        self._opacity = 1.0
        self.show()
        self.update()

        self._fade_timer.stop()
        self._fade_timer.start(duration_ms)

    def _start_fade(self):
        anim = QPropertyAnimation(self, b"opacity_prop")
        anim.setDuration(800)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(self.hide)
        anim.start()
        self._fade_anim = anim  # prevent GC

    def hide_caption(self):
        self._fade_timer.stop()
        self.hide()
