"""Write-only, paired VP-2 transcript capture through Wingman's voice door.

The runtime never reads from Wingman. One completed user/assistant exchange is
sent to ``voice_log_turn``; that governed RPC applies the canonical voice dye
and writes the two hot-layer rows.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from urllib import error, request

from loguru import logger
from pipecat.frames.frames import (
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


@dataclass
class VoiceTurnWriter:
    url: str
    key: str
    surface: str
    room: str
    call_id: str = field(default_factory=lambda: f"vp2-livekit-{uuid.uuid4()}")
    _pending_user: str | None = None

    @classmethod
    def from_environment(cls, *, surface: str, room: str) -> "VoiceTurnWriter":
        url = os.getenv("NOVACORE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
        key = os.getenv("NOVACORE_SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise RuntimeError(
                "Write-only transcript capture requires NOVACORE_SUPABASE_URL and "
                "NOVACORE_SUPABASE_KEY"
            )
        return cls(url=url.rstrip("/"), key=key, surface=surface, room=room)

    def record_user(self, text: str) -> None:
        clean = text.strip()
        if not clean:
            return
        if self._pending_user is not None:
            raise RuntimeError("Capture invariant failed: prior user turn has no assistant pair")
        self._pending_user = clean

    async def record_assistant(self, text: str) -> None:
        clean = text.strip()
        if not clean:
            return
        if self._pending_user is None:
            raise RuntimeError("Capture invariant failed: assistant turn has no user pair")
        payload = {
            "p_call_id": self.call_id,
            "p_user_message": self._pending_user,
            "p_assistant_response": clean,
        }
        await asyncio.to_thread(self._post, payload)
        self._pending_user = None
        logger.info(
            "Captured paired voice transcript through voice_log_turn "
            f"(surface={self.surface}, room={self.room}, call_id={self.call_id})"
        )

    def _post(self, payload: dict[str, str]) -> None:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.url + "/rest/v1/rpc/voice_log_turn",
            data=body,
            method="POST",
            headers={
                "apikey": self.key,
                "Authorization": "Bearer " + self.key,
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=15) as response:
                if response.status < 200 or response.status >= 300:
                    raise RuntimeError(f"voice_log_turn returned HTTP {response.status}")
        except error.HTTPError as exc:
            raise RuntimeError(f"voice_log_turn failed with HTTP {exc.code}") from exc
        except error.URLError as exc:
            raise RuntimeError("voice_log_turn transport failed") from exc


class UserTurnCapture(FrameProcessor):
    def __init__(self, writer: VoiceTurnWriter):
        super().__init__()
        self._writer = writer

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame):
            self._writer.record_user(frame.text)
        await self.push_frame(frame, direction)


class AssistantTurnCapture(FrameProcessor):
    def __init__(self, writer: VoiceTurnWriter):
        super().__init__()
        self._writer = writer
        self._chunks: list[str] = []
        self._collecting = False

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMFullResponseStartFrame):
            self._chunks = []
            self._collecting = True
        elif isinstance(frame, LLMTextFrame) and self._collecting:
            self._chunks.append(frame.text)
        elif isinstance(frame, LLMFullResponseEndFrame) and self._collecting:
            self._collecting = False
            await self._writer.record_assistant("".join(self._chunks))
            self._chunks = []
        await self.push_frame(frame, direction)
