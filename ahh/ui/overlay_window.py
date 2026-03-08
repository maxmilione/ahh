"""Main overlay window - manages multiple windows for click-through + interactive elements."""
import math
import ctypes
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                QPushButton, QLabel, QApplication)
from PySide6.QtCore import Qt, QRect, Signal, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPainter, QPainterPath, QScreen, QShortcut, QKeySequence

from .hand_widget import HandWidget
from .waveform_widget import WaveformWidget
from .step_stack import StepStack
from .bubbles import ClarifyBubbles
from .caption_strip import CaptionStrip
from .confirm_modal import ConfirmModal
from .cursor_overlay import CursorOverlay
from .text_input import TextInputBar


def make_click_through(hwnd: int):
    """Make a window click-through using Win32 API."""
    GWL_EXSTYLE = -20
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_LAYERED = 0x00080000
    WS_EX_TOOLWINDOW = 0x00000080
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style = style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


class VisualOverlay(QMainWindow):
    """Full-screen click-through overlay for cursor effects and captions."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        screen = QApplication.primaryScreen()
        geom = screen.geometry()
        self.setGeometry(geom)

        central = QWidget()
        central.setAttribute(Qt.WA_TranslucentBackground)
        self.setCentralWidget(central)

        # Cursor overlay (full screen)
        self.cursor_overlay = CursorOverlay(central)
        self.cursor_overlay.setGeometry(0, 0, geom.width(), geom.height())

        # Caption strip (bottom center)
        self.caption = CaptionStrip(central)
        caption_w = min(700, geom.width() - 200)
        self.caption.setFixedWidth(caption_w)
        self.caption.move((geom.width() - caption_w) // 2, geom.height() - 80)

    def showEvent(self, event):
        super().showEvent(event)
        # Make click-through after showing
        QTimer.singleShot(50, self._apply_click_through)

    def _apply_click_through(self):
        try:
            make_click_through(int(self.winId()))
        except Exception:
            pass


class HandWindow(QMainWindow):
    """Small always-on-top window that holds the hand widget."""

    hand_clicked = Signal()
    hand_double_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(140, 220)

        # Position bottom-right
        screen = QApplication.primaryScreen()
        geom = screen.geometry()
        self._home_pos = QPoint(geom.width() - 160, geom.height() - 245)
        self.move(self._home_pos)

        self.hand = HandWidget(self)
        self.hand.move(0, 0)

        # Waveform below hand
        self.waveform = WaveformWidget(self)
        self.waveform.move(10, 125)

        self._drag_pos = None
        self._press_pos = None
        self._is_dragging = False
        self._is_pointing = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        # Smooth movement animation
        self._move_anim = QPropertyAnimation(self, b"pos")
        self._move_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._move_anim.setDuration(500)

        # Deferred single-click timer for double-click detection
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(250)
        self._click_timer.timeout.connect(self._emit_single_click)

    def _emit_single_click(self):
        self.hand_clicked.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            self._press_pos = event.globalPosition().toPoint()
            self._is_dragging = False

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._press_pos
            if delta.manhattanLength() > 5:
                self._is_dragging = True
                self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self._is_dragging:
                # Defer single click — double click will cancel it
                self._click_timer.start()
            self._drag_pos = None
            self._press_pos = None
            self._is_dragging = False

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._click_timer.stop()  # Cancel pending single click
            self.hand_double_clicked.emit()

    def enterEvent(self, event):
        self.hand.start_hover_wave()

    def leaveEvent(self, event):
        self.hand.stop_hover_wave()

    # The finger's natural direction at 0° rotation, measured from the
    # widget center (60,60) to the fingertip (~31,9) in screen coords.
    # atan2(-51, -29) ≈ -120°.  Upper-left.
    _FINGER_NATURAL_ANGLE = -120.0  # degrees
    _TIP_DISTANCE = 59              # px from widget center to fingertip
    _TIP_GAP = 25                   # extra gap so tip doesn't cover target

    def point_at(self, target: QPoint, duration_ms: int = 1000):
        """Move hand so the fingertip points at the target.

        1. Position the widget so its center is offset from the target
           (hand body away, finger toward).
        2. Rotate the frozen pointing image so the fingertip aims at the
           target, compensating for the finger's natural -120° angle.
        """
        entering = not self._is_pointing
        self._is_pointing = True
        self.waveform.hide()

        screen = QApplication.primaryScreen().geometry()
        widget_cx = 60  # widget center in window coords (120x120 widget)
        widget_cy = 60

        # Total distance from widget center to target
        total_offset = self._TIP_DISTANCE + self._TIP_GAP

        # Approach from the side with more room
        dx = -1 if target.x() > screen.width() / 2 else 1
        dy = -1 if target.y() > screen.height() / 2 else 1

        # Hand center in screen coords (offset from target)
        hand_cx = target.x() + dx * total_offset
        hand_cy = target.y() + dy * total_offset

        # Window top-left
        dest_x = int(hand_cx - widget_cx)
        dest_y = int(hand_cy - widget_cy)

        # Clamp to screen
        dest_x = max(0, min(dest_x, screen.width() - self.width()))
        dest_y = max(0, min(dest_y, screen.height() - self.height()))

        # Recalculate actual center after clamping
        actual_cx = dest_x + widget_cx
        actual_cy = dest_y + widget_cy

        # Desired angle: from hand center toward target
        desired_angle = math.degrees(
            math.atan2(target.y() - actual_cy, target.x() - actual_cx)
        )

        # Rotation = desired direction minus the finger's natural direction
        rotation = desired_angle - self._FINGER_NATURAL_ANGLE

        dest = QPoint(dest_x, dest_y)
        self.hand.set_pointing(True, rotation)

        if entering:
            # First move into pointing mode: teleport instantly so the
            # waving hand at home doesn't leave a ghost on screen.
            self._move_anim.stop()
            self.hide()
            self.move(dest)
            self.show()
            self.raise_()
        else:
            # Subsequent moves: animate smoothly between targets
            self._move_anim.stop()
            self._move_anim.setStartValue(self.pos())
            self._move_anim.setEndValue(dest)
            self._move_anim.setDuration(duration_ms)
            self._move_anim.start()

    def return_home(self, duration_ms: int = 400):
        """Return hand to its home position and exit pointing mode."""
        self._is_pointing = False
        self.hand.set_pointing(False)
        self.waveform.show()

        self._move_anim.stop()
        self._move_anim.setStartValue(self.pos())
        self._move_anim.setEndValue(self._home_pos)
        self._move_anim.setDuration(duration_ms)
        self._move_anim.start()


class SpeechBubbleWindow(QMainWindow):
    """Floating speech bubble that shows what the hand is saying."""

    BUBBLE_MAX_W = 270
    TAIL_SIZE = 12
    SHADOW_M = 10  # margin for shadow rendering

    def __init__(self, hand_win: HandWindow):
        super().__init__()
        self._hand_win = hand_win
        self._tail_below = True  # True = tail on bottom (bubble above hand)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        central = QWidget()
        central.setAttribute(Qt.WA_TranslucentBackground)
        self.setCentralWidget(central)

        self._label = QLabel(central)
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._label.setFont(QFont("DM Sans", 12))
        self._label.setStyleSheet("""
            QLabel {
                background: transparent;
                padding: 12px 14px;
                color: #3C3C3A;
            }
        """)
        self._label.setMaximumWidth(self.BUBBLE_MAX_W)

        self.hide()

    def show_bubble(self, text: str):
        self._label.setText(text)
        self._label.adjustSize()

        m = self.SHADOW_M
        lw = min(self._label.sizeHint().width(), self.BUBBLE_MAX_W)
        lh = self._label.sizeHint().height()
        self._label.setFixedSize(lw, lh)
        win_w = lw + m * 2
        win_h = lh + self.TAIL_SIZE + m * 2
        self.setFixedSize(win_w, win_h)

        hand_pos = self._hand_win.pos()
        x = hand_pos.x() + self._hand_win.width() - win_w + m - 5

        # If bubble would go above the screen, show below the hand instead
        y_above = hand_pos.y() - win_h + m + 2
        if y_above < 0:
            self._tail_below = False  # tail points up (bubble is below hand)
            y = hand_pos.y() + self._hand_win.height() - m - 2
        else:
            self._tail_below = True   # tail points down (bubble is above hand)
            y = y_above
        self.move(x, y)

        # Position label after the tail if tail is on top
        if self._tail_below:
            self._label.move(m, m)
        else:
            self._label.move(m, m + self.TAIL_SIZE)
        self.show()
        self.raise_()

    def hide_bubble(self):
        self.hide()

    def paintEvent(self, event):
        """Draw clean speech bubble with subtle shadow and adaptive tail."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        m = self.SHADOW_M
        from PySide6.QtCore import QRectF
        tail_h = self.TAIL_SIZE

        if self._tail_below:
            # Tail on bottom — bubble body at top
            card_rect = QRectF(m, m,
                               self.width() - 2 * m,
                               self.height() - 2 * m - tail_h)
        else:
            # Tail on top — bubble body below tail
            card_rect = QRectF(m, m + tail_h,
                               self.width() - 2 * m,
                               self.height() - 2 * m - tail_h)

        # Single soft shadow
        shadow_rect = card_rect.adjusted(-2, 0, 2, 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(28, 28, 26, 10))
        painter.drawRoundedRect(shadow_rect, 16, 16)

        # Bubble body
        painter.setBrush(QColor(252, 249, 242))
        painter.setPen(QColor(237, 232, 220))
        painter.drawRoundedRect(card_rect, 14, 14)

        # Draw tail
        tail_x = card_rect.right() - 30

        if self._tail_below:
            # Tail pointing down-right
            tail_top = card_rect.bottom() - 1
            path = QPainterPath()
            path.moveTo(tail_x, tail_top)
            path.cubicTo(
                tail_x + 4, tail_top + tail_h * 0.6,
                tail_x + 10, tail_top + tail_h,
                tail_x + 14, tail_top + tail_h
            )
            path.cubicTo(
                tail_x + 11, tail_top + tail_h * 0.4,
                tail_x + 18, tail_top,
                tail_x + 22, tail_top
            )
            path.closeSubpath()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(252, 249, 242))
            painter.drawPath(path)

            # Tail border
            painter.setPen(QColor(237, 232, 220))
            painter.setBrush(Qt.NoBrush)
            border_path = QPainterPath()
            border_path.moveTo(tail_x, tail_top)
            border_path.cubicTo(
                tail_x + 4, tail_top + tail_h * 0.6,
                tail_x + 10, tail_top + tail_h,
                tail_x + 14, tail_top + tail_h
            )
            painter.drawPath(border_path)
        else:
            # Tail pointing up-right
            tail_bot = card_rect.top() + 1
            path = QPainterPath()
            path.moveTo(tail_x, tail_bot)
            path.cubicTo(
                tail_x + 4, tail_bot - tail_h * 0.6,
                tail_x + 10, tail_bot - tail_h,
                tail_x + 14, tail_bot - tail_h
            )
            path.cubicTo(
                tail_x + 11, tail_bot - tail_h * 0.4,
                tail_x + 18, tail_bot,
                tail_x + 22, tail_bot
            )
            path.closeSubpath()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(252, 249, 242))
            painter.drawPath(path)

            # Tail border
            painter.setPen(QColor(237, 232, 220))
            painter.setBrush(Qt.NoBrush)
            border_path = QPainterPath()
            border_path.moveTo(tail_x, tail_bot)
            border_path.cubicTo(
                tail_x + 4, tail_bot - tail_h * 0.6,
                tail_x + 10, tail_bot - tail_h,
                tail_x + 14, tail_bot - tail_h
            )
            painter.drawPath(border_path)

        painter.end()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(50, self._apply_click_through)

    def _apply_click_through(self):
        try:
            make_click_through(int(self.winId()))
        except Exception:
            pass


class StepStackWindow(QMainWindow):
    """Separate always-on-top window for the step stack (view only, click-through)."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        screen = QApplication.primaryScreen()
        geom = screen.geometry()
        self.setGeometry(geom.width() - 340, 40, 320, geom.height() - 320)

        self.step_stack = StepStack(self)
        self.step_stack.move(0, 0)
        self.step_stack.setFixedHeight(geom.height() - 320)
        self.step_stack.show()

        self.hide()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(50, self._apply_click_through)

    def _apply_click_through(self):
        try:
            make_click_through(int(self.winId()))
        except Exception:
            pass


class StopButtonWindow(QMainWindow):
    """Tiny always-on-top window for the STOP button."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        screen = QApplication.primaryScreen()
        geom = screen.geometry()
        self.setFixedSize(90, 38)
        self.move(geom.width() - 110, 12)

        self.stop_btn = QPushButton("\u25a0 Stop", self)
        self.stop_btn.setFont(QFont("DM Sans", 12, QFont.Medium))
        self.stop_btn.setFixedSize(90, 38)
        self.stop_btn.move(0, 0)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: #E8A090;
                border: none;
                border-radius: 999px;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background: #D97B6C;
            }
        """)

        self.hide()


class InteractivePopup(QMainWindow):
    """Popup window for interactive elements (bubbles, modal, text input).

    Only shown when user interaction is needed. Full screen with transparent bg.
    """

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        screen = QApplication.primaryScreen()
        geom = screen.geometry()
        self.setGeometry(geom)

        central = QWidget()
        central.setAttribute(Qt.WA_TranslucentBackground)
        self.setCentralWidget(central)

        # Clarify bubbles (near hand, left of it)
        self.bubbles = ClarifyBubbles(central)
        self.bubbles.move(geom.width() - 540, geom.height() - 450)

        # Text input fallback (bottom center)
        caption_w = min(700, geom.width() - 200)
        self.text_input = TextInputBar(central)
        self.text_input.setFixedWidth(caption_w)
        self.text_input.move((geom.width() - caption_w) // 2, geom.height() - 140)

        # Confirm modal (center, accounting for shadow margin)
        self.confirm_modal = ConfirmModal(central)
        cm_w = 400 + self.confirm_modal.SHADOW_MARGIN * 2
        cm_h = 180 + self.confirm_modal.SHADOW_MARGIN * 2
        self.confirm_modal.move(
            (geom.width() - cm_w) // 2,
            (geom.height() - cm_h) // 2
        )

        self.hide()

    def has_visible_content(self) -> bool:
        """Check if any interactive content is visible."""
        return (self.bubbles.isVisible() or
                self.text_input.isVisible() or
                self.confirm_modal.isVisible())


class OverlayWindow:
    """Manages all overlay windows as a unified interface."""

    def __init__(self):
        # Visual layer (click-through, always visible)
        self._visual = VisualOverlay()

        # Hand window (always visible, draggable, clickable)
        self._hand_win = HandWindow()

        # Step stack (click-through, view only)
        self._step_win = StepStackWindow()

        # Stop button (small clickable window)
        self._stop_win = StopButtonWindow()

        # Speech bubble (floats above hand)
        self._speech_win = SpeechBubbleWindow(self._hand_win)

        # Interactive popup (shown only when bubbles/modal/text needed)
        self._popup = InteractivePopup()

        # Expose components for external access
        self.cursor_overlay = self._visual.cursor_overlay
        self.caption = self._visual.caption
        self.hand = self._hand_win.hand
        self.waveform = self._hand_win.waveform
        self.step_stack = self._step_win.step_stack
        self.bubbles = self._popup.bubbles
        self.text_input = self._popup.text_input
        self.confirm_modal = self._popup.confirm_modal

        # Signals
        self.hand_clicked = self._hand_win.hand_clicked
        self.hand_double_clicked = self._hand_win.hand_double_clicked
        self.stop_requested = self._stop_win.stop_btn.clicked

        # ESC shortcut (via hand window which is always visible)
        self._esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self._hand_win)

    def show(self):
        self._visual.show()
        self._hand_win.show()

    def show_stop_button(self):
        self._stop_win.show()
        self._stop_win.raise_()

    def hide_stop_button(self):
        self._stop_win.hide()

    def show_step_stack(self):
        self._step_win.show()
        self._step_win.raise_()

    def hide_step_stack(self):
        self._step_win.hide()

    def set_interactive(self, interactive: bool):
        """Show/hide the interactive popup layer."""
        if interactive:
            self._popup.show()
            self._popup.raise_()
        else:
            if not self._popup.has_visible_content():
                self._popup.hide()

    def show_text_input(self):
        """Show text input with proper focus."""
        self._popup.show()
        self._popup.raise_()
        self._popup.activateWindow()
        self.text_input.show_input()
        self.text_input.raise_()

    def show_speech_bubble(self, text: str):
        self._speech_win.show_bubble(text)

    def hide_speech_bubble(self):
        self._speech_win.hide_bubble()

    def point_hand_at(self, target: QPoint):
        """Move the hand to point at a screen target."""
        self._hand_win.point_at(target)

    def return_hand_home(self):
        """Return the hand to its home position."""
        self._hand_win.return_home()

    @property
    def esc_shortcut(self):
        return self._esc_shortcut
