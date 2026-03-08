"""Hand widget - waving hand with pointing mode for plan execution."""
import os
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QColor, QMovie, QPainter, QPixmap


class HandWidget(QWidget):
    """Waving hand widget that plays an animated GIF.

    Modes:
    - Default: Static first frame of waving hand
    - Hover: Plays wave GIF twice
    - Listening: Plays wave GIF + indicator dot
    - Pointing: Plays transition GIF (open->point), freezes on last frame, rotates toward target
    """

    clicked = Signal()
    transition_done = Signal()  # emitted when pointing transition GIF finishes

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listening = False
        self._hovered = False
        self._pointing = False
        self._point_frozen = False  # True when frozen on last frame of pointing GIF
        self._rotation = 0.0
        self._frozen_pixmap = None  # last frame of pointing GIF, cached

        # Red dot blinking state
        self._show_red_dot = False
        self._dot_visible = True
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(500)
        self._blink_timer.timeout.connect(self._toggle_dot)

        self.setFixedSize(120, 120)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._setup_ui()

    def _setup_ui(self):
        # Hand GIF label (used for waving mode)
        self._hand_label = QLabel(self)
        self._hand_label.setAlignment(Qt.AlignCenter)
        self._hand_label.setAttribute(Qt.WA_TranslucentBackground)
        self._hand_label.setFixedSize(120, 120)
        self._hand_label.move(0, 0)

        # Load waving hand GIF
        asset_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
        wave_path = os.path.normpath(os.path.join(asset_dir, "waving_hand.gif"))

        self._movie = QMovie(wave_path)
        self._movie.setScaledSize(QSize(110, 110))
        self._movie.setSpeed(275)  # 2.75x speed
        self._hand_label.setMovie(self._movie)

        self._movie.jumpToFrame(0)
        self._total_frames = self._movie.frameCount()
        self._frames_played = 0
        self._movie.stop()
        self._movie.frameChanged.connect(self._on_wave_frame_changed)

        # Load pointing transition GIF
        point_path = os.path.normpath(os.path.join(asset_dir, "pointing_hand.gif"))
        self._point_movie = QMovie(point_path)
        self._point_movie.setScaledSize(QSize(110, 110))
        self._point_movie.setSpeed(300)  # 3x speed for snappy transition
        self._point_total = self._point_movie.frameCount()
        self._point_movie.frameChanged.connect(self._on_point_frame_changed)

        # Cache last frame of pointing GIF for frozen state
        if self._point_total > 0:
            self._point_movie.jumpToFrame(self._point_total - 1)
            self._frozen_pixmap = self._point_movie.currentPixmap().copy()
            self._point_movie.stop()

        # Label for transition GIF playback (hidden by default)
        self._point_label = QLabel(self)
        self._point_label.setAlignment(Qt.AlignCenter)
        self._point_label.setAttribute(Qt.WA_TranslucentBackground)
        self._point_label.setFixedSize(120, 120)
        self._point_label.move(0, 0)
        self._point_label.setMovie(self._point_movie)
        self._point_label.hide()

    def _on_wave_frame_changed(self, frame_number: int):
        """Count total frames played, stop after 2 full cycles."""
        self._frames_played += 1
        if self._total_frames > 0 and self._frames_played >= self._total_frames * 2:
            self._movie.stop()

    def _on_point_frame_changed(self, frame_number: int):
        """When transition GIF reaches last frame, freeze it."""
        if frame_number >= self._point_total - 1:
            self._point_movie.stop()
            self._point_label.hide()
            self._point_frozen = True
            # Cache the last frame
            self._frozen_pixmap = self._point_movie.currentPixmap().copy()
            self.update()
            self.transition_done.emit()

    def _toggle_dot(self):
        self._dot_visible = not self._dot_visible
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Draw frozen pointing hand with rotation
        if self._point_frozen and self._frozen_pixmap:
            cx, cy = self.width() / 2, self.height() / 2
            painter.translate(cx, cy)
            painter.rotate(self._rotation)
            painter.translate(-cx, -cy)

            pw = self._frozen_pixmap.width()
            ph = self._frozen_pixmap.height()
            x = (self.width() - pw) / 2
            y = (self.height() - ph) / 2
            painter.drawPixmap(int(x), int(y), self._frozen_pixmap)

        # Listening indicator dot (warm amber)
        if self._show_red_dot and self._dot_visible:
            painter.resetTransform()
            dot_x, dot_y = 98, 10
            dot_r = 6
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(240, 222, 176, 50))   # soft amber glow
            painter.drawEllipse(dot_x - dot_r - 3, dot_y - dot_r - 3,
                                (dot_r + 3) * 2, (dot_r + 3) * 2)
            painter.setBrush(QColor(240, 222, 176, 210))  # soft amber solid
            painter.drawEllipse(dot_x - dot_r, dot_y - dot_r,
                                dot_r * 2, dot_r * 2)

        painter.end()

    # --- Public API ---

    def set_pointing(self, pointing: bool, angle: float = 0.0):
        """Enter/exit pointing mode.

        When entering: plays transition GIF (open hand -> pointing), then freezes.
        When exiting: returns to waving hand.
        """
        if pointing and not self._pointing:
            # Enter pointing mode - play transition GIF
            self._pointing = True
            self._point_frozen = False
            self._rotation = angle
            self._movie.stop()
            self._hand_label.hide()

            # Play transition GIF from start
            self._point_movie.jumpToFrame(0)
            self._point_label.show()
            self._point_movie.start()

        elif pointing and self._pointing:
            # Already pointing, just update rotation
            self._rotation = angle
            self.update()

        elif not pointing and self._pointing:
            # Exit pointing mode
            self._pointing = False
            self._point_frozen = False
            self._point_movie.stop()
            self._point_label.hide()
            self._hand_label.show()
            self._movie.jumpToFrame(0)
            self.update()

    def set_rotation(self, angle: float):
        """Update pointing direction (degrees, 0 = right, 90 = down)."""
        self._rotation = angle
        if self._point_frozen:
            self.update()

    def set_listening(self, listening: bool):
        self._listening = listening
        self._show_red_dot = listening
        if listening:
            self._dot_visible = True
            self._blink_timer.start()
            self._frames_played = 0
            self._movie.start()
        else:
            self._blink_timer.stop()
            self._show_red_dot = False
            self.update()
            if not self._hovered:
                self._movie.stop()
                self._movie.jumpToFrame(0)

    def set_status(self, text: str):
        pass

    def start_hover_wave(self):
        """Called by parent window on mouse enter."""
        if self._pointing:
            return
        self._hovered = True
        self._frames_played = 0
        self._movie.start()

    def stop_hover_wave(self):
        """Called by parent window on mouse leave."""
        self._hovered = False
        if not self._listening and not self._pointing:
            self._movie.stop()
            self._movie.jumpToFrame(0)
