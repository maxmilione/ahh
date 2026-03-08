"""Step stack panel - shows plan steps with active/completed status."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QScrollArea, QFrame)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QFont, QColor, QPainter

# Solid cream used everywhere to eliminate transparency
_CREAM = "#FAF7EF"


class StepBadge(QWidget):
    """Minimal circular step number badge."""

    def __init__(self, number: int, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self._number = number
        self._text = str(number)
        self._bg_color = QColor("#EDE8DC")
        self._text_color = QColor("#8A8070")

    def set_state(self, state: str):
        if state == "active":
            self._bg_color = QColor("#D4E8F2")
            self._text_color = QColor("#3A7A9C")
            self._text = str(self._number)
        elif state == "completed":
            self._bg_color = QColor("#F0DEB0")
            self._text_color = QColor("#7A5A10")
            self._text = "\u2713"
        else:
            self._bg_color = QColor("#EDE8DC")
            self._text_color = QColor("#8A8070")
            self._text = str(self._number)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._bg_color)
        painter.drawEllipse(1, 1, 26, 26)
        painter.setPen(self._text_color)
        painter.setFont(QFont("DM Sans", 11, QFont.Bold))
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
        main_layout.setContentsMargins(10, 10, 12, 10)
        main_layout.setSpacing(10)

        # Badge
        self._badge = StepBadge(step_id, self)
        main_layout.addWidget(self._badge, 0, Qt.AlignTop)

        # Text column
        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        text_col.setContentsMargins(0, 0, 0, 0)

        self._title_label = QLabel(title)
        self._title_label.setFont(QFont("DM Sans", 13, QFont.Bold))
        self._title_label.setWordWrap(True)
        self._title_label.setStyleSheet(f"color: #4A4540; background: {_CREAM};")
        text_col.addWidget(self._title_label)

        if teach:
            self._teach_label = QLabel(teach)
            self._teach_label.setFont(QFont("DM Sans", 11, QFont.DemiBold))
            self._teach_label.setWordWrap(True)
            self._teach_label.setStyleSheet(f"color: #6A6460; background: {_CREAM};")
            text_col.addWidget(self._teach_label)
        else:
            self._teach_label = None

        main_layout.addLayout(text_col, 1)

    def set_status(self, status: str):
        self._status = status
        self._badge.set_state(status)
        self.setStyleSheet(self._style_for_status())
        if status == "completed":
            self._title_label.setStyleSheet(
                f"color: #9A9488; text-decoration: line-through; background: {_CREAM};"
            )
        elif status == "active":
            self._title_label.setStyleSheet("color: #1C1A18; background: #EEF5F9;")
        else:
            self._title_label.setStyleSheet(f"color: #4A4540; background: {_CREAM};")

    def _style_for_status(self) -> str:
        if self._status == "active":
            return f"""
                StepItem {{
                    background: #EEF5F9;
                    border: none;
                    border-radius: 10px;
                }}
            """
        return f"""
            StepItem {{
                background: {_CREAM};
                border: none;
                border-radius: 10px;
            }}
        """


class StepStack(QWidget):
    """Panel showing list of steps with status indicators."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(320)

        self._items: list[StepItem] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(0)

        # Header
        header = QLabel("  Plan")
        header.setFont(QFont("DM Sans", 15, QFont.Bold))
        header.setFixedHeight(40)
        header.setStyleSheet(f"color: #2C2A25; background: {_CREAM};")
        outer.addWidget(header)

        # Scroll area for steps
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: {_CREAM}; border: none; }}
            QWidget {{ background: {_CREAM}; }}
            QScrollBar:vertical {{ width: 3px; background: {_CREAM}; }}
            QScrollBar::handle:vertical {{ background: rgba(28,28,26,40); border-radius: 1px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        outer.addWidget(scroll)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(2, 4, 2, 4)
        self._layout.setSpacing(4)
        self._layout.addStretch()
        scroll.setWidget(self._container)

    def paintEvent(self, event):
        """Draw solid card background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(4, 4, self.width() - 8, self.height() - 8)

        # Single soft shadow
        shadow_rect = rect.adjusted(-2, 0, 2, 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(28, 28, 26, 12))
        painter.drawRoundedRect(shadow_rect, 18, 18)

        # Card background - solid warm cream
        painter.setBrush(QColor(_CREAM))
        painter.setPen(QColor(237, 232, 220))
        painter.drawRoundedRect(rect, 14, 14)

        painter.end()

    def set_steps(self, steps: list[dict]):
        """Set steps from plan. Each dict: {id, title, teach}."""
        for item in self._items:
            self._layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()

        for step in steps:
            item = StepItem(step["id"], step["title"], step.get("teach", ""))
            self._layout.insertWidget(self._layout.count() - 1, item)
            self._items.append(item)

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
