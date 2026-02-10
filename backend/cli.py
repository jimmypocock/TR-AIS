"""
CLI for Ableton AI Assistant.

Simple REPL for testing natural language control of Ableton.

Usage:
    python3 -m backend.cli
"""

import asyncio
import sys

from .ableton import AbletonClient
from .claude_engine import ClaudeEngine
from .executor import CommandExecutor
from .session_cache import SessionCache


async def main():
    """Main CLI loop."""
    print("=" * 50)
    print("Ableton AI Assistant")
    print("=" * 50)
    print()

    # Initialize Claude engine
    try:
        engine = ClaudeEngine()
        print("[OK] Claude engine initialized")
    except ValueError as e:
        print(f"[ERROR] {e}")
        print()
        print("Set your API key in .env:")
        print("  ANTHROPIC_API_KEY=sk-ant-...")
        return

    # Connect to Ableton
    client = AbletonClient()
    print("[...] Connecting to Ableton...")

    try:
        connected = await client.connect()
        if not connected:
            print("[ERROR] Could not connect to Ableton")
            print()
            print("Make sure:")
            print("  1. Ableton Live is running")
            print("  2. AbletonOSC is installed and enabled")
            print("  3. Status bar shows 'Listening for OSC on port 11000'")
            return
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    # Get initial tempo
    tempo = await client.transport.get_tempo()
    print(f"[OK] Connected (tempo: {tempo} BPM)")

    # Initialize session cache (skip devices for faster startup)
    cache = SessionCache(client)
    print("[...] Loading tracks...")
    try:
        await cache.refresh(include_devices=False)
        state = cache.state
        print(f"[OK] Loaded {len(state.tracks)} tracks")

        # Show tracks
        if state.tracks:
            print()
            print("Tracks:")
            for t in state.tracks:
                devices_str = f" [{len(t.devices)} devices]" if t.devices else ""
                print(f"  [{t.index}] {t.name}{devices_str}")
    except Exception as e:
        print(f"[Warning] Could not load full session state: {e}")
        state = cache.state  # Use whatever we got

    print()

    # Create executor
    executor = CommandExecutor(client)

    # Print help
    print("Commands:")
    print("  Type natural language to control Ableton")
    print("  'state' or 'refresh' - Refresh and show session state")
    print("  'quit' or 'exit' - Exit the CLI")
    print()
    print("-" * 50)

    # Main loop
    while True:
        try:
            # Get input
            user_input = input("\n> ").strip()

            if not user_input:
                continue

            # Handle special commands
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            if user_input.lower() in ("state", "refresh"):
                print("[...] Refreshing session state...")
                await cache.refresh()
                state = cache.state

                print(f"Tempo: {state.tempo} BPM")
                print(f"Playing: {state.playing}")
                print(f"Recording: {state.recording}")
                print(f"Metronome: {'on' if state.metronome else 'off'}")
                print()
                print(f"Tracks ({len(state.tracks)}):")
                for t in state.tracks:
                    status = []
                    if t.muted:
                        status.append("M")
                    if t.soloed:
                        status.append("S")
                    if t.armed:
                        status.append("R")
                    status_str = f" [{' '.join(status)}]" if status else ""

                    devices = [d.name for d in t.devices]
                    devices_str = f" → {', '.join(devices)}" if devices else ""

                    vol_pct = int(t.volume * 100)
                    pan_str = f"L{int(-t.pan*100)}" if t.pan < 0 else f"R{int(t.pan*100)}" if t.pan > 0 else "C"

                    print(f"  [{t.index}] {t.name} (vol:{vol_pct}% pan:{pan_str}){status_str}{devices_str}")
                continue

            # Use cached session state for Claude context (no refresh - use what we have)
            session_state = cache.state.to_dict()

            # Process with Claude
            print("[Thinking...]")
            result = engine.process(user_input, session_state)

            if result.error:
                print(f"[Error] {result.error}")
                continue

            # Show thinking
            if result.thinking:
                print(f"[Thought] {result.thinking}")

            # Validate and execute commands
            if result.commands:
                valid_cmds, errors = engine.validate_commands(result.commands)

                if errors:
                    for err in errors:
                        print(f"[Warning] {err}")

                if valid_cmds:
                    print(f"[Executing {len(valid_cmds)} command(s)...]")
                    report = await executor.execute(valid_cmds)

                    for r in report.results:
                        if r.success:
                            print(f"  [OK] {r.action}: {r.result}")
                        else:
                            print(f"  [FAIL] {r.action}: {r.error}")

            # Show Claude's response
            if result.response:
                print()
                print(result.response)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"[Error] {e}")

    # Cleanup
    client.disconnect()


def run():
    """Entry point for the CLI."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
