"""
Ahh! (A Helping Hand) - Main Entrypoint
========================================
A Windows desktop teaching agent that shows a helping hand character,
takes voice/text input, plans browser tasks, and teaches users by showing
real cursor movements with visual overlays.
"""
import sys
import os
import asyncio
import threading
import logging
import re
from datetime import datetime
from functools import partial
from pathlib import Path
from dotenv import load_dotenv

# Set up file logging for debugging (INFO level, only for ahh logger)
log = logging.getLogger("ahh")
log.setLevel(logging.DEBUG)
_fh = logging.FileHandler(os.path.join(os.path.dirname(__file__), "ahh_debug.log"))
_fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
log.addHandler(_fh)

# Load .env file from project root
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot, QPoint, QRectF
from PySide6.QtGui import QFontDatabase

from ahh.ui.overlay_window import OverlayWindow
from ahh.audio.recorder import AudioRecorder
from ahh.audio.stt_client import STTClient
from ahh.audio.tts_client import TTSClient
from ahh.agent.planner import Planner
from ahh.agent.schema import PlanResponse
from ahh.automation.browser_driver import BrowserDriver
from ahh.automation.cursor_executor import CursorExecutor


class AsyncBridge(QObject):
    """Bridge between asyncio event loop and Qt signals."""
    plan_ready = Signal(object)       # PlanResponse
    action_started = Signal(str, str) # action_type, caption
    action_done = Signal(int)         # step_id
    step_changed = Signal(int)        # step_id
    execution_done = Signal()
    execution_error = Signal(str)
    transcript_ready = Signal(str)
    silence_detected = Signal()     # VAD auto-stop
    confirm_needed = Signal(str)      # message
    browser_coords = Signal(float, float, float, float, float, float)  # screen_x, screen_y, w, h, top, left
    click_pulse = Signal(float, float)  # screen_x, screen_y for click animation
    tts_started = Signal(str)  # spoken text
    tts_stopped = Signal()


class AhhApp:
    """Main application controller."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Load custom fonts
        font_dir = os.path.join(os.path.dirname(__file__), "ahh", "assets", "fonts")
        dm_sans = os.path.join(font_dir, "DMSans-Variable.ttf")
        if os.path.exists(dm_sans):
            QFontDatabase.addApplicationFont(dm_sans)

        # Core components
        self.overlay = OverlayWindow()
        self.recorder = AudioRecorder()
        self.stt = STTClient()
        self.tts = TTSClient()
        self.planner = Planner()
        self.browser = BrowserDriver()
        self.cursor = CursorExecutor()

        # Async bridge
        self.bridge = AsyncBridge()

        # State
        self._recording = False
        self._executing = False
        self._current_request = ""
        self._current_plan: PlanResponse | None = None
        self._stopped = False
        self._confirm_future: asyncio.Future | None = None
        self._confirm_result = False

        # Async event loop in background thread
        self._loop = asyncio.new_event_loop()
        self._async_thread = threading.Thread(target=self._run_async_loop, daemon=True)

        # TTS play callbacks -> bridge signals (called from background thread)
        self.tts.on_play_start = lambda text: self.bridge.tts_started.emit(text)
        self.tts.on_play_stop = lambda: self.bridge.tts_stopped.emit()

        # VAD auto-stop callback (called from recording thread)
        self.recorder.on_silence_detected = lambda: self.bridge.silence_detected.emit()

        # Waveform amplitude callback
        self.overlay.waveform.set_amplitude_callback(self.recorder.get_amplitude)

        self._connect_signals()

    def _connect_signals(self):
        # Hand click -> toggle recording
        self.overlay.hand_clicked.connect(self._on_hand_click)

        # Hand double-click -> text input
        self.overlay.hand_double_clicked.connect(self._on_hand_double_click)

        # Stop button / ESC
        self.overlay.stop_requested.connect(self._on_stop)
        self.overlay.esc_shortcut.activated.connect(self._on_stop)

        # Text fallback
        self.overlay.text_input.text_submitted.connect(self._on_text_submitted)
        self.overlay.text_input.closed.connect(lambda: self.overlay.set_interactive(False))

        # Bubble selection
        self.overlay.bubbles.option_selected.connect(self._on_bubble_selected)

        # Async bridge signals
        self.bridge.plan_ready.connect(self._on_plan_ready)
        self.bridge.action_started.connect(self._on_action_started)
        self.bridge.step_changed.connect(self._on_step_changed)
        self.bridge.action_done.connect(self._on_action_done)
        self.bridge.execution_done.connect(self._on_execution_done)
        self.bridge.execution_error.connect(self._on_execution_error)
        self.bridge.transcript_ready.connect(self._on_transcript_ready)
        self.bridge.confirm_needed.connect(self._on_confirm_needed)
        self.bridge.browser_coords.connect(self._on_browser_coords)
        self.bridge.click_pulse.connect(self._on_click_pulse)

        # Confirm modal
        self.overlay.confirm_modal.confirmed.connect(self._on_confirm_yes)
        self.overlay.confirm_modal.cancelled.connect(self._on_confirm_no)

        # TTS waveform
        self.bridge.tts_started.connect(self._on_tts_started)
        self.bridge.tts_stopped.connect(self._on_tts_stopped)

        # VAD auto-stop
        self.bridge.silence_detected.connect(self._on_silence_detected)

    def _run_async_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self):
        """Start the application."""
        self._async_thread.start()
        self.overlay.show()
        self.overlay.caption.show_caption("Click or double-click the hand!", icon="navigate", duration_ms=5000)
        sys.exit(self.app.exec())

    # --- Recording ---

    def _on_hand_click(self):
        log.info("Hand clicked")
        if self._executing:
            return  # Don't interrupt execution

        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _on_hand_double_click(self):
        """Double-click opens text input instead of voice."""
        log.info("Hand double-clicked")
        if self._executing:
            return
        if self._recording:
            self._stop_recording_silent()
        self.overlay.show_text_input()

    def _start_recording(self):
        self._recording = True
        self.overlay.hand.set_listening(True)
        self.overlay.waveform.start_listening()
        try:
            self.recorder.start()
        except RuntimeError:
            # Audio not available, show text input
            self._recording = False
            self.overlay.hand.set_listening(False)
            self.overlay.waveform.stop()
            self.overlay.caption.show_caption("No mic found. Type below.", icon="wait", duration_ms=3000)
            self.overlay.show_text_input()

    def _stop_recording(self):
        self._recording = False
        self.overlay.hand.set_listening(False)
        self.overlay.waveform.stop()
        self.overlay.caption.show_caption("Processing...", icon="wait", duration_ms=10000)

        wav_data = self.recorder.stop()
        if wav_data:
            # Transcribe in background
            asyncio.run_coroutine_threadsafe(
                self._transcribe_and_plan(wav_data), self._loop
            )
        else:
            self.overlay.caption.show_caption("No audio captured. Type instead.", icon="wait", duration_ms=3000)
            self.overlay.show_text_input()

    def _stop_recording_silent(self):
        """Stop recording without processing (for switching to text input)."""
        self._recording = False
        self.overlay.hand.set_listening(False)
        self.overlay.waveform.stop()
        self.recorder.stop()  # discard audio

    async def _transcribe_and_plan(self, wav_data: bytes):
        text = self.stt.transcribe(wav_data)
        if text:
            self.bridge.transcript_ready.emit(text)
        else:
            self.bridge.transcript_ready.emit("")

    @Slot(str)
    def _on_transcript_ready(self, text: str):
        if text:
            self.overlay.caption.show_caption(f'Heard: "{text[:50]}"', icon="search", duration_ms=3000)
            self._process_request(text)
        else:
            self.overlay.caption.show_caption("Couldn't hear. Type instead.", icon="wait", duration_ms=3000)
            self.overlay.show_text_input()

    @Slot(str)
    def _on_text_submitted(self, text: str):
        log.info(f"Text submitted: {text}")
        self.overlay.set_interactive(False)
        self._process_request(text)

    # --- Planning ---

    def _process_request(self, request: str):
        self._current_request = request
        self.overlay.caption.show_caption("Planning...", icon="wait", duration_ms=15000)
        log.info(f"Processing request: {request}")

        asyncio.run_coroutine_threadsafe(
            self._do_plan(request), self._loop
        )

    async def _do_plan(self, request: str, context: str = ""):
        try:
            log.info("Calling planner...")
            plan = self.planner.plan(request, context)
            log.info(f"Plan ready: clarify={bool(plan.clarify)}, steps={len(plan.steps) if plan.steps else 0}")
            self.bridge.plan_ready.emit(plan)
        except Exception as e:
            log.error(f"Planning error: {e}")
            self.bridge.execution_error.emit(f"Planning failed: {e}")

    @Slot(object)
    def _on_plan_ready(self, plan: PlanResponse):
        if plan.clarify:
            # Show clarification bubbles
            q = plan.clarify[0]
            self.overlay.set_interactive(True)
            self.overlay.bubbles.show_question(q.question, q.choices)
            self._pending_clarify_question = q.question
            # Speak the question
            self.tts.speak_async(q.question)
        elif plan.steps and plan.actions:
            # Show plan and execute
            self.overlay.step_stack.set_steps(
                [{"id": s.id, "title": s.title, "teach": s.teach} for s in plan.steps]
            )
            self.overlay.show_step_stack()
            self.overlay.show_stop_button()

            # Execute plan
            self._executing = True
            self._stopped = False
            self._current_plan = plan
            self.cursor.reset()
            asyncio.run_coroutine_threadsafe(
                self._execute_plan(plan), self._loop
            )
        else:
            self.overlay.caption.show_caption("Couldn't make a plan. Try again.", icon="wait", duration_ms=5000)

    @Slot(int, str)
    def _on_bubble_selected(self, index: int, text: str):
        self.overlay.set_interactive(False)
        question = getattr(self, '_pending_clarify_question', '')

        asyncio.run_coroutine_threadsafe(
            self._do_replan(question, text), self._loop
        )

    async def _do_replan(self, question: str, answer: str):
        try:
            plan = self.planner.replan_with_answer(self._current_request, question, answer)
            self.bridge.plan_ready.emit(plan)
        except Exception as e:
            self.bridge.execution_error.emit(f"Re-planning failed: {e}")

    # --- Execution ---

    async def _execute_plan(self, plan: PlanResponse):
        try:
            # Start browser
            if not self.browser.is_running:
                await self.browser.start()
                await asyncio.sleep(1)

            # Start cursor overlay tracking
            self.bridge.step_changed.emit(0)  # Signal to start cursor overlay

            current_step_id = -1

            for action in plan.actions:
                if self._stopped:
                    break

                # Update step heading
                if action.step_id != current_step_id:
                    current_step_id = action.step_id
                    step = next((s for s in plan.steps if s.id == current_step_id), None)
                    self.bridge.step_changed.emit(current_step_id)
                    if step:
                        self.bridge.action_started.emit(action.type, step.teach)
                        # Speak the teaching text and wait for it to finish
                        tts_thread = self.tts.speak_async(step.teach)
                        await asyncio.get_event_loop().run_in_executor(
                            None, tts_thread.join
                        )
                        if self._stopped:
                            break

                # Point the hand at the target BEFORE narrating/executing
                await self._point_hand_to_action(action)

                # Narrate this specific action while hand is already pointing
                narration = getattr(action, 'narrate', '') or ''
                if narration:
                    tts_thread = self.tts.speak_async(narration)
                    await asyncio.get_event_loop().run_in_executor(
                        None, tts_thread.join
                    )
                    if self._stopped:
                        break

                await self._execute_action(action)
                await asyncio.sleep(0.5)

            self.bridge.execution_done.emit()

        except Exception as e:
            self.bridge.execution_error.emit(str(e))

    async def _point_hand_to_action(self, action):
        """Move the pointing hand to where this action's target is, BEFORE executing."""
        if not self.browser.is_running or not self.browser.page:
            return

        action_type = action.type
        params = action.params

        try:
            win_x, win_y = await self.browser.get_window_position()
            vp_x, vp_y = await self.browser.get_viewport_offset()
        except Exception:
            return

        if action_type == "navigate":
            # Point at the URL bar area (browser chrome, not page)
            try:
                inner_w = await self.browser.page.evaluate("window.innerWidth")
            except Exception:
                inner_w = 1200
            url_cx = win_x + inner_w / 2
            url_cy = win_y + 50  # URL bar ~50px from top of window
            self.bridge.browser_coords.emit(
                url_cx, url_cy, inner_w * 0.5, 30,
                url_cy - 15, url_cx - inner_w * 0.25
            )

        elif action_type in ("click", "type", "read"):
            selector = params.get("selector", "")
            if not selector:
                return
            try:
                # Try to dismiss popups first so element is visible
                await self.browser.dismiss_popups()
                box = await self.browser.get_element_screen_box(selector)
                if box:
                    cx = box["x"] + box["width"] / 2
                    cy = box["y"] + box["height"] / 2
                    screen_x, screen_y = self.cursor.page_to_screen(
                        cx, cy, win_x, win_y, vp_x, vp_y
                    )
                    self.bridge.browser_coords.emit(
                        float(screen_x), float(screen_y),
                        float(box["width"]), float(box["height"]),
                        float(box["y"] + win_y + vp_y),
                        float(box["x"] + win_x + vp_x)
                    )
            except Exception:
                pass

        elif action_type == "scroll":
            # Point at center of viewport
            try:
                inner_w = await self.browser.page.evaluate("window.innerWidth")
                inner_h = await self.browser.page.evaluate("window.innerHeight")
            except Exception:
                inner_w, inner_h = 1200, 800
            center_x = win_x + vp_x + inner_w / 2
            center_y = win_y + vp_y + inner_h / 2
            self.bridge.browser_coords.emit(
                center_x, center_y, 100.0, 100.0,
                center_y - 50, center_x - 50
            )

    async def _execute_action(self, action):
        """Execute a single action with cursor mirroring."""
        params = action.params
        action_type = action.type

        if action_type == "navigate":
            url = params.get("url", "")
            self.bridge.action_started.emit("navigate", f"Opening {url}")
            await self.browser.navigate(url)
            await asyncio.sleep(1)

        elif action_type == "click":
            selector = params.get("selector", "")
            desc = params.get("description", "clicking element")

            # Safety check
            is_submit = await self.browser.is_submit_button(selector)
            if is_submit:
                self.bridge.confirm_needed.emit(
                    f"About to click a submit/send button: {desc}\nProceed?"
                )
                confirmed = await self._wait_for_confirm()
                if not confirmed:
                    return

            self.bridge.action_started.emit("click", desc)

            # Click the element (hand is already pointing at it)
            box = await self.browser.click(selector)
            if box:
                win_x, win_y = await self.browser.get_window_position()
                vp_offset_x, vp_offset_y = await self.browser.get_viewport_offset()
                screen_x, screen_y = self.cursor.page_to_screen(
                    box["x"], box["y"], win_x, win_y, vp_offset_x, vp_offset_y
                )
                # Update hand position and show click pulse
                self.bridge.browser_coords.emit(
                    screen_x, screen_y,
                    box["width"], box["height"],
                    box["top"] + win_y + vp_offset_y,
                    box["left"] + win_x + vp_offset_x
                )
                self.bridge.click_pulse.emit(float(screen_x), float(screen_y))

            await asyncio.sleep(0.5)

        elif action_type == "type":
            selector = params.get("selector", "")
            text = params.get("text", "")

            # Safety check for password fields
            is_password = await self.browser.is_password_field(selector)
            if is_password:
                self.bridge.confirm_needed.emit(
                    f"About to type into a password field.\nProceed?"
                )
                confirmed = await self._wait_for_confirm()
                if not confirmed:
                    return

            self.bridge.action_started.emit("type", f'Typing "{text[:30]}"')

            box = await self.browser.type_text(selector, text)
            if box:
                win_x, win_y = await self.browser.get_window_position()
                vp_offset_x, vp_offset_y = await self.browser.get_viewport_offset()
                screen_x, screen_y = self.cursor.page_to_screen(
                    box["x"], box["y"], win_x, win_y, vp_offset_x, vp_offset_y
                )
                self.bridge.browser_coords.emit(
                    screen_x, screen_y,
                    box["width"], box["height"],
                    box["top"] + win_y + vp_offset_y,
                    box["left"] + win_x + vp_offset_x
                )

            await asyncio.sleep(0.3)

        elif action_type == "scroll":
            direction = params.get("direction", "down")
            amount = params.get("amount", 300)
            self.bridge.action_started.emit("scroll", f"Scrolling {direction}")
            await self.browser.scroll(direction, amount)
            await asyncio.sleep(0.5)

        elif action_type == "wait":
            seconds = params.get("seconds", 1)
            self.bridge.action_started.emit("wait", f"Waiting {seconds}s")
            await self.browser.wait(seconds)

        elif action_type == "read":
            selector = params.get("selector", "")
            purpose = params.get("purpose", "reading content")
            self.bridge.action_started.emit("search", purpose)
            text = await self.browser.read_text(selector)
            if text:
                # Show first 100 chars in caption
                preview = text[:100].strip()
                self.bridge.action_started.emit("search", f"Found: {preview}")
            await asyncio.sleep(1)

    async def _wait_for_confirm(self) -> bool:
        """Wait for user to confirm or cancel in the modal."""
        self._confirm_future = self._loop.create_future()
        try:
            result = await asyncio.wait_for(self._confirm_future, timeout=30)
            return result
        except asyncio.TimeoutError:
            return False
        finally:
            self._confirm_future = None

    # --- UI Callbacks ---

    @Slot(str, str)
    def _on_action_started(self, action_type: str, caption: str):
        self.overlay.caption.show_caption(caption, icon=action_type)

    @Slot(int)
    def _on_step_changed(self, step_id: int):
        if step_id == 0:
            self.overlay.cursor_overlay.start_tracking()
        else:
            self.overlay.step_stack.set_step_active(step_id)

    @Slot(int)
    def _on_action_done(self, step_id: int):
        self.overlay.step_stack.set_step_completed(step_id)

    @Slot()
    def _on_execution_done(self):
        self._executing = False
        self.overlay.cursor_overlay.stop_tracking()
        self.overlay.cursor_overlay.clear_highlight()
        self.overlay.return_hand_home()
        self.overlay.hide_stop_button()

        # Save lesson summary before showing "All done!"
        saved_path = self._save_lesson_summary()

        self.overlay.caption.show_caption("All done!", icon="navigate", duration_ms=3000)
        self.tts.speak_async("All done!")

        if saved_path:
            # Show "Lesson saved" caption after a short delay
            QTimer.singleShot(3500, lambda: self.overlay.caption.show_caption(
                "Lesson saved to Desktop!", icon="navigate", duration_ms=3000
            ))

    def _save_lesson_summary(self) -> str | None:
        """Save a summary of the completed lesson to the Desktop."""
        plan = self._current_plan
        if not plan or not plan.steps:
            return None

        try:
            # Create lessons folder on Desktop
            desktop = Path.home() / "Desktop" / "AHH Lessons"
            desktop.mkdir(parents=True, exist_ok=True)

            # Generate filename from request + timestamp
            now = datetime.now()
            safe_name = re.sub(r'[<>:"/\\|?*]', '', self._current_request[:60]).strip()
            if not safe_name:
                safe_name = "lesson"
            filename = f"{safe_name} - {now.strftime('%Y-%m-%d %H.%M')}.txt"
            filepath = desktop / filename

            # Build summary content
            lines = []
            lines.append(f"Lesson: {self._current_request}")
            lines.append(f"Date: {now.strftime('%B %d, %Y at %I:%M %p')}")
            lines.append("─" * 40)
            lines.append("")

            # Group actions by step
            actions_by_step: dict[int, list] = {}
            if plan.actions:
                for action in plan.actions:
                    actions_by_step.setdefault(action.step_id, []).append(action)

            for step in plan.steps:
                lines.append(f"Step {step.id}: {step.title}")
                lines.append(f"  Explanation: {step.teach}")
                lines.append("")

                # Add action narrations for this step
                step_actions = actions_by_step.get(step.id, [])
                for action in step_actions:
                    narration = getattr(action, 'narrate', '') or ''
                    if narration:
                        lines.append(f"  → {narration}")
                    else:
                        # Fall back to a description of the action
                        desc = self._action_description(action)
                        if desc:
                            lines.append(f"  → {desc}")

                lines.append("")

            lines.append("─" * 40)
            lines.append("Saved by AHH! (A Helping Hand)")

            filepath.write_text("\n".join(lines), encoding="utf-8")
            log.info(f"Lesson summary saved: {filepath}")
            return str(filepath)

        except Exception as e:
            log.error(f"Failed to save lesson summary: {e}")
            return None

    def _action_description(self, action) -> str:
        """Generate a short human-readable description of an action."""
        params = action.params
        if action.type == "navigate":
            return f"Navigated to {params.get('url', '')}"
        elif action.type == "click":
            return f"Clicked {params.get('description', 'an element')}"
        elif action.type == "type":
            return f'Typed "{params.get("text", "")}"'
        elif action.type == "scroll":
            return f"Scrolled {params.get('direction', 'down')}"
        elif action.type == "read":
            return f"Read {params.get('purpose', 'content')}"
        elif action.type == "wait":
            return f"Waited {params.get('seconds', 1)} seconds"
        return ""

    @Slot(str)
    def _on_execution_error(self, error: str):
        self._executing = False
        self.overlay.cursor_overlay.stop_tracking()
        self.overlay.hide_stop_button()
        self.overlay.caption.show_caption(f"Error: {error}", icon="wait", duration_ms=8000)
        log.error(f"Execution error: {error}")

    @Slot(str)
    def _on_confirm_needed(self, message: str):
        self.overlay.set_interactive(True)
        self.overlay.confirm_modal.show_confirm(message)

    def _on_confirm_yes(self):
        self.overlay.set_interactive(False)
        self._confirm_result = True
        if self._confirm_future and not self._confirm_future.done():
            self._loop.call_soon_threadsafe(self._confirm_future.set_result, True)

    def _on_confirm_no(self):
        self.overlay.set_interactive(False)
        self._confirm_result = False
        if self._confirm_future and not self._confirm_future.done():
            self._loop.call_soon_threadsafe(self._confirm_future.set_result, False)

    @Slot(float, float, float, float, float, float)
    def _on_browser_coords(self, sx, sy, w, h, top, left):
        # Show highlight rectangle around the target element
        self.overlay.cursor_overlay.set_highlight(
            QRectF(left, top, w, h),
            label=""
        )
        # Move pointing hand to target
        self.overlay.point_hand_at(QPoint(int(sx), int(sy)))

    @Slot(float, float)
    def _on_click_pulse(self, sx, sy):
        self.overlay.cursor_overlay.add_click_pulse(QPoint(int(sx), int(sy)))

    @Slot()
    def _on_silence_detected(self):
        """VAD detected silence after speech — auto-stop recording."""
        if self._recording:
            log.info("VAD: silence detected, auto-stopping recording")
            self._stop_recording()

    @Slot(str)
    def _on_tts_started(self, text: str):
        self.overlay.waveform.start_speaking()
        self.overlay.show_speech_bubble(text)

    @Slot()
    def _on_tts_stopped(self):
        self.overlay.waveform.stop()
        self.overlay.hide_speech_bubble()

    def _on_stop(self):
        """Stop all automation."""
        self._stopped = True
        self._executing = False
        self._recording = False
        self.overlay.hand.set_listening(False)
        self.overlay.waveform.stop()
        self.overlay.hide_speech_bubble()
        self.cursor.stop()
        self.tts.stop()

        # Stop browser
        asyncio.run_coroutine_threadsafe(
            self._cleanup_stop(), self._loop
        )

        self.overlay.cursor_overlay.stop_tracking()
        self.overlay.cursor_overlay.clear_highlight()
        self.overlay.return_hand_home()
        self.overlay.hide_stop_button()
        self.overlay.hide_step_stack()
        self.overlay.caption.hide_caption()
        self.overlay.bubbles.hide_bubbles()
        self.overlay.confirm_modal.hide()
        self.overlay.set_interactive(False)
        self.overlay.caption.show_caption("Stopped.", icon="wait", duration_ms=3000)

        # Cancel pending confirm
        if self._confirm_future and not self._confirm_future.done():
            self._loop.call_soon_threadsafe(self._confirm_future.set_result, False)

    async def _cleanup_stop(self):
        try:
            if self.browser.is_running:
                await self.browser.stop()
        except Exception:
            pass


def main():
    # Check for required env vars
    missing = []
    if not os.environ.get("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY (for planning)")
    if not os.environ.get("ELEVENLABS_API_KEY"):
        missing.append("ELEVENLABS_API_KEY (for speech-to-text and text-to-speech)")
    if missing:
        print("WARNING: Missing API keys in .env:")
        for m in missing:
            print(f"  - {m}")

    app = AhhApp()
    app.run()


if __name__ == "__main__":
    main()
