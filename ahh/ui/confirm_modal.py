"""Confirmation modal for safety-sensitive actions."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton)
from PySide6.QtCore import Qt, Signal, QRectF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont, QColor, QPainter

from ahh.ui.theme import T


class ConfirmModal(QWidget):
    """Modal that asks user to confirm sensitive actions."""

    confirmed = Signal()
    cancelled = Signal()
    SHADOW_MARGIN = T.SHADOW_MARGIN + 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420 + self.SHADOW_MARGIN * 2, 190 + self.SHADOW_MARGIN * 2)
        self._anim_progress = 0.0

        layout = QVBoxLayout(self)
        m = self.SHADOW_MARGIN
        layout.setContentsMargins(m + T.SP_8, m + T.SP_6, m + T.SP_8, m + T.SP_6)
        layout.setSpacing(T.SP_3)

        self._title = QLabel("Confirmation Required")
        self._title.setFont(QFont(T.FONT_HEADING, T.FONT_XL))
        self._title.setStyleSheet(f"color: {T.TEXT_PRIMARY}; background: transparent;")
        self._title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._title)

        self._desc = QLabel()
        self._desc.setFont(QFont(T.FONT_FAMILY, T.FONT_MD))
        self._desc.setWordWrap(True)
        self._desc.setStyleSheet(f"color: {T.TEXT_SECONDARY}; background: transparent;")
        self._desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._desc)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(T.SP_3)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFont(QFont(T.FONT_FAMILY, T.FONT_MD, QFont.Medium))
        self._cancel_btn.setMinimumHeight(38)
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.setStyleSheet(T.btn_pill(bg="transparent"))
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)

        self._confirm_btn = QPushButton("Proceed")
        self._confirm_btn.setFont(QFont(T.FONT_FAMILY, T.FONT_MD, QFont.Medium))
        self._confirm_btn.setMinimumHeight(38)
        self._confirm_btn.setCursor(Qt.PointingHandCursor)
        self._confirm_btn.setStyleSheet(T.btn_accent())
        self._confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(self._confirm_btn)
        layout.addLayout(btn_layout)

        self._fade_anim = QPropertyAnimation(self, b"anim_progress")
        self._fade_anim.setDuration(T.ANIM_NORMAL)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
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

        # Shadow
        shadow = card_rect.adjusted(0, 1, 0, 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 10))
        painter.drawRoundedRect(shadow, T.RADIUS_LG + 2, T.RADIUS_LG + 2)

        # Card
        painter.setBrush(QColor(T.WHITE))
        painter.setPen(QColor(T.BORDER))
        painter.drawRoundedRect(card_rect, T.RADIUS_LG, T.RADIUS_LG)
        painter.end()

    def show_confirm(self, message: str):
        self._desc.setText(message)
        self._anim_progress = 0.0
        self.show()
        self.raise_()
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def _on_confirm(self):
        self.hide()
        self.confirmed.emit()

    def _on_cancel(self):
        self.hide()
        self.cancelled.emit()
