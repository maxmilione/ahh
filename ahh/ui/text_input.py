"""Text input fallback when STT fails."""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from PySide6.QtCore import Qt, Signal, QRectF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont, QColor, QPainter

from ahh.ui.theme import T


class TextInputBar(QWidget):
    """Fallback text input when voice recognition fails.

    White card with shadow, rounded input field and blue send button.
    """

    SHADOW_MARGIN = 6
    text_submitted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(60 + self.SHADOW_MARGIN * 2)

        self._opacity = 0.0

        m = self.SHADOW_MARGIN
        layout = QHBoxLayout(self)
        layout.setContentsMargins(m + T.SP_4, m + T.SP_2, m + T.SP_4, m + T.SP_2)
        layout.setSpacing(T.SP_3)

        # --- Text field ---
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type your request here...")
        self._input.setFont(QFont(T.FONT_FAMILY, T.FONT_MD))
        self._input.setMinimumHeight(40)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                color: {T.TEXT_PRIMARY};
                border: none;
                padding: 8px 4px;
                font-family: {T.FONT_FAMILY};
                font-size: {T.FONT_MD}pt;
                selection-background-color: {T.ACCENT_LIGHT};
            }}
            QLineEdit::placeholder {{
                color: {T.TEXT_PLACEHOLDER};
            }}
        """)
        self._input.returnPressed.connect(self._on_submit)
        layout.addWidget(self._input, 1)

        # --- Circular send button ---
        self._send_btn = QPushButton("\u2191")  # up arrow
        self._send_btn.setFont(QFont(T.FONT_FAMILY, 14, QFont.DemiBold))
        self._send_btn.setFixedSize(38, 38)
        self._send_btn.setCursor(Qt.PointingHandCursor)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T.ACCENT};
                border: none;
                border-radius: 19px;
                color: {T.TEXT_WHITE};
            }}
            QPushButton:hover {{
                background: {T.ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background: {T.ACCENT_PRESS};
            }}
        """)
        self._send_btn.clicked.connect(self._on_submit)
        layout.addWidget(self._send_btn)

        # --- Fade animation ---
        self._fade_anim = QPropertyAnimation(self, b"opacity")
        self._fade_anim.setDuration(T.ANIM_NORMAL)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.hide()

    # -- opacity property for fade animation --
    def _get_opacity(self):
        return self._opacity

    def _set_opacity(self, val):
        self._opacity = val
        self.update()

    opacity = Property(float, _get_opacity, _set_opacity)

    def paintEvent(self, event):
        """Draw white card with shadow and thin border."""
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

    def _on_submit(self):
        text = self._input.text().strip()
        if text:
            self.text_submitted.emit(text)
            self._input.clear()
            self.hide()

    def show_input(self):
        self._input.clear()
        self._opacity = 0.0
        self.show()
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()
        self._input.setFocus()
