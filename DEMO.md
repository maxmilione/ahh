# Demo Script

## Pre-Flight Checklist

1. Environment variables set (`ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`)
2. `playwright install chromium` completed
3. App launched: `python main.py`
4. Cherry blossom plant visible on screen

---

## Flow A: DMV Change of Address (Primary Demo)

### What to Say (or Type)
> "Help me find the DMV change of address form"

### What Should Happen
1. Plant shows "Listening..." with pink pulse while recording
2. After clicking plant again (stop recording), it shows the transcribed text
3. Claude plans ~4-5 steps
4. Step stack appears on the right side showing the plan
5. Browser opens (Chromium)
6. Cursor halo appears, trail follows the cursor
7. Browser navigates to Google
8. OS cursor moves to the search box with visible trail
9. Types "DMV change of address form" with visible keystrokes
10. Clicks search or presses Enter
11. Clicks an official-looking result (e.g., dmv.ca.gov)
12. Caption bar explains each step: "Searching Google for the DMV form because that's the fastest way to find it"
13. Steps get checked off as completed
14. "All done!" appears when finished

### Backup Plan
If voice doesn't work:
- Click the plant, it will show text input bar
- Type: "Help me find the DMV change of address form"
- Same flow continues

---

## Flow B: Weather Check (Backup Demo)

### What to Say (or Type)
> "What's the weather today?"

### What Should Happen
1. Same voice/text capture flow
2. Claude plans ~3 steps
3. Browser opens, navigates to Google
4. Searches "weather today"
5. Reads the weather widget or clicks a result
6. Shows summary in caption

---

## Flow C: Quick Test (Minimal)

### What to Type
> "Search Google for cute cats"

### What Should Happen
1. Opens browser
2. Goes to google.com
3. Types "cute cats"
4. Clicks search
5. Done!

---

## Controls During Demo

- **ESC** - Emergency stop, halts everything
- **STOP button** (red, top-right) - Same as ESC
- **Drag plant** - Move it out of the way if needed

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Plant doesn't appear | Check PySide6 installed, try `pip install PySide6` |
| No sound recording | Install PyAudio: `pip install pyaudio`. If fails, use text input |
| "Planning failed" | Check ANTHROPIC_API_KEY is set correctly |
| Browser doesn't open | Run `playwright install chromium` |
| Cursor doesn't move | Run as Administrator for pyautogui access |
| Overlay not click-through | Windows issue, try restarting app |
