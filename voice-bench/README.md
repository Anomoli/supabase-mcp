# voice-bench — VP-2 sovereign voice loop

Local, fully offline voice assistant bench. Phase 1:

    mic → Silero VAD → Moonshine STT → Ollama (local LLM) → Kokoro TTS → speaker

Everything runs on CPU via ONNX except the LLM, which is the machine's existing
Ollama endpoint (GPU stays dedicated to it). No cloud APIs, no keys, anywhere.
Read `DECISIONS.md` for the why behind every choice, `INSTALL_MANIFEST.md` for
exactly what gets installed.

## Setup (Gammy)

Per DECISIONS D-003: on Windows use **native** Python 3.11+ (not WSL2), plus
[espeak-ng](https://github.com/espeak-ng/espeak-ng/releases) installed once.
On Linux: `apt install espeak-ng portaudio19-dev`.

```
cd voice-bench
python -m venv .venv
.venv\Scripts\activate          # Windows   (Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

## Verify components (no mic needed)

```
python scripts/smoke_test.py
```

First run downloads Kokoro (~354 MB, into `models/kokoro/`) and Moonshine
(~230 MB, into `models/moonshine/`). Expect every section PASS when Ollama is
up; `out/kokoro_smoke.wav` is the synthesized evidence, and the
`stt-tts-roundtrip` section proves Moonshine can hear what Kokoro says.

## Run the loop (the phase-1 gate)

```
ollama list                      # confirm a model; default expected: llama3.1:8b
python src/bot.py
```

Speak; the bot answers out loud. One coherent spoken exchange = gate passed —
then write `GATE1_PASSED.md` (what works + how you verified) per the ticket.

Env overrides: `OLLAMA_BASE_URL` (default `http://localhost:11434/v1`),
`OLLAMA_MODEL`, `MOONSHINE_MODEL` (default `base`; keep English models — see
license note in INSTALL_MANIFEST), `KOKORO_VOICE` (default `af_heart`).

## Status

- [x] Scaffold + component verification (cloud container, 2026-08-21): Kokoro
      TTS, Silero VAD, VAD-on-real-speech, pipeline graph all PASS; Moonshine
      download and Ollama check SKIP there (network policy / no Ollama) and
      complete on Gammy.
- [ ] Phase 1 gate: live mic↔speaker exchange on Gammy → `GATE1_PASSED.md`
- [ ] Phase 2: self-hosted LiveKit transport
- [ ] Phase 3: Superwhisper S1-mini transcript cleanup (raw kept separately)
