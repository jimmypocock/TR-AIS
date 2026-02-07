import json
import uuid
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from midi_engine import MIDIEngine
from pattern_generator import PatternGenerator

load_dotenv()

app = FastAPI(title="TR-AIS")

# --- Global State ---
sessions: dict = {}
engine: Optional[MIDIEngine] = None
generator: Optional[PatternGenerator] = None
active_session_id: Optional[str] = None
connected_websockets: list[WebSocket] = []
loop: Optional[asyncio.AbstractEventLoop] = None

SESSIONS_FILE = Path("sessions.json")


# --- Persistence ---
def save_sessions():
    try:
        with open(SESSIONS_FILE, "w") as f:
            json.dump(sessions, f, indent=2, default=str)
    except Exception as e:
        print(f"Warning: Could not save sessions: {e}")


def load_sessions():
    global sessions
    if SESSIONS_FILE.exists():
        try:
            with open(SESSIONS_FILE, "r") as f:
                sessions = json.load(f)
            print(f"📂 Loaded {len(sessions)} sessions")
        except Exception as e:
            print(f"Warning: Could not load sessions: {e}")
            sessions = {}


# --- Request Models ---
class MessageRequest(BaseModel):
    content: str


class ParamsUpdate(BaseModel):
    bpm: Optional[float] = None
    swing: Optional[float] = None


class SessionCreate(BaseModel):
    name: Optional[str] = None


class MidiDeviceSelect(BaseModel):
    device: str


# --- WebSocket Broadcast ---
async def broadcast(data: dict):
    dead = []
    for ws in connected_websockets:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in connected_websockets:
            connected_websockets.remove(ws)


def on_step(step: int):
    """Called from MIDI engine thread on each step."""
    if loop and connected_websockets:
        asyncio.run_coroutine_threadsafe(
            broadcast({"type": "step", "step": step}), loop
        )


# --- Lifecycle ---
@app.on_event("startup")
async def startup():
    global engine, generator, loop
    loop = asyncio.get_event_loop()

    load_sessions()

    # Initialize MIDI engine (connects to first available device)
    available_devices = MIDIEngine.list_devices()
    if available_devices:
        print(f"🎹 Available MIDI devices: {', '.join(available_devices)}")
        try:
            engine = MIDIEngine()  # Auto-connects to first available
            engine.on_step = on_step
            print(f"✅ Connected to MIDI: {engine.port_name}")
        except Exception as e:
            print(f"⚠️  Could not connect to MIDI: {e}")
            print("   Running in demo mode (no MIDI output)")
            engine = None
    else:
        print("⚠️  No MIDI devices found")
        print("   Running in demo mode (no MIDI output)")
        engine = None

    # Init Claude
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            generator = PatternGenerator()
            print("✅ Claude API ready")
        except Exception as e:
            print(f"⚠️  Claude API error: {e}")
            generator = None
    else:
        print("⚠️  No ANTHROPIC_API_KEY — copy .env.example to .env and add your key")
        generator = None


@app.on_event("shutdown")
async def shutdown():
    if engine:
        engine.close()
    save_sessions()
    print("👋 Shut down cleanly")


# --- WebSocket ---
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_websockets.append(ws)

    # Send current state on connect
    state = {
        "type": "state",
        "playing": engine.playing if engine else False,
        "active_session": active_session_id,
        "step": engine.current_step if engine else 0,
        "bpm": engine.bpm if engine else 120,
        "swing": engine.swing if engine else 0,
        "sessions": list(sessions.values()),
        "midi_devices": MIDIEngine.list_devices(),
        "midi_device": engine.port_name if engine else None,
    }
    if active_session_id and active_session_id in sessions:
        session = sessions[active_session_id]
        state["session"] = session
        if session["patterns"] and session["current_version"] >= 0:
            pattern = session["patterns"][session["current_version"]]
            state["pattern"] = pattern
            # Ensure engine has the pattern loaded
            if engine and not engine.pattern:
                engine.set_pattern(pattern)
    await ws.send_json(state)

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in connected_websockets:
            connected_websockets.remove(ws)


# --- Session Endpoints ---
@app.post("/api/sessions")
async def create_session(req: SessionCreate):
    session_id = str(uuid.uuid4())[:8]
    session = {
        "id": session_id,
        "name": req.name or f"Session {len(sessions) + 1}",
        "conversation": [],
        "patterns": [],
        "current_version": -1,
        "created_at": datetime.now().isoformat(),
    }
    sessions[session_id] = session
    save_sessions()
    await broadcast({"type": "session_created", "session": session})
    return session


@app.get("/api/sessions")
async def list_sessions():
    return list(sessions.values())


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    global active_session_id
    if session_id not in sessions:
        return {"error": "Session not found"}

    # Load the session's current pattern into the engine
    session = sessions[session_id]
    active_session_id = session_id
    if engine and session["patterns"] and session["current_version"] >= 0:
        pattern = session["patterns"][session["current_version"]]
        engine.set_pattern(pattern)
        print(f"📂 Loaded pattern from session {session_id}")

    return session


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    global active_session_id
    if session_id in sessions:
        del sessions[session_id]
        if active_session_id == session_id:
            active_session_id = None
            if engine:
                engine.stop()
        save_sessions()
        await broadcast({"type": "session_deleted", "session_id": session_id})
    return {"ok": True}


# --- Message & Pattern Generation ---
@app.post("/api/sessions/{session_id}/message")
async def send_message(session_id: str, req: MessageRequest):
    global active_session_id

    if session_id not in sessions:
        return {"error": "Session not found"}
    if not generator:
        return {"error": "No API key configured. Add ANTHROPIC_API_KEY to your .env file."}

    session = sessions[session_id]
    active_session_id = session_id

    # Build Claude conversation from history
    claude_messages = []
    for msg in session["conversation"]:
        claude_messages.append({"role": msg["role"], "content": msg["content"]})

    # New user message - inject current pattern context if we have one
    user_content = req.content
    if session["patterns"] and session["current_version"] >= 0:
        current_pattern = session["patterns"][session["current_version"]]
        user_content += (
            f"\n\n[CONTEXT — the current playing pattern is:\n"
            f"```json\n{json.dumps(current_pattern, indent=2)}\n```\n"
            f"Modify this pattern based on my request above. Keep everything I didn't mention.]"
        )

    claude_messages.append({"role": "user", "content": user_content})

    # Broadcast that we're generating
    await broadcast({"type": "generating", "session_id": session_id})

    # Generate pattern
    try:
        message, pattern = generator.generate(claude_messages)
    except Exception as e:
        return {"error": f"Generation failed: {str(e)}"}

    # Store in conversation (clean version without injected context)
    session["conversation"].append({"role": "user", "content": req.content})
    session["conversation"].append({"role": "assistant", "content": message})

    # Store pattern version
    if pattern:
        session["patterns"].append(pattern)
        session["current_version"] = len(session["patterns"]) - 1

        # Send to TR-8S and start playing
        if engine:
            engine.set_pattern(pattern)
            if not engine.playing:
                engine.play()

    save_sessions()

    result = {
        "message": message,
        "pattern": pattern,
        "version": session["current_version"],
        "total_versions": len(session["patterns"]),
    }

    await broadcast({
        "type": "pattern_update",
        "session_id": session_id,
        **result,
        "playing": engine.playing if engine else False,
        "bpm": pattern.get("bpm", 120) if pattern else (engine.bpm if engine else 120),
        "swing": pattern.get("swing", 0) if pattern else (engine.swing if engine else 0),
    })

    return result


# --- Playback Controls ---
@app.post("/api/play")
async def play():
    print(f"▶️  Play requested - engine={engine is not None}, pattern={engine.pattern is not None if engine else 'N/A'}, port={engine.port_name if engine else 'N/A'}")
    if engine and engine.pattern:
        engine.play()
        print(f"▶️  Play started - playing={engine.playing}")
        await broadcast({"type": "playback", "playing": True})
        return {"playing": True}
    return {"error": "No pattern loaded"}


@app.post("/api/stop")
async def stop():
    if engine:
        engine.stop()
        await broadcast({"type": "playback", "playing": False, "step": -1})
    return {"playing": False}


@app.post("/api/sessions/{session_id}/version/{version}")
async def set_version(session_id: str, version: int):
    if session_id not in sessions:
        return {"error": "Session not found"}

    session = sessions[session_id]
    if 0 <= version < len(session["patterns"]):
        session["current_version"] = version
        pattern = session["patterns"][version]
        if engine:
            engine.set_pattern(pattern)
        save_sessions()

        await broadcast({
            "type": "version_change",
            "version": version,
            "total_versions": len(session["patterns"]),
            "pattern": pattern,
            "bpm": pattern.get("bpm", 120),
            "swing": pattern.get("swing", 0),
        })
        return {"version": version, "pattern": pattern}
    return {"error": f"Invalid version (0-{len(session['patterns'])-1})"}


@app.patch("/api/params")
async def update_params(req: ParamsUpdate):
    if engine:
        if req.bpm is not None:
            engine.set_bpm(req.bpm)
        if req.swing is not None:
            engine.set_swing(req.swing)
        await broadcast({
            "type": "params",
            "bpm": engine.bpm,
            "swing": engine.swing,
        })
        return {"bpm": engine.bpm, "swing": engine.swing}
    return {"error": "No MIDI engine"}


# --- MIDI Device Management ---
@app.get("/api/midi/devices")
async def list_midi_devices():
    """List all available MIDI output devices."""
    devices = MIDIEngine.list_devices()
    return {
        "devices": devices,
        "current": engine.port_name if engine else None,
    }


@app.post("/api/midi/select")
async def select_midi_device(req: MidiDeviceSelect):
    """Switch to a different MIDI device."""
    global engine

    available = MIDIEngine.list_devices()
    if req.device not in available:
        return {"error": f"Device not found: {req.device}"}

    if engine:
        # Switch existing engine to new device
        try:
            engine.switch_device(req.device)
        except Exception as e:
            return {"error": str(e)}
    else:
        # No engine yet, create one
        try:
            engine = MIDIEngine(req.device)
            engine.on_step = on_step
        except Exception as e:
            return {"error": f"Could not connect: {e}"}

    # Broadcast device change to all clients
    await broadcast({
        "type": "midi_device",
        "device": engine.port_name,
        "devices": available,
    })

    return {"device": engine.port_name, "ok": True}


@app.post("/api/midi/refresh")
async def refresh_midi_devices():
    """Refresh the list of available MIDI devices."""
    devices = MIDIEngine.list_devices()
    await broadcast({
        "type": "midi_devices",
        "devices": devices,
        "current": engine.port_name if engine else None,
    })
    return {"devices": devices, "current": engine.port_name if engine else None}


# --- Static Files & Index ---
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


# --- Run ---
if __name__ == "__main__":
    import uvicorn
    print("\n🥁 TR-AIS — AI Drum Pattern Generator for Roland TR-8S")
    print("   Open http://localhost:8000 in your browser")
    print("   Or from your phone: http://<your-mac-ip>:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)