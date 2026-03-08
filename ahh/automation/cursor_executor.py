"""OS cursor executor - mirrors Playwright actions with real OS cursor."""
import asyncio
import time
import ctypes
import ctypes.wintypes
from typing import Optional, Callable

import pyautogui

# Disable pyautogui fail-safe for controlled automation
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


class CursorExecutor:
    """Mirrors browser actions with real OS cursor movement."""

    def __init__(self):
        self._stopped = False
        self.on_click: Optional[Callable] = None  # callback(screen_x, screen_y)

    def stop(self):
        self._stopped = True

    def reset(self):
        self._stopped = False

    async def move_to(self, screen_x: int, screen_y: int, duration: float = 0.5):
        """Smoothly move OS cursor to screen coordinates."""
        if self._stopped:
            return

        # Get current position
        start_x, start_y = pyautogui.position()

        # Smooth movement using pyautogui
        steps = max(10, int(duration * 60))
        for i in range(steps + 1):
            if self._stopped:
                return
            t = i / steps
            # Ease-in-out cubic
            t = t * t * (3 - 2 * t)
            x = int(start_x + (screen_x - start_x) * t)
            y = int(start_y + (screen_y - start_y) * t)
            pyautogui.moveTo(x, y, _pause=False)
            await asyncio.sleep(duration / steps)

    async def click_at(self, screen_x: int, screen_y: int):
        """Move to position and click."""
        if self._stopped:
            return

        await self.move_to(screen_x, screen_y)
        if self._stopped:
            return

        pyautogui.click(screen_x, screen_y)

        if self.on_click:
            self.on_click(screen_x, screen_y)

    async def type_text(self, text: str, interval: float = 0.05):
        """Type text character by character with visible delay."""
        if self._stopped:
            return

        for char in text:
            if self._stopped:
                return
            pyautogui.typewrite(char if char.isascii() else '', interval=0)
            if not char.isascii():
                # For non-ASCII, use clipboard
                import subprocess
                subprocess.run(['clip'], input=char.encode('utf-16le'),
                             check=True, shell=True)
                pyautogui.hotkey('ctrl', 'v')
            await asyncio.sleep(interval)

    async def press_key(self, key: str):
        """Press a keyboard key."""
        if self._stopped:
            return
        pyautogui.press(key)

    async def hotkey(self, *keys):
        """Press a keyboard shortcut."""
        if self._stopped:
            return
        pyautogui.hotkey(*keys)

    def page_to_screen(self, page_x: float, page_y: float,
                       win_x: int, win_y: int,
                       viewport_offset_x: int, viewport_offset_y: int) -> tuple[int, int]:
        """Convert page coordinates to screen coordinates.

        Args:
            page_x, page_y: Element position in page coordinates.
            win_x, win_y: Browser window position on screen.
            viewport_offset_x, viewport_offset_y: Offset from window to viewport.

        Returns:
            (screen_x, screen_y)
        """
        screen_x = int(win_x + viewport_offset_x + page_x)
        screen_y = int(win_y + viewport_offset_y + page_y)
        return screen_x, screen_y
