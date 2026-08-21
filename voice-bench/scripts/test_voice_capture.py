"""No-network tests for the VP-2 write-only transcript capture contract."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from voice_capture import VoiceTurnWriter


def main() -> None:
    sent = []
    writer = VoiceTurnWriter(
        url="https://example.invalid",
        key="test-only",
        surface="livekit",
        room="voice-bench",
        call_id="vp2-test-call",
    )
    writer._post = sent.append
    writer.record_user(" Hello from Chris. ")
    asyncio.run(writer.record_assistant(" Hello Chris. "))
    assert sent == [
        {
            "p_call_id": "vp2-test-call",
            "p_user_message": "Hello from Chris.",
            "p_assistant_response": "Hello Chris.",
        }
    ]
    assert writer._pending_user is None

    try:
        asyncio.run(writer.record_assistant("orphan"))
    except RuntimeError as exc:
        assert "no user pair" in str(exc)
    else:
        raise AssertionError("orphan assistant turn was not rejected")

    writer.record_user("first")
    try:
        writer.record_user("second")
    except RuntimeError as exc:
        assert "prior user turn" in str(exc)
    else:
        raise AssertionError("unpaired user overwrite was not rejected")

    print("PASS voice capture: paired RPC payload + fail-closed invariants")


if __name__ == "__main__":
    main()
