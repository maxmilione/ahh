# Ahh! (A Helping Hand)

A Windows desktop teaching agent that shows a helping hand character on screen. Users click the hand to give voice commands, and the app uses real browser automation with teaching overlays to complete tasks while explaining every step.

## Setup (Windows 10/11)

### 0. Install Python 3.11+

Download from https://www.python.org/downloads/ and install.
**Check "Add Python to PATH"** during installation.

### 1. Create Virtual Environment

```cmd
cd "C:\Users\maxgi\OneDrive\เอกสาร\AHH!"
python -m venv venv
venv\Scripts\activate
```

### 2. Install Dependencies

```cmd
pip install -r requirements.txt
playwright install chromium
```

### 3. Set Environment Variables

```cmd
set ANTHROPIC_API_KEY=your_anthropic_api_key_here
set ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

Or create a `.env` file (optional, you'll need to source it manually):
```
ANTHROPIC_API_KEY=sk-ant-...
ELEVENLABS_API_KEY=xi-...
```

### 4. Run

```cmd
python main.py
```

## How It Works

1. **Helping hand** appears on screen (bottom-right). Drag it anywhere.
2. **Click the hand** to start voice recording. Click again to stop and process.
3. If voice fails, a **text input box** appears as fallback.
4. The app calls Claude to **plan** the task as browser steps.
5. If clarification is needed, **bubble options** appear near the hand.
6. A Playwright browser opens and the app **mirrors actions with the real OS cursor**.
7. **Teaching overlays** show: cursor halo, trail, click pulses, element highlights, arrows, and captions.
8. **Step stack** panel shows progress through the plan.
9. Press **ESC** or click **STOP** to halt at any time.

## Project Structure

```
/ahh
  /ui            - PySide6 overlay components
    hand_widget.py     - Draggable helping hand
    overlay_window.py  - Main transparent overlay
    step_stack.py      - Plan steps panel
    bubbles.py         - Clarification bubbles
    caption_strip.py   - Action captions
    confirm_modal.py   - Safety confirmation
    cursor_overlay.py  - Halo, trail, click pulse, highlight, arrow
    text_input.py      - Text fallback input
  /audio         - Audio capture and STT
    recorder.py        - Microphone recording
    stt_client.py      - ElevenLabs Scribe API
  /agent         - LLM planning
    planner.py         - Claude API planner
    schema.py          - JSON schema + validation
  /automation    - Browser + cursor control
    browser_driver.py  - Playwright Chromium driver
    cursor_executor.py - OS cursor mirroring
  /assets
    hand.svg           - Hand character asset
main.py          - Application entrypoint
requirements.txt - Python dependencies
```

## Dependencies

- Python 3.11+
- PySide6 (Qt6) - Overlay UI
- Playwright - Browser automation
- PyAudio - Microphone capture
- pyautogui - OS cursor control
- anthropic - Claude API
- requests - HTTP client for ElevenLabs
- pydantic - JSON schema validation
- numpy - Audio amplitude
