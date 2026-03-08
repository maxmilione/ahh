"""Confirmation modal for safety-sensitive actions."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton)
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QFont, QColor, QPainter


class ConfirmModal(QWidget):
    """Modal that asks user to confirm sensitive actions."""

    confirmed = Signal()
    cancelled = Signal()

    SHADOW_MARGIN = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400 + self.SHADOW_MARGIN * 2, 180 + self.SHADOW_MARGIN * 2)

        layout = QVBoxLayout(self)
        m = self.SHADOW_MARGIN
        layout.setContentsMargins(m + 28, m + 20, m + 28, m + 20)
        layout.setSpacing(12)

        # Title
        self._title = QLabel("Confirmation Required")
        self._title.setFont(QFont("DM Sans", 14, QFont.DemiBold))
        self._title.setStyleSheet("color: #3C3C3A; background: transparent;")
        self._title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._title)

        # Description
        self._desc = QLabel()
        self._desc.setFont(QFont("DM Sans", 12))
        self._desc.setWordWrap(True)
        self._desc.setStyleSheet("color: #7A7468; background: transparent;")
        self._desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._desc)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFont(QFont("DM Sans", 12, QFont.Medium))
        self._cancel_btn.setMinimumHeight(36)
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #E0D9C8;
                border-radius: 999px;
                color: #5A5445;
                padding: 8px 22px;
            }
            QPushButton:hover {
                background: #F0EAD8;
                border-color: #C8C0AE;
            }
        """)
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)

        self._confirm_btn = QPushButton("Proceed")
        self._confirm_btn.setFont(QFont("DM Sans", 12, QFont.Medium))
        self._confirm_btn.setMinimumHeight(36)
        self._confirm_btn.setCursor(Qt.PointingHandCursor)
        self._confirm_btn.setStyleSheet("""
            QPushButton {
                background: #E8A090;
                border: none;
                border-radius: 999px;
                color: #FFFFFF;
                padding: 8px 22px;
            }
            QPushButton:hover { background: #D97B6C; }
        """)
        self._confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(self._confirm_btn)

        layout.addLayout(btn_layout)

        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        m = self.SHADOW_MARGIN
        card_rect = QRectF(m, m, self.width() - 2 * m, self.height() - 2 * m)

        # Single soft shadow
        shadow_rect = card_rect.adjusted(-2, 0, 2, 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(28, 28, 26, 10))
        painter.drawRoundedRect(shadow_rect, 18, 18)

        # Card body
        painter.setBrush(QColor(252, 249, 242))
        painter.setPen(QColor(237, 232, 220))
        painter.drawRoundedRect(card_rect, 16, 16)
        painter.end()

    def show_confirm(self, message: str):
        self._desc.setText(message)
        self.show()
        self.raise_()

    def _on_confirm(self):
        self.hide()
        self.confirmed.emit()

    def _on_cancel(self):
        self.hide()
        self.cancelled.emit()
