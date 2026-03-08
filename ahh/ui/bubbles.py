"""Clarify bubbles - clean option bubbles near the plant."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton)
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QFont, QColor, QPainter


class BubbleOption(QPushButton):
    """Single bubble option button - minimal pastel style."""

    def __init__(self, text: str, index: int, parent=None):
        super().__init__(text, parent)
        self.index = index
        self.setFont(QFont("DM Sans", 12))
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)
        self.setStyleSheet("""
            QPushButton {
                background: #F8F5ED;
                border: 1px solid #E8E2D2;
                border-radius: 999px;
                padding: 8px 16px;
                text-align: left;
                color: #4A4540;
            }
            QPushButton:hover {
                background: #EEF5F9;
                border-color: #B8D8E8;
            }
            QPushButton:pressed {
                background: #D4E8F2;
                border-color: #90C4D8;
                color: #3A6A80;
            }
        """)


class ClarifyBubbles(QWidget):
    """Shows a question with 2-3 option bubbles for user to choose."""

    option_selected = Signal(int, str)  # index, text
    closed = Signal()

    SHADOW_MARGIN = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(320 + self.SHADOW_MARGIN * 2)

        self._layout = QVBoxLayout(self)
        m = self.SHADOW_MARGIN
        self._layout.setContentsMargins(m + 14, m + 10, m + 14, m + 14)
        self._layout.setSpacing(6)

        # Close button
        self._close_btn = QPushButton("\u2715")
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(90, 84, 69, 40);
                color: #F5F0E2;
                border: none;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #E8A090;
            }
        """)
        self._close_btn.clicked.connect(self._on_close)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(self._close_btn)
        self._layout.addLayout(close_row)

        # Question label
        self._question_label = QLabel()
        self._question_label.setFont(QFont("DM Sans", 12, QFont.Medium))
        self._question_label.setWordWrap(True)
        self._question_label.setStyleSheet("""
            QLabel {
                color: #3C3C3A;
                background: transparent;
                padding: 8px 4px;
            }
        """)
        self._layout.addWidget(self._question_label)

        self._buttons: list[BubbleOption] = []
        self.hide()

    def paintEvent(self, event):
        """Draw clean card background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        m = self.SHADOW_MARGIN
        card_rect = QRectF(m, m, self.width() - 2 * m, self.height() - 2 * m)

        # Single soft shadow
        shadow_rect = card_rect.adjusted(-2, 0, 2, 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(28, 28, 26, 10))
        painter.drawRoundedRect(shadow_rect, 16, 16)

        # Card body - warm cream
        painter.setBrush(QColor(252, 249, 242, 248))
        painter.setPen(QColor(237, 232, 220))
        painter.drawRoundedRect(card_rect, 14, 14)
        painter.end()

    def show_question(self, question: str, choices: list[str]):
        """Display question with choices."""
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
        self.show()

    def _on_choice(self, index: int, text: str):
        self.option_selected.emit(index, text)
        self.hide()

    def _on_close(self):
        self.hide()
        self.closed.emit()

    def hide_bubbles(self):
        self.hide()
