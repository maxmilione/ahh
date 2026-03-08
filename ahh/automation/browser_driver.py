"""Playwright browser driver - controls Chromium for deterministic browser actions."""
import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright


class BrowserDriver:
    """Manages a Playwright Chromium browser for automation."""

    # Common cookie/consent button selectors and text patterns
    _CONSENT_SELECTORS = [
        "#onetrust-accept-btn-handler",
        "#accept-cookies",
        "#cookie-accept",
        ".cookie-accept",
        "[data-testid='cookie-accept']",
        "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
        "#didomi-notice-agree-button",
        ".cc-accept",
        ".cc-btn.cc-dismiss",
        "#consent-accept",
        "#gdpr-accept",
        "[aria-label='Accept cookies']",
        "[aria-label='Accept all cookies']",
        "[aria-label='Close']",
    ]

    _CONSENT_TEXT_PATTERNS = [
        "accept all",
        "accept cookies",
        "allow all",
        "allow cookies",
        "i agree",
        "got it",
        "agree and close",
        "ok, got it",
        "continue",
        "dismiss",
    ]

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._running = False

    @property
    def page(self) -> Optional[Page]:
        return self._page

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self):
        """Launch browser."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        self._context = await self._browser.new_context(
            viewport=None,  # Use full window size
            no_viewport=True,
        )
        self._page = await self._context.new_page()
        self._running = True

        # Auto-dismiss JavaScript dialogs (alert, confirm, prompt, beforeunload)
        self._page.on("dialog", self._handle_dialog)

    async def _handle_dialog(self, dialog):
        """Auto-dismiss JavaScript alert/confirm/prompt dialogs."""
        try:
            await dialog.accept()
        except Exception:
            pass

    async def dismiss_popups(self):
        """Try to dismiss cookie consent banners and overlay popups."""
        if not self._page:
            return

        # Try known CSS selectors first
        for selector in self._CONSENT_SELECTORS:
            try:
                el = self._page.locator(selector).first
                if await el.is_visible(timeout=200):
                    await el.click(timeout=1000)
                    await asyncio.sleep(0.3)
                    return
            except Exception:
                continue

        # Try finding buttons by text content
        for text in self._CONSENT_TEXT_PATTERNS:
            try:
                # Match button or link containing the text (case-insensitive)
                btn = self._page.get_by_role("button", name=text, exact=False).first
                if await btn.is_visible(timeout=200):
                    await btn.click(timeout=1000)
                    await asyncio.sleep(0.3)
                    return
            except Exception:
                continue

        # Try generic close buttons on visible overlays/modals
        try:
            close_btns = self._page.locator(
                "button:visible, [role='button']:visible, a:visible"
            ).filter(has_text="✕")
            if await close_btns.first.is_visible(timeout=200):
                await close_btns.first.click(timeout=1000)
                await asyncio.sleep(0.3)
                return
        except Exception:
            pass

    async def stop(self):
        """Close browser."""
        self._running = False
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._playwright = None
        self._page = None
        self._context = None

    async def navigate(self, url: str):
        """Navigate to a URL and auto-dismiss cookie/consent popups."""
        if self._page:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
            # Wait briefly for popups to appear, then dismiss
            await asyncio.sleep(1.5)
            await self.dismiss_popups()

    async def click(self, selector: str) -> dict:
        """Click an element. Returns bounding box info for cursor mirroring.
        If the click fails, tries to dismiss popups and retries once."""
        if not self._page:
            return {}

        for attempt in range(2):
            try:
                await self._page.wait_for_selector(selector, timeout=5000)
                element = self._page.locator(selector).first
                box = await element.bounding_box()
                if box:
                    await element.click(timeout=3000)
                    return {
                        "x": box["x"] + box["width"] / 2,
                        "y": box["y"] + box["height"] / 2,
                        "width": box["width"],
                        "height": box["height"],
                        "top": box["y"],
                        "left": box["x"],
                    }
            except Exception as e:
                print(f"[BrowserDriver] Click attempt {attempt+1} failed for '{selector}': {e}")
                if attempt == 0:
                    # Try dismissing popups and retry
                    await self.dismiss_popups()
                    await asyncio.sleep(0.5)

        return {}

    async def type_text(self, selector: str, text: str) -> dict:
        """Type text into an element. Returns bounding box info.
        If it fails, tries to dismiss popups and retries once."""
        if not self._page:
            return {}

        for attempt in range(2):
            try:
                await self._page.wait_for_selector(selector, timeout=5000)
                element = self._page.locator(selector).first
                box = await element.bounding_box()
                await element.click(timeout=3000)
                await element.fill("")
                await element.type(text, delay=50)  # Visible typing
                if box:
                    return {
                        "x": box["x"] + box["width"] / 2,
                        "y": box["y"] + box["height"] / 2,
                        "width": box["width"],
                        "height": box["height"],
                        "top": box["y"],
                        "left": box["x"],
                    }
            except Exception as e:
                print(f"[BrowserDriver] Type attempt {attempt+1} failed for '{selector}': {e}")
                if attempt == 0:
                    await self.dismiss_popups()
                    await asyncio.sleep(0.5)

        return {}

    async def press_key(self, key: str):
        """Press a keyboard key."""
        if self._page:
            await self._page.keyboard.press(key)

    async def scroll(self, direction: str = "down", amount: int = 300):
        """Scroll the page."""
        if self._page:
            delta = amount if direction == "down" else -amount
            await self._page.mouse.wheel(0, delta)

    async def wait(self, seconds: float):
        """Wait for a specified time."""
        await asyncio.sleep(seconds)

    async def read_text(self, selector: str) -> str:
        """Read text content from an element."""
        if not self._page:
            return ""
        try:
            await self._page.wait_for_selector(selector, timeout=5000)
            element = self._page.locator(selector).first
            return await element.text_content() or ""
        except Exception as e:
            print(f"[BrowserDriver] Read failed for '{selector}': {e}")
            return ""

    async def get_element_screen_box(self, selector: str) -> dict:
        """Get element bounding box in page coordinates."""
        if not self._page:
            return {}

        try:
            element = self._page.locator(selector).first
            box = await element.bounding_box()
            if box:
                return box
        except Exception:
            pass
        return {}

    async def get_window_position(self) -> tuple[int, int]:
        """Get browser window position on screen."""
        if not self._page:
            return (0, 0)
        try:
            result = await self._page.evaluate("""
                () => ({x: window.screenX, y: window.screenY})
            """)
            return (result["x"], result["y"])
        except Exception:
            return (0, 0)

    async def get_viewport_offset(self) -> tuple[int, int]:
        """Get the offset from window position to viewport (accounts for chrome UI)."""
        if not self._page:
            return (0, 0)
        try:
            result = await self._page.evaluate("""
                () => ({
                    x: window.outerWidth - window.innerWidth,
                    y: window.outerHeight - window.innerHeight
                })
            """)
            # Chrome UI is typically at the top
            return (0, result["y"])
        except Exception:
            return (0, 80)  # reasonable default for Chrome

    async def is_password_field(self, selector: str) -> bool:
        """Check if a field is a password input."""
        if not self._page:
            return False
        try:
            result = await self._page.evaluate(f"""
                (selector) => {{
                    const el = document.querySelector(selector);
                    return el && el.type === 'password';
                }}
            """, selector)
            return bool(result)
        except Exception:
            return False

    async def is_submit_button(self, selector: str) -> bool:
        """Check if an element is a submit button."""
        if not self._page:
            return False
        try:
            result = await self._page.evaluate("""
                (selector) => {
                    const el = document.querySelector(selector);
                    if (!el) return false;
                    const text = (el.textContent || '').toLowerCase();
                    const type = (el.type || '').toLowerCase();
                    return type === 'submit' ||
                           text.includes('submit') ||
                           text.includes('send') ||
                           text.includes('confirm') ||
                           text.includes('pay') ||
                           text.includes('purchase');
                }
            """, selector)
            return bool(result)
        except Exception:
            return False
