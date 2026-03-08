"""Clarify bubbles - clean option bubbles near the hand."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton)
from PySide6.QtCore import Qt, Signal, QRectF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont, QColor, QPainter

from ahh.ui.theme import T


class BubbleOption(QPushButton):
    """Single bubble option button."""

    def __init__(self, text: str, index: int, parent=None):
        super().__init__(text, parent)
        self.index = index
        self.setFont(QFont(T.FONT_FAMILY, T.FONT_MD))
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(42)
        self.setStyleSheet(T.btn_pill(min_h=42))


class ClarifyBubbles(QWidget):
    """Shows a question with 2-3 option bubbles."""

    option_selected = Signal(int, str)
    closed = Signal()
    SHADOW_MARGIN = T.SHADOW_MARGIN

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(340 + self.SHADOW_MARGIN * 2)
        self._anim_progress = 0.0

        self._layout = QVBoxLayout(self)
        m = self.SHADOW_MARGIN
        self._layout.setContentsMargins(m + T.SP_4, m + T.SP_3, m + T.SP_4, m + T.SP_4)
        self._layout.setSpacing(T.SP_2)

        self._close_btn = QPushButton("\u2715")
        self._close_btn.setFixedSize(26, 26)
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T.BG_HOVER};
                color: {T.TEXT_MUTED};
                border: none;
                border-radius: 13px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {T.ACCENT};
                color: {T.TEXT_WHITE};
            }}
        """)
        self._close_btn.clicked.connect(self._on_close)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(self._close_btn)
        self._layout.addLayout(close_row)

        self._question_label = QLabel()
        self._question_label.setFont(QFont(T.FONT_HEADING, T.FONT_MD))
        self._question_label.setWordWrap(True)
        self._question_label.setStyleSheet(f"color: {T.TEXT_PRIMARY}; background: transparent; padding: {T.SP_2}px {T.SP_1}px;")
        self._layout.addWidget(self._question_label)

        self._buttons: list[BubbleOption] = []
        self.hide()

    def _get_anim_progress(self):
        return self._anim_progress

    def _set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    anim_progress = Property(float, _get_anim_progress, _set_anim_progress)

    def paintEvent(self, event):
        if self._anim_progress <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._anim_progress)
        m = self.SHADOW_MARGIN
        card_rect = QRectF(m, m, self.width() - 2 * m, self.height() - 2 * m)

        shadow = card_rect.adjusted(0, 1, 0, 3)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 8))
        painter.drawRoundedRect(shadow, T.RADIUS_LG, T.RADIUS_LG)

        painter.setBrush(QColor(T.WHITE))
        painter.setPen(QColor(T.BORDER))
        painter.drawRoundedRect(card_rect, T.RADIUS_LG, T.RADIUS_LG)
        painter.end()

    def show_question(self, question: str, choices: list[str]):
        for btn in self._buttons:
            self._layout.removeWidget(btn)
            btn.deleteLater()
        self._buttons.clear()
        self._question_label.setText(question)
        for i, choice in enumerate(choices):
            btn = BubbleOption(choice, i)
            btn.clicked.connect(lambda checked, idx=i, txt=choice: self._on_choice(idx, txt))
            self._layout.addWidget(btn)
            self._buttons.append(btn)
        self.adjustSize()
        self._anim_progress = 0.0
        self.show()
        anim = QPropertyAnimation(self, b"anim_progress")
        anim.setDuration(T.ANIM_NORMAL)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        self._show_anim = anim

    def _on_choice(self, index: int, text: str):
        self.option_selected.emit(index, text)
        self.hide()

    def _on_close(self):
        self.hide()
        self.closed.emit()

    def hide_bubbles(self):
        self.hide()
