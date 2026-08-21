"""VP-2 phase 1: sovereign local voice loop.

mic -> Silero VAD -> Moonshine STT -> Ollama LLM -> Kokoro TTS -> speaker

All inference is local: ONNX on CPU for VAD/STT/TTS; the LLM is the machine's
existing Ollama endpoint. No cloud APIs, no keys. Phase 1 gate: one working
spoken exchange through this loop on real mic/speaker hardware.

Run:  python src/bot.py            (from the voice-bench/ directory)
Env:  OLLAMA_BASE_URL   default http://localhost:11434/v1
      OLLAMA_MODEL      default qwen2.5:14b-instruct (verified on Gammy)
      MOONSHINE_MODEL   default base         (tiny|base|small-streaming|...)
      KOKORO_VOICE      default af_heart
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"
# VP-2 constraint: touch nothing outside the repo — all model caches live here.
# Must be set before pipecat's moonshine service imports moonshine_voice.
os.environ.setdefault("MOONSHINE_VOICE_CACHE", str(MODELS_DIR / "moonshine"))
os.environ.setdefault("NLTK_DATA", str(MODELS_DIR / "nltk_data"))

import asyncio

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
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct")
# English Moonshine models carry the standard license; non-English ones are
# non-commercial Community License — keep language pinned to EN for VP-2.
MOONSHINE_MODEL = os.getenv("MOONSHINE_MODEL", "base")
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "af_heart")


def optional_device_index(name: str) -> int | None:
    value = os.getenv(name)
    return int(value) if value not in (None, "") else None

SYSTEM_PROMPT = (
    "You are a local, fully offline voice assistant running on this machine. "
    "Your answers are spoken aloud, so keep them to one or two short sentences, "
    "with no markdown, lists, or special characters."
)


async def main():
    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            input_device_index=optional_device_index("AUDIO_INPUT_DEVICE_INDEX"),
            output_device_index=optional_device_index("AUDIO_OUTPUT_DEVICE_INDEX"),
            vad_analyzer=SileroVADAnalyzer(),
        )
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

    context = LLMContext(messages=[{"role": "system", "content": SYSTEM_PROMPT}])
    aggregators = LLMContextAggregatorPair(context)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            aggregators.user(),
            llm,
            tts,
            transport.output(),
            aggregators.assistant(),
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=16000,  # Moonshine's required rate
            audio_out_sample_rate=24000,  # Kokoro's native rate
            enable_metrics=True,
        ),
    )

    logger.info(f"LLM: {OLLAMA_MODEL} @ {OLLAMA_BASE_URL}")
    logger.info(f"STT: moonshine/{MOONSHINE_MODEL}  TTS: kokoro/{KOKORO_VOICE}")
    logger.info(
        "Audio devices: input={} output={} (None means PortAudio default)",
        optional_device_index("AUDIO_INPUT_DEVICE_INDEX"),
        optional_device_index("AUDIO_OUTPUT_DEVICE_INDEX"),
    )
    logger.info("Speak into the mic; Ctrl-C to quit.")

    runner = PipelineRunner(handle_sigint=True)
    await runner.run(worker)


if __name__ == "__main__":
    asyncio.run(main())
