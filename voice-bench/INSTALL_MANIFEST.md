# VP-2 INSTALL_MANIFEST

Everything installed for the voice bench, when, and how big. All Python
packages live in `voice-bench/.venv`; all model weights in `voice-bench/models/`
(both gitignored). Nothing installed outside the repo except the two OS
packages listed. Timestamps UTC.

## 2026-08-21T16:30Z — build session (Claude cloud container, Ubuntu 24.04)

### OS packages (apt — the only installs outside the repo)
| package | version | why |
|---|---|---|
| espeak-ng | 1.51+dfsg-12build1 | phonemization fallback for Kokoro G2P |
| portaudio19-dev | 19.6.0-1.2build3 | build dep for PyAudio (mic/speaker I/O) |

On Windows (Gammy, if native per DECISIONS D-003): espeak-ng via its MSI
installer from the espeak-ng releases page; PyAudio ships prebuilt wheels, no
PortAudio install needed.

### Python packages (pip, in .venv — Python 3.11.15)
Direct dependencies (pinned in requirements.txt):
| package | version | size (installed, approx) | why |
|---|---|---|---|
| pipecat-ai[moonshine,kokoro,local,silero] | 1.7.0 | 30 MB | pipeline orchestrator; bundles Silero VAD + smart-turn ONNX models in the wheel |
| openai | 2.54.0 | 5 MB | client library pipecat uses to talk to the LOCAL Ollama endpoint (no OpenAI cloud, no key) |
| numpy | 2.4.6 | 45 MB | audio buffer math |
| soundfile | 0.14.0 | 2 MB | smoke test writes WAV evidence |

Notable transitive deps (from the extras): moonshine-voice 0.1.3 (Moonshine
ONNX runtime + libmoonshine.so), kokoro-onnx 0.6.1, onnxruntime 1.24.4 (53 MB),
PyAudio 0.2.14, espeakng-loader 0.2.4, phonemizer-fork 3.3.2. Full freeze:
123 packages, .venv ≈ 1.0 GB total.

History note: torch 2.13.0 + transformers 5.15.1 (~7 GB) were installed first
under the original plan (D-004), then fully removed when we found pipecat 1.7's
native ONNX services (D-006). They are NOT part of the bench.

### Models (in voice-bench/models/, downloaded on first use)
| model | file(s) | size | source | license | status |
|---|---|---|---|---|---|
| Kokoro-82M v1.0 (TTS) | kokoro/kokoro-v1.0.onnx | 326 MB | github.com/thewh1teagle/kokoro-onnx release model-files-v1.0 | Apache-2.0 | downloaded + verified 2026-08-21T16:36Z |
| Kokoro voices | kokoro/voices-v1.0.bin | 28 MB | same release | Apache-2.0 | downloaded + verified 2026-08-21T16:36Z |
| Moonshine base-en (STT) | moonshine/ (cache dir via MOONSHINE_VOICE_CACHE) | ~230 MB | download.moonshine.ai (fetched automatically by moonshine-voice) | English models: standard Moonshine license (non-English are non-commercial — stay on EN) | NOT yet downloaded — CDN blocked from build container; downloads on first run on Gammy |
| Silero VAD | (inside pipecat wheel) | 2 MB | bundled in pipecat-ai | MIT | verified 2026-08-21T16:36Z |

First run on a fresh box also fetches NLTK `punkt_tab` (a few MB, tokenizer
data used by moonshine-voice text handling); bot.py and the smoke test pin it
into `models/nltk_data` via the NLTK_DATA env var so it stays in the repo.

No cloud API keys anywhere; the only network use is one-time model downloads.

## 2026-08-21T18:05Z — phase 2 additions (same build session)

### Python packages (pip, in .venv)
| package | version | why |
|---|---|---|
| pipecat-ai[livekit] extra: livekit | 1.1.14 | LiveKit RTC client SDK (transport) |
| livekit-api | 1.2.0 | token minting for bot + client surfaces |
| livekit-protocol | 1.1.24 | transitive dep of the two above |

### Server (Docker image, runs on Gammy under Docker Desktop)
| image | version | size | why | license |
|---|---|---|---|---|
| livekit/livekit-server | v1.9 | ~60 MB pulled | self-hosted LiveKit for phase 2 rooms | Apache-2.0 |

Still no cloud services and no API keys: the LiveKit server is self-hosted, tokens are
signed locally with the shared dev secret in livekit/livekit.yaml (change it).
