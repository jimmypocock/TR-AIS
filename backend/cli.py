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


async def get_session_state(client: AbletonClient) -> dict:
    """Get current session state for Claude context."""
    state = {
        "tempo": await client.transport.get_tempo(),
        "playing": await client.transport.is_playing(),
        "tracks": []
    }

    # Get track count and info
    track_count = await client.tracks.get_count()
    if track_count:
        for i in range(track_count):
            track_info = {
                "index": i,
                "name": f"Track {i + 1}",  # Will be replaced when we have name fetching
            }
            state["tracks"].append(track_info)

    return state


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
        print("Set your API key:")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
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

    # Get initial state
    tempo = await client.transport.get_tempo()
    track_count = await client.tracks.get_count()
    print(f"[OK] Connected to Ableton (tempo: {tempo} BPM, {track_count} tracks)")
    print()

    # Create executor
    executor = CommandExecutor(client)

    # Print help
    print("Commands:")
    print("  Type natural language to control Ableton")
    print("  'state' - Show current session state")
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

            if user_input.lower() == "state":
                state = await get_session_state(client)
                print(f"Tempo: {state['tempo']} BPM")
                print(f"Playing: {state['playing']}")
                print(f"Tracks: {len(state['tracks'])}")
                for t in state["tracks"]:
                    print(f"  [{t['index']}] {t['name']}")
                continue

            # Get current session state
            session_state = await get_session_state(client)

            # Process with Claude
            print("[Thinking...]")
            result = engine.process(user_input, session_state)

            if result.error:
                print(f"[Error] {result.error}")
                continue

            # Show thinking (optional)
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
