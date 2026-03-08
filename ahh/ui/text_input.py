"""Text input fallback when STT fails."""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPainter, QPainterPath


class TextInputBar(QWidget):
    """Fallback text input when voice recognition fails."""

    text_submitted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(52)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type your request here...")
        self._input.setFont(QFont("DM Sans", 12))
        self._input.setMinimumHeight(38)
        self._input.setStyleSheet("""
            QLineEdit {
                background: #FAF7EF;
                border: 1px solid #E0D9C8;
                border-radius: 19px;
                padding: 8px 16px;
                color: #3C3C3A;
            }
            QLineEdit:focus {
                border-color: #B8D8E8;
                background: #FEFCF8;
            }
            QLineEdit::placeholder {
                color: #B0A890;
            }
        """)
        self._input.returnPressed.connect(self._on_submit)
        layout.addWidget(self._input, 1)

        # Circular send button
        self._send_btn = QPushButton("\u2191")  # up arrow
        self._send_btn.setFont(QFont("DM Sans", 14, QFont.DemiBold))
        self._send_btn.setFixedSize(34, 34)
        self._send_btn.setCursor(Qt.PointingHandCursor)
        self._send_btn.setStyleSheet("""
            QPushButton {
                background: #F0DEB0;
                border: none;
                border-radius: 17px;
                color: #5A4A20;
            }
            QPushButton:hover { background: #E8D098; }
            QPushButton:pressed { background: #D8C080; }
        """)
        self._send_btn.clicked.connect(self._on_submit)
        layout.addWidget(self._send_btn)

        self.hide()

    def paintEvent(self, event):
        """Draw subtle background pill."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(248, 245, 237, 200))
        path = QPainterPath()
        path.addRoundedRect(self.rect().toRectF().adjusted(2, 2, -2, -2), 999, 999)
        painter.drawPath(path)
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
        self.show()
        self._input.setFocus()
