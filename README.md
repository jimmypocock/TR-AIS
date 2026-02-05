# 🥁 TR-AIS — AI Drum Pattern Generator for Roland TR-8S

Talk to your TR-8S like a band member. Describe the beat you want in natural language, and AI programs it in real time.

## Setup

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Set your Anthropic API key
cp .env.example .env
# Edit .env and add your key

# 3. Connect TR-8S via USB and make sure it shows in Audio MIDI Setup

# 4. Run
python3 main.py
```

Open <http://localhost:8000> in your browser.

### Access from Your Phone

Control TR-AIS from your phone while you're at the TR-8S — as long as you're on the same WiFi network.

**Find your Mac's IP address:**
```bash
# From Terminal
ipconfig getifaddr en0
```

Or visit [whatismyipaddress.com](https://whatismyipaddress.com) and look for your **Private IP** (not the public one).

**Then on your phone:** Open `http://<your-ip>:8000` (e.g., `http://192.168.1.42:8000`)

## Usage

1. Click **+** to create a session
2. Type what you want: *"80s power ballad, big snare, 78 BPM"*
3. The TR-8S starts playing immediately
4. Refine: *"Add some ghost notes on the snare"*
5. Keep jamming — each message builds on the last

## Controls

- **Play/Stop**: Start or stop the sequencer
- **BPM slider**: Adjust tempo in real time
- **Swing slider**: Add shuffle feel
- **Version nav**: Browse pattern history (◀ ▶)

## Files

- `main.py` — FastAPI server & WebSocket
- `midi_engine.py` — Real-time MIDI sequencer
- `pattern_generator.py` — Claude API integration
- `static/index.html` — Web UI
- `sessions.json` — Auto-saved session data
