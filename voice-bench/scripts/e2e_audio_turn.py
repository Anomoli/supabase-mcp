"""Run one deterministic sovereign audio turn without physical I/O.

Kokoro synthesizes the caller prompt, Moonshine transcribes it, local Ollama
answers, Kokoro synthesizes the answer, and Moonshine independently transcribes
that answer. WAV artifacts and a JSON receipt are written under out/.

This proves the full model chain but is NOT the VP-2 physical mic/speaker gate.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
from moonshine_voice import Transcriber, get_model_for_language, string_to_model_arch
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
OUT = ROOT / "out"
os.environ.setdefault("MOONSHINE_VOICE_CACHE", str(MODELS / "moonshine"))
os.environ.setdefault("NLTK_DATA", str(MODELS / "nltk_data"))

PROMPT = "Yitan, answer with exactly these words: phase one audio gate is alive."
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct")
BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
VOICE = os.getenv("KOKORO_VOICE", "af_heart")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resample(samples: np.ndarray, source_rate: int, target_rate: int = 16000) -> np.ndarray:
    if source_rate == target_rate:
        return samples.astype(np.float32)
    length = int(len(samples) * target_rate / source_rate)
    return np.interp(
        np.linspace(0, len(samples) - 1, length), np.arange(len(samples)), samples
    ).astype(np.float32)


def transcribe(transcriber: Transcriber, samples: np.ndarray, sample_rate: int) -> str:
    mono_16k = resample(samples, sample_rate)
    result = transcriber.transcribe_without_streaming(mono_16k.tolist(), 16000)
    return " ".join(line.text for line in result.lines).strip()


def main() -> None:
    OUT.mkdir(exist_ok=True)
    kokoro = Kokoro(
        str(MODELS / "kokoro" / "kokoro-v1.0.onnx"),
        str(MODELS / "kokoro" / "voices-v1.0.bin"),
    )
    model_path, architecture = get_model_for_language("en", string_to_model_arch("base"))
    moonshine = Transcriber(model_path, architecture)

    timings: dict[str, float] = {}

    started = time.perf_counter()
    prompt_audio, prompt_rate = kokoro.create(PROMPT, voice=VOICE, lang="en-us")
    timings["prompt_tts_seconds"] = time.perf_counter() - started
    prompt_path = OUT / "e2e_prompt.wav"
    sf.write(prompt_path, prompt_audio, prompt_rate)

    started = time.perf_counter()
    raw_transcript = transcribe(moonshine, prompt_audio, prompt_rate)
    timings["prompt_stt_seconds"] = time.perf_counter() - started

    started = time.perf_counter()
    client = OpenAI(base_url=BASE_URL, api_key="local-ollama-no-cloud-key")
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a local voice bench. Follow the user's exact response wording. "
                    "Return plain spoken text only."
                ),
            },
            {"role": "user", "content": raw_transcript},
        ],
        temperature=0,
    )
    answer = (completion.choices[0].message.content or "").strip()
    timings["ollama_seconds"] = time.perf_counter() - started

    started = time.perf_counter()
    answer_audio, answer_rate = kokoro.create(answer, voice=VOICE, lang="en-us")
    timings["answer_tts_seconds"] = time.perf_counter() - started
    answer_path = OUT / "e2e_answer.wav"
    sf.write(answer_path, answer_audio, answer_rate)

    started = time.perf_counter()
    heard_answer = transcribe(moonshine, answer_audio, answer_rate)
    timings["answer_stt_verification_seconds"] = time.perf_counter() - started

    expected_words = {"phase", "one", "audio", "gate", "is", "alive"}
    normalized_answer = heard_answer.lower().replace("1", "one")
    heard_words = {
        "".join(char for char in word if char.isalpha())
        for word in normalized_answer.split()
    }
    missing = sorted(expected_words - heard_words)
    passed = not missing

    receipt = {
        "classification": "PASS_MODEL_CHAIN_NOT_PHYSICAL_GATE" if passed else "FAIL",
        "physical_gate_claimed": False,
        "model": MODEL,
        "base_url": BASE_URL,
        "raw_prompt_transcript": raw_transcript,
        "ollama_answer": answer,
        "verified_answer_transcript": heard_answer,
        "missing_expected_words": missing,
        "timings_seconds": {key: round(value, 3) for key, value in timings.items()},
        "artifacts": {
            str(prompt_path.relative_to(ROOT)): {
                "bytes": prompt_path.stat().st_size,
                "sha256": sha256(prompt_path),
            },
            str(answer_path.relative_to(ROOT)): {
                "bytes": answer_path.stat().st_size,
                "sha256": sha256(answer_path),
            },
        },
        "boundaries": [
            "local Ollama only",
            "no cloud API keys",
            "no database wiring",
            "not a substitute for the real mic/speaker Gate 1 exchange",
        ],
    }
    receipt_path = OUT / "e2e_audio_turn_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
