"""VP-2 component smoke test — no mic/speaker needed.

Verifies each sovereign component in isolation, then the STT<->TTS round trip:
Kokoro synthesizes a known sentence to a WAV, Moonshine transcribes it back,
and the words must overlap. Sections that need something this machine lacks
(network for first-time model download, a running Ollama) SKIP with a reason
instead of failing, so the same script is useful on any box.

Run:  python scripts/smoke_test.py     (from the voice-bench/ directory)
Exit code 0 = no failures (skips allowed). The mic->speaker gate demo is
src/bot.py on real hardware; this script is evidence, not the gate.
"""

import asyncio
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"
OUT_DIR = REPO_ROOT / "out"
os.environ.setdefault("MOONSHINE_VOICE_CACHE", str(MODELS_DIR / "moonshine"))
os.environ.setdefault("NLTK_DATA", str(MODELS_DIR / "nltk_data"))

import numpy as np

TEST_SENTENCE = "The quick brown fox jumps over the lazy dog"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
MOONSHINE_MODEL = os.getenv("MOONSHINE_MODEL", "base")
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "af_heart")

results: list[tuple[str, str, str]] = []  # (name, PASS|SKIP|FAIL, detail)


def record(name: str, status: str, detail: str = ""):
    results.append((name, status, detail))
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def resample_to_16k(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    if sample_rate == 16000:
        return samples
    target_len = int(len(samples) * 16000 / sample_rate)
    return np.interp(
        np.linspace(0, len(samples) - 1, target_len), np.arange(len(samples)), samples
    )


def check_imports():
    import pipecat

    from pipecat.audio.vad.silero import SileroVADAnalyzer  # noqa: F401
    from pipecat.processors.aggregators.llm_context import LLMContext  # noqa: F401
    from pipecat.services.kokoro.tts import KokoroTTSService  # noqa: F401
    from pipecat.services.moonshine.stt import MoonshineSTTService  # noqa: F401
    from pipecat.services.ollama.llm import OLLamaLLMService  # noqa: F401

    record("imports", "PASS", f"pipecat {pipecat.__version__}")


async def check_silero_vad():
    from pipecat.audio.vad.silero import SileroVADAnalyzer

    vad = SileroVADAnalyzer()
    vad.set_sample_rate(16000)
    n = vad.num_frames_required()
    silence = np.zeros(n, dtype=np.int16).tobytes()
    state = await vad.analyze_audio(silence)
    record("silero-vad", "PASS", f"bundled ONNX model loaded; silence -> {state.name}")


def synthesize_kokoro() -> tuple[np.ndarray, int] | None:
    """Synthesize TEST_SENTENCE; returns (float32 samples, sample_rate) or None."""
    from pipecat.services.kokoro.tts import _ensure_model_files

    model_path = MODELS_DIR / "kokoro" / "kokoro-v1.0.onnx"
    voices_path = MODELS_DIR / "kokoro" / "voices-v1.0.bin"
    try:
        _ensure_model_files(model_path, voices_path)
    except Exception as e:
        record("kokoro-tts", "SKIP", f"model download failed (offline box?): {e}")
        return None

    from kokoro_onnx import Kokoro

    kokoro = Kokoro(str(model_path), str(voices_path))
    samples, sample_rate = kokoro.create(TEST_SENTENCE, voice=KOKORO_VOICE, lang="en-us")

    import soundfile as sf

    OUT_DIR.mkdir(exist_ok=True)
    wav_path = OUT_DIR / "kokoro_smoke.wav"
    sf.write(wav_path, samples, sample_rate)
    secs = len(samples) / sample_rate
    record("kokoro-tts", "PASS", f"{secs:.1f}s of audio @ {sample_rate} Hz -> {wav_path}")
    return samples, sample_rate


async def check_vad_on_speech(audio: tuple[np.ndarray, int] | None):
    """Run Silero over the Kokoro speech: real speech must trigger SPEAKING."""
    if audio is None:
        record("vad-on-speech", "SKIP", "no TTS audio to analyze")
        return
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.audio.vad.vad_analyzer import VADState

    samples, sample_rate = audio
    vad = SileroVADAnalyzer()
    vad.set_sample_rate(16000)
    pcm = (np.clip(resample_to_16k(samples, sample_rate), -1, 1) * 32767).astype(np.int16)
    n = vad.num_frames_required()
    states = set()
    for i in range(0, len(pcm) - n, n):
        states.add(await vad.analyze_audio(pcm[i : i + n].tobytes()))
    status = "PASS" if VADState.SPEAKING in states else "FAIL"
    record("vad-on-speech", status, f"states over utterance: {sorted(s.name for s in states)}")


def transcribe_moonshine(audio: tuple[np.ndarray, int] | None):
    try:
        from moonshine_voice import Transcriber, get_model_for_language, string_to_model_arch

        model_path, arch = get_model_for_language("en", string_to_model_arch(MOONSHINE_MODEL))
    except Exception as e:
        record("moonshine-stt", "SKIP", f"model download failed (offline box?): {e}")
        return

    transcriber = Transcriber(model_path, arch)
    if audio is None:
        record("moonshine-stt", "PASS", "model loaded (no TTS audio for round trip)")
        return

    samples, sample_rate = audio
    samples = resample_to_16k(samples, sample_rate)  # Moonshine wants 16 kHz mono
    transcript = transcriber.transcribe_without_streaming(
        samples.astype(np.float32).tolist(), 16000
    )
    text = " ".join(line.text for line in transcript.lines).strip()

    expected = set(TEST_SENTENCE.lower().split())
    got = set("".join(c for c in text.lower() if c.isalpha() or c == " ").split())
    overlap = len(expected & got) / len(expected)
    status = "PASS" if overlap >= 0.7 else "FAIL"
    record("stt-tts-roundtrip", status, f'heard "{text}" ({overlap:.0%} word match)')


def check_ollama():
    import urllib.error
    import urllib.request

    base = OLLAMA_BASE_URL.rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/models", timeout=5) as resp:
            body = resp.read().decode()
    except (urllib.error.URLError, OSError) as e:
        record("ollama", "SKIP", f"no Ollama at {base}: {e}")
        return
    if OLLAMA_MODEL.split(":")[0] in body:
        record("ollama", "PASS", f"endpoint up, model {OLLAMA_MODEL} available")
    else:
        record("ollama", "FAIL", f"endpoint up but {OLLAMA_MODEL} not in `ollama list`")


def check_pipeline_graph():
    """Build the bot's pipeline graph with the LLM stage (models not needed)."""
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
    from pipecat.services.ollama.llm import OLLamaLLMService

    llm = OLLamaLLMService(
        base_url=OLLAMA_BASE_URL, settings=OLLamaLLMService.Settings(model=OLLAMA_MODEL)
    )
    aggregators = LLMContextAggregatorPair(
        LLMContext(messages=[{"role": "system", "content": "smoke"}])
    )
    Pipeline([aggregators.user(), llm, aggregators.assistant()])
    record("pipeline-graph", "PASS", "aggregators + OLLamaLLMService wired")


def run(section, fn, *args):
    try:
        return fn(*args) if not asyncio.iscoroutinefunction(fn) else asyncio.run(fn(*args))
    except Exception:
        record(section, "FAIL", traceback.format_exc(limit=1).strip().splitlines()[-1])
        return None


def main():
    print("VP-2 component smoke test")
    run("imports", check_imports)
    run("silero-vad", check_silero_vad)
    audio = run("kokoro-tts", synthesize_kokoro)
    run("vad-on-speech", check_vad_on_speech, audio)
    run("moonshine-stt", transcribe_moonshine, audio)
    run("ollama", check_ollama)
    run("pipeline-graph", check_pipeline_graph)

    failed = [r for r in results if r[1] == "FAIL"]
    print(f"\n{len(results)} sections: "
          f"{sum(1 for r in results if r[1] == 'PASS')} passed, "
          f"{sum(1 for r in results if r[1] == 'SKIP')} skipped, "
          f"{len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
