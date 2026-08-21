"""VP-2 phase 2: same sovereign loop, LiveKit room as transport.

Chris's surfaces (NovaCore mobile app, later Twilio SIP, desk press-to-talk)
join a room on the SELF-HOSTED LiveKit server as clients; this bot joins as
another participant. Gate 1 (redefined 2026-08-21T17:30Z): a real two-way
spoken exchange with Chris from one of his surfaces.

    Chris's mic --LiveKit--> Silero VAD -> Moonshine STT -> Ollama -> Kokoro TTS --LiveKit--> Chris's speaker

Run:  python src/bot_livekit.py         (from the voice-bench/ directory)
Env:  LIVEKIT_URL        default ws://localhost:7880   (bot runs next to the server)
      LIVEKIT_API_KEY    required; loaded from external secret file by launcher
      LIVEKIT_API_SECRET required; loaded from external secret file by launcher
      NOVACORE_SUPABASE_URL / NOVACORE_SUPABASE_KEY required for write-only capture
      LIVEKIT_ROOM       default voice-bench
      plus the same OLLAMA_* / MOONSHINE_MODEL / KOKORO_VOICE as bot.py

Mint a token for a phone/browser client with scripts/livekit_token.py.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"
os.environ.setdefault("MOONSHINE_VOICE_CACHE", str(MODELS_DIR / "moonshine"))
os.environ.setdefault("NLTK_DATA", str(MODELS_DIR / "nltk_data"))

import asyncio

from livekit import api
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.services.moonshine.stt import MoonshineSTTService
from pipecat.services.ollama.llm import OLLamaLLMService
from pipecat.transcriptions.language import Language
from pipecat.transports.livekit.transport import LiveKitParams, LiveKitTransport

from voice_capture import AssistantTurnCapture, UserTurnCapture, VoiceTurnWriter

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.environ["LIVEKIT_API_KEY"]
LIVEKIT_API_SECRET = os.environ["LIVEKIT_API_SECRET"]
LIVEKIT_ROOM = os.getenv("LIVEKIT_ROOM", "voice-bench")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct")
MOONSHINE_MODEL = os.getenv("MOONSHINE_MODEL", "base")
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "af_heart")

SYSTEM_PROMPT = (
    "You are a local, fully offline voice assistant. Your answers are spoken "
    "aloud over a call, so keep them to one or two short sentences, with no "
    "markdown, lists, or special characters."
)


def bot_token() -> str:
    """Mint the bot's own room token against the self-hosted server."""
    return (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity("vp2-bot")
        .with_name("VP-2 Voice Bench")
        .with_grants(api.VideoGrants(room_join=True, room=LIVEKIT_ROOM))
        .to_jwt()
    )


async def main():
    transport = LiveKitTransport(
        url=LIVEKIT_URL,
        token=bot_token(),
        room_name=LIVEKIT_ROOM,
        params=LiveKitParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    stt = MoonshineSTTService(
        settings=MoonshineSTTService.Settings(model=MOONSHINE_MODEL, language=Language.EN)
    )
    tts = KokoroTTSService(
        model_path=str(MODELS_DIR / "kokoro" / "kokoro-v1.0.onnx"),
        voices_path=str(MODELS_DIR / "kokoro" / "voices-v1.0.bin"),
        settings=KokoroTTSService.Settings(voice=KOKORO_VOICE, language=Language.EN),
    )
    llm = OLLamaLLMService(
        base_url=OLLAMA_BASE_URL, settings=OLLamaLLMService.Settings(model=OLLAMA_MODEL)
    )

    aggregators = LLMContextAggregatorPair(
        LLMContext(messages=[{"role": "system", "content": SYSTEM_PROMPT}])
    )
    capture = VoiceTurnWriter.from_environment(surface="livekit", room=LIVEKIT_ROOM)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            UserTurnCapture(capture),
            aggregators.user(),
            llm,
            AssistantTurnCapture(capture),
            tts,
            transport.output(),
            aggregators.assistant(),
        ]
    )

    worker = PipelineWorker(
        pipeline,
        # This is a call surface, not a one-shot job. Keep it resident while
        # waiting for Chris rather than cancelling after Pipecat's 300s default.
        idle_timeout_secs=None,
        cancel_on_idle_timeout=False,
        cancel_runner_on_idle_timeout=False,
        params=PipelineParams(
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000,
            enable_metrics=True,
        ),
    )

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant_id):
        logger.info(f"Participant joined: {participant_id} — ready for captured exchange")

    logger.info(f"LiveKit: room '{LIVEKIT_ROOM}' @ {LIVEKIT_URL}")
    logger.info(f"LLM: {OLLAMA_MODEL} @ {OLLAMA_BASE_URL}")
    logger.info("Waiting for a participant (phone/app/browser client)...")

    runner = PipelineRunner(handle_sigint=True)
    await runner.run(worker)


if __name__ == "__main__":
    asyncio.run(main())
