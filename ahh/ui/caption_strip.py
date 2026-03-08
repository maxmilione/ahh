"""Caption strip - shows what + why for each action."""
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, QTimer, QRectF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont, QColor, QPainter, QPainterPath

from ahh.ui.theme import T


class CaptionStrip(QWidget):
    """Bottom-of-screen caption card."""

    SHADOW_MARGIN = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(52 + self.SHADOW_MARGIN * 2)
        self._opacity = 0.0

        m = self.SHADOW_MARGIN
        layout = QHBoxLayout(self)
        layout.setContentsMargins(m + T.SP_5, m + T.SP_2, m + T.SP_5, m + T.SP_2)
        layout.setSpacing(T.SP_3)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(30, 30)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setFont(QFont(T.FONT_FAMILY, T.FONT_ICON))
        self._icon_label.setStyleSheet(f"color: {T.TEXT_BODY}; background: transparent;")
        layout.addWidget(self._icon_label)

        self._text_label = QLabel()
        self._text_label.setFont(QFont(T.FONT_FAMILY, T.FONT_MD, QFont.Medium))
        self._text_label.setWordWrap(True)
        self._text_label.setStyleSheet(f"color: {T.TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(self._text_label, 1)

        self._fade_timer = QTimer()
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self._start_fade_out)
        self.hide()

    def _get_opacity(self):
        return self._opacity

    def _set_opacity(self, val):
        self._opacity = val
        self.update()

    opacity_prop = Property(float, _get_opacity, _set_opacity)

    def paintEvent(self, event):
        if self._opacity <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)

        m = self.SHADOW_MARGIN
        card_rect = QRectF(m, m, self.width() - 2 * m, self.height() - 2 * m)

        # Subtle shadow
        shadow = card_rect.adjusted(0, 1, 0, 3)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 10))
        painter.drawRoundedRect(shadow, T.RADIUS_LG, T.RADIUS_LG)

        # White card with thin border
        painter.setBrush(QColor(T.WHITE))
        painter.setPen(QColor(T.BORDER))
        painter.drawRoundedRect(card_rect, T.RADIUS_LG, T.RADIUS_LG)
        painter.end()
        super().paintEvent(event)

    def show_caption(self, text: str, icon: str = "", duration_ms: int = 5000):
        icon_map = {
            "click": "\U0001f5b1\ufe0f", "type": "\u2328\ufe0f",
            "navigate": "\U0001f310", "scroll": "\U0001f4dc",
            "search": "\U0001f50d", "wait": "\u23f3",
        }
        self._icon_label.setText(icon_map.get(icon, "\U0001f4a1"))
        self._text_label.setText(text)
        self.show()
        anim = QPropertyAnimation(self, b"opacity_prop")
        anim.setDuration(T.ANIM_FAST)
        anim.setStartValue(self._opacity)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        self._fade_in_anim = anim
        self._fade_timer.stop()
        self._fade_timer.start(duration_ms)

    def _start_fade_out(self):
        anim = QPropertyAnimation(self, b"opacity_prop")
        anim.setDuration(600)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(self.hide)
        anim.start()
        self._fade_out_anim = anim

    def hide_caption(self):
        self._fade_timer.stop()
        self._opacity = 0.0
        self.hide()
