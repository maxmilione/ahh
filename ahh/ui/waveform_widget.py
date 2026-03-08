"""Waveform visualization widget for mic input and TTS playback."""
import time
import math
import random
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QLinearGradient


class WaveformWidget(QWidget):
    """Shows audio waveform bars below the hand widget.

    Two modes:
    - listening: dark gray bars react to real-time mic amplitude
    - speaking: lighter gray bars animate a pulsing sine wave pattern
    """

    NUM_BARS = 11

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(120, 35)

        self._mode = None  # None, "listening", "speaking"
        self._amplitude_callback = None
        self._bar_heights = [0.0] * self.NUM_BARS
        self._smoothed_amp = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(33)  # ~30fps
        self._timer.timeout.connect(self._tick)

        self.hide()

    def set_amplitude_callback(self, callback):
        """Set a callable that returns current amplitude 0.0-1.0."""
        self._amplitude_callback = callback

    def start_listening(self):
        self._mode = "listening"
        self._bar_heights = [0.0] * self.NUM_BARS
        self._smoothed_amp = 0.0
        self._timer.start()
        self.show()

    def start_speaking(self):
        self._mode = "speaking"
        self._bar_heights = [0.0] * self.NUM_BARS
        self._timer.start()
        self.show()

    def stop(self):
        self._mode = None
        self._timer.stop()
        self._bar_heights = [0.0] * self.NUM_BARS
        self.update()
        self.hide()

    def _tick(self):
        if self._mode == "listening":
            amp = 0.0
            if self._amplitude_callback:
                try:
                    amp = self._amplitude_callback()
                except Exception:
                    amp = 0.0
            self._smoothed_amp += (amp - self._smoothed_amp) * 0.3
            center = self.NUM_BARS // 2
            for i in range(self.NUM_BARS):
                dist = abs(i - center) / center
                base = self._smoothed_amp * (1.0 - 0.5 * dist)
                jitter = random.uniform(-0.05, 0.05)
                target = max(0.05, min(1.0, base + jitter))
                self._bar_heights[i] += (target - self._bar_heights[i]) * 0.4

        elif self._mode == "speaking":
            t = time.time()
            for i in range(self.NUM_BARS):
                phase = (i / self.NUM_BARS) * math.pi * 2
                val = 0.3 + 0.3 * math.sin(t * 4 + phase)
                self._bar_heights[i] += (val - self._bar_heights[i]) * 0.3

        self.update()

    def paintEvent(self, event):
        if self._mode is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        bar_width = 3
        gap = (w - self.NUM_BARS * bar_width) / (self.NUM_BARS + 1)
        max_bar_height = h - 4
        min_bar_height = 4

        for i in range(self.NUM_BARS):
            bar_h = max(min_bar_height, self._bar_heights[i] * max_bar_height)
            x = gap + i * (bar_width + gap)
            y = (h - bar_h) / 2

            # Blue accent gradient per bar
            if self._mode == "listening":
                grad = QLinearGradient(x, y, x, y + bar_h)
                grad.setColorAt(0.0, QColor(123, 184, 212, 210))   # #7BB8D4
                grad.setColorAt(1.0, QColor(150, 200, 222, 140))
            else:
                grad = QLinearGradient(x, y, x, y + bar_h)
                grad.setColorAt(0.0, QColor(105, 166, 194, 190))   # #69A6C2
                grad.setColorAt(1.0, QColor(140, 195, 218, 130))

            painter.setPen(Qt.NoPen)
            painter.setBrush(grad)
            painter.drawRoundedRect(int(x), int(y), bar_width, int(bar_h), 999, 999)

        painter.end()
