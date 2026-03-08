"""Step stack panel - shows plan steps with active/completed status."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QScrollArea, QFrame, QGraphicsOpacityEffect)
from PySide6.QtCore import Qt, QRectF, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPainter

from ahh.ui.theme import T


class StepBadge(QWidget):
    """Minimal circular step number badge."""

    def __init__(self, number: int, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self._number = number
        self._text = str(number)
        self._bg_color = QColor(T.BORDER)
        self._text_color = QColor(T.TEXT_MUTED)

    def set_state(self, state: str):
        if state == "active":
            self._bg_color = QColor(T.ACCENT)
            self._text_color = QColor(T.TEXT_WHITE)
            self._text = str(self._number)
        elif state == "completed":
            self._bg_color = QColor(T.CHECK_BG)
            self._text_color = QColor(T.CHECK_TEXT)
            self._text = "\u2713"
        else:
            self._bg_color = QColor(T.BORDER)
            self._text_color = QColor(T.TEXT_MUTED)
            self._text = str(self._number)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._bg_color)
        painter.drawEllipse(1, 1, 26, 26)
        painter.setPen(self._text_color)
        painter.setFont(QFont(T.FONT_FAMILY, T.FONT_SM, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, self._text)
        painter.end()


class StepItem(QFrame):
    """Single step in the step stack."""

    def __init__(self, step_id: int, title: str, teach: str, parent=None):
        super().__init__(parent)
        self.step_id = step_id
        self._status = "pending"

        self.setMinimumHeight(56)
        self.setStyleSheet(self._style_for_status())

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(T.SP_3, T.SP_3, T.SP_3, T.SP_3)
        main_layout.setSpacing(T.SP_3)

        self._badge = StepBadge(step_id, self)
        main_layout.addWidget(self._badge, 0, Qt.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(T.SP_1)
        text_col.setContentsMargins(0, 2, 0, 0)

        self._title_label = QLabel(title)
        self._title_label.setFont(QFont(T.FONT_HEADING, T.FONT_LG))
        self._title_label.setWordWrap(True)
        self._title_label.setStyleSheet(f"color: {T.TEXT_BODY}; background: transparent;")
        text_col.addWidget(self._title_label)

        if teach:
            self._teach_label = QLabel(teach)
            self._teach_label.setFont(QFont(T.FONT_FAMILY, T.FONT_SM))
            self._teach_label.setWordWrap(True)
            self._teach_label.setStyleSheet(f"color: {T.TEXT_SECONDARY}; background: transparent;")
            text_col.addWidget(self._teach_label)
        else:
            self._teach_label = None

        main_layout.addLayout(text_col, 1)

        # Opacity effect for fade-in
        self._opacity_fx = QGraphicsOpacityEffect(self)
        self._opacity_fx.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_fx)

    def fade_in(self, delay_ms: int = 0):
        anim = QPropertyAnimation(self._opacity_fx, b"opacity", self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(T.ANIM_SLOW)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        if delay_ms:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(delay_ms, anim.start)
        else:
            anim.start()
        self._fade_anim = anim

    def set_status(self, status: str):
        self._status = status
        self._badge.set_state(status)
        self.setStyleSheet(self._style_for_status())

        if status == "completed":
            self._title_label.setStyleSheet(
                f"color: {T.TEXT_HINT}; text-decoration: line-through; background: transparent;"
            )
            if self._teach_label:
                self._teach_label.setStyleSheet(
                    f"color: {T.TEXT_PLACEHOLDER}; background: transparent;"
                )
        elif status == "active":
            self._title_label.setStyleSheet(
                f"color: {T.TEXT_PRIMARY}; background: transparent;"
            )
            if self._teach_label:
                self._teach_label.setStyleSheet(
                    f"color: {T.TEXT_SECONDARY}; background: transparent;"
                )
        else:
            self._title_label.setStyleSheet(
                f"color: {T.TEXT_BODY}; background: transparent;"
            )
            if self._teach_label:
                self._teach_label.setStyleSheet(
                    f"color: {T.TEXT_SECONDARY}; background: transparent;"
                )

    def _style_for_status(self) -> str:
        if self._status == "active":
            return f"""
                StepItem {{
                    background: {T.ACTIVE_BG};
                    border: none;
                    border-radius: {T.RADIUS_MD}px;
                }}
            """
        return f"""
            StepItem {{
                background: {T.WHITE};
                border: none;
                border-radius: {T.RADIUS_MD}px;
            }}
        """


class StepStack(QWidget):
    """Panel showing list of steps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(320)
        self._items: list[StepItem] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(T.SP_3, T.SP_3, T.SP_3, T.SP_3)
        outer.setSpacing(0)

        header = QLabel("  Plan")
        header.setFont(QFont(T.FONT_HEADING, T.FONT_XXL))
        header.setFixedHeight(44)
        header.setStyleSheet(f"color: {T.TEXT_PRIMARY}; background: {T.WHITE};")
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: {T.WHITE}; border: none; }}
            QWidget {{ background: {T.WHITE}; }}
            QScrollBar:vertical {{ width: 3px; background: {T.WHITE}; }}
            QScrollBar::handle:vertical {{ background: rgba(0,0,0,25); border-radius: 1px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        outer.addWidget(scroll)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(2, T.SP_1, 2, T.SP_1)
        self._layout.setSpacing(T.SP_1)
        self._layout.addStretch()
        scroll.setWidget(self._container)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(4, 4, self.width() - 8, self.height() - 8)

        # Soft shadow
        shadow = rect.adjusted(0, 1, 0, 3)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 8))
        painter.drawRoundedRect(shadow, T.RADIUS_LG + 2, T.RADIUS_LG + 2)

        # Card
        painter.setBrush(QColor(T.WHITE))
        painter.setPen(QColor(T.BORDER))
        painter.drawRoundedRect(rect, T.RADIUS_LG, T.RADIUS_LG)
        painter.end()

    def set_steps(self, steps: list[dict]):
        for item in self._items:
            self._layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()
        for i, step in enumerate(steps):
            item = StepItem(step["id"], step["title"], step.get("teach", ""))
            self._layout.insertWidget(self._layout.count() - 1, item)
            self._items.append(item)
            item.fade_in(delay_ms=i * 80)

    def set_step_active(self, step_id: int):
        for item in self._items:
            if item.step_id == step_id:
                item.set_status("active")
            elif item._status == "active":
                item.set_status("completed")

    def set_step_completed(self, step_id: int):
        for item in self._items:
            if item.step_id == step_id:
                item.set_status("completed")

    def clear_steps(self):
        for item in self._items:
            self._layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()
