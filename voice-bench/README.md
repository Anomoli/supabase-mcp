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
scripts\\run_smoke.cmd
```

First run downloads Kokoro (~354 MB, into `models/kokoro/`) and Moonshine
(~230 MB, into `models/moonshine/`). Expect every section PASS when Ollama is
up; `out/kokoro_smoke.wav` is the synthesized evidence, and the
`stt-tts-roundtrip` section proves Moonshine can hear what Kokoro says.

## Run the loop (the phase-1 gate)

```
ollama list                      # confirm qwen2.5:14b-instruct is available
scripts\\run_bot.cmd
```

Speak; the bot answers out loud. One coherent spoken exchange = gate passed —
then write `GATE1_PASSED.md` (what works + how you verified) per the ticket.

Env overrides: `OLLAMA_BASE_URL` (default `http://localhost:11434/v1`),
`OLLAMA_MODEL` (default `qwen2.5:14b-instruct`), `MOONSHINE_MODEL` (default
`base`; keep English models — see
license note in INSTALL_MANIFEST), `KOKORO_VOICE` (default `af_heart`).
Optional `AUDIO_INPUT_DEVICE_INDEX` and `AUDIO_OUTPUT_DEVICE_INDEX` values pin
specific PortAudio endpoints. The Windows launchers clear inherited
`PYTHONPATH` and keep caches inside the repository.

For a deterministic full local model-chain turn without physical audio devices:

```
scripts/run_e2e.cmd
```

This writes WAVs and `out/e2e_audio_turn_receipt.json`; it does not substitute
for the physical mic/speaker gate.

## Self-hosted LiveKit phone path

```
python scripts/configure_livekit.py
cd livekit && docker compose --env-file "%USERPROFILE%\.novacore\secrets\vp2-livekit.env" up -d && cd ..
scripts/run_livekit_bot.cmd
scripts/mint_livekit_token.cmd chris
```

Credentials live outside the repository at
`%USERPROFILE%\.novacore\secrets\vp2-livekit.env` (override with
`VP2_LIVEKIT_ENV_FILE`). The configuration advertises Gammy's Tailscale IP for
RTC; Tailscale Serve provides tailnet-only WSS. The bot requires Wingman write
credentials in its process environment and sends each completed paired exchange
through `voice_log_turn`; it has no DB read path.

## Status

- [x] Scaffold + component verification (cloud container, 2026-08-21): Kokoro
      TTS, Silero VAD, VAD-on-real-speech, pipeline graph all PASS; Moonshine
      download and Ollama check SKIP there (network policy / no Ollama) and
      complete on Gammy.
- [ ] Phase 1 gate: live mic↔speaker exchange on Gammy → `GATE1_PASSED.md`
- [x] Self-hosted LiveKit server + sovereign bot + authenticated WSS join/greeting
      verified on Gammy; narrow governed transcript capture approved and wired;
      final Chris phone exchange pending
- [ ] Phase 3: Superwhisper S1-mini transcript cleanup (raw kept separately)
