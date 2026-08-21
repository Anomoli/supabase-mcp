# VP-2 voice-bench — DECISIONS

Ticket: VP-2 (sovereign voice bench). Work order: agent_chat row `e28d14d8-76f9-45a5-a727-c7608a02ce05`.
Pair: Yitan (resident on Gammy) + Fable (this session). Protocol: one driver at a time, swap at phase gates.

Format per entry: context → positions considered → call → reasoning. Newest last.

---

## D-001 · 2026-08-21 · Where is this session running, and who drives?

**Context.** The ticket says "check the OS first." This session turned out NOT to be on
Gammy: it is a Claude Code cloud container — Ubuntu 24.04, 4-core Intel Xeon, 15 GB RAM,
no NVIDIA GPU, no `/dev/snd` audio devices, no Ollama on `localhost:11434`, no
`~/novacore`. Meanwhile agent_chat shows Yitan claimed VP-2 at 16:12 UTC and Rook posted
`HANDOFF_OVERDUE` at 16:18 UTC with no evidence produced.

**Positions.**
1. Wait for Yitan to produce evidence, navigate only. — Rejected: the pairing protocol
   says the second mind drives solo when the resident driver has stalled.
2. Drive solo from this container as far as physics allows. — Chosen.

**Call.** Fable drives phase 1 solo from the cloud container. Everything that is CPU-only
and headless gets built AND verified here (component level: STT/TTS/VAD on real WAV
files). The mic↔speaker gate demo can only happen on Gammy — this container has no audio
hardware — so GATE1_PASSED.md will NOT be written from here. Yitan (or Chris) pulls the
branch on Gammy and runs the gate.

## D-002 · 2026-08-21 · Repo location: designated branch, not ~/novacore (yet)

**Context.** Ticket says repo lives at `~/novacore/voice-bench`. This container is
ephemeral — anything not pushed dies with it — and the only push target this session has
is `anomoli/supabase-mcp`, branch `claude/vp2-sovereign-voice-bench-gh7n42`.

**Call.** Build in `voice-bench/` inside that repo on that branch. On Gammy, deploy with:

    git clone <anomoli/supabase-mcp> --branch claude/vp2-sovereign-voice-bench-gh7n42 ~/novacore/voice-bench-src
    # or pull the branch in an existing clone; the bench itself is the voice-bench/ subdir

Record the final on-Gammy path here when it lands. The ticket's "git init before first
file" is satisfied in spirit: the tree is under git before any bench file exists, and the
first bench commit is this DECISIONS.md. "Touch nothing outside the repo" holds — all
deps go in `voice-bench/.venv`, all models in `voice-bench/models/` (both gitignored).

## D-003 · 2026-08-21 · Windows: WSL2 vs native (pre-made call, confirm on Gammy)

**Context.** Gammy is an HP Omen and most likely runs Windows 11. The ticket requires
this call recorded before installing anything there. Made off-box; whoever drives on
Gammy confirms the OS and either ratifies or overturns with reasoning added here.

**Positions.**
1. **WSL2**: Linux tooling parity with this scaffold, easier Docker for LiveKit in
   phase 2. But: WSL2 audio goes through WSLg/PulseAudio passthrough, which is exactly
   the fragile, added-latency path for the one thing phase 1 must prove — a full-duplex
   mic↔speaker loop. GPU isn't needed for this stack (all CPU by design), so WSL2's GPU
   story buys nothing here.
2. **Native Windows Python**: PyAudio/PortAudio talk to WASAPI directly — the reliable
   audio path. Every phase-1 dep (Pipecat, Moonshine via transformers, Kokoro, Silero
   ONNX, torch-CPU) ships Windows wheels. Ollama already runs natively on Gammy.
   LiveKit in phase 2 can still be a Docker Desktop container while the agent stays
   native — transport is a network hop either way.

**Call.** Native Windows (Python 3.11+ venv) if Gammy is Windows. Reasoning: phase 1's
gate is audio I/O reliability; native wins there, and nothing in the stack needs Linux.
If Gammy turns out to already run Linux, this scaffold runs as-is and D-003 is moot.

## D-004 · 2026-08-21 · Moonshine via transformers; Kokoro via kokoro pip package

**Context.** Pipecat has no built-in local Moonshine or local Kokoro service (its Kokoro
integration talks to a remote websocket, which would violate "sovereign only" if pointed
at a cloud host and doesn't exist locally anyway).

**Call.** Two thin custom services in `src/services/`:
- `moonshine_stt.py` — wraps `UsefulSensors/moonshine-base` through `transformers`
  (supported since transformers 4.48). Segmented STT: VAD hands it a finished utterance,
  it transcribes the whole segment. CPU-friendly, no cloud.
- `kokoro_tts.py` — wraps `hexgrad/Kokoro-82M` through the `kokoro` package (KPipeline).
  82M params, real-time-or-better on CPU. Needs `espeak-ng` on the OS for fallback
  phonemization (on Windows: the espeak-ng installer; recorded in INSTALL_MANIFEST).
Both models are Apache/MIT-licensed open weights pulled from Hugging Face once, then
cached in `voice-bench/models/` — no keys, no cloud calls at runtime.

## D-005 · 2026-08-21 · LLM endpoint is configuration, not code

**Call.** The bot reads `OLLAMA_BASE_URL` (default `http://localhost:11434/v1`) and
`OLLAMA_MODEL` (default `llama3.1:8b` — swap for whatever Gammy actually serves, check
with `ollama list`). No API keys anywhere; Pipecat's OLLamaLLMService uses the
OpenAI-compatible surface of the local endpoint with a dummy key internally. The
component smoke test SKIPs its Ollama section when the endpoint is down; the full
loop requires it.

## D-006 · 2026-08-21 · REVISES D-004: use pipecat 1.7's native local services

**Context.** D-004 assumed pipecat had no local Moonshine/Kokoro and planned custom
wrappers over transformers+torch (~7 GB of deps). Reading the installed pipecat 1.7.0
source showed both exist natively and are exactly the sovereign shape we want:
`MoonshineSTTService` (moonshine-voice, ONNX, CPU) and `KokoroTTSService` (kokoro-onnx).

**Call.** Drop the custom services and torch entirely; use pipecat's own. Consequences:
- venv shrinks from ~8 GB to ~1 GB; zero custom inference code to maintain.
- Models stay repo-local: Kokoro via explicit `model_path`/`voices_path` args,
  Moonshine via the `MOONSHINE_VOICE_CACHE` env var, NLTK data via `NLTK_DATA`.
- License check: English Moonshine models use the standard license; non-English ones
  are non-commercial Community License. Bot pins `language=EN`; stay on English models.
- Verified on this container 2026-08-21T16:37Z: Kokoro synthesized real speech
  (out/kokoro_smoke.wav), Silero detected it as speech (full QUIET→STARTING→SPEAKING→
  STOPPING cycle), pipeline graph builds. Moonshine could not be verified here —
  download.moonshine.ai is blocked by the container's network policy — so the
  stt-tts-roundtrip smoke section runs first on Gammy.

## D-007 · 2026-08-21 · Gammy execution target confirmed

**Observed on Gammy.** Windows 10 build 26200, Python 3.11.15, native headset
microphone and speaker devices, FFmpeg, UV, and Ollama are present. Ollama serves
`qwen2.5:14b-instruct`, `qwen2.5:32b-instruct`, `gemma4:26b`, and
`nomic-embed-text`; it does not serve the scaffold's placeholder `llama3.1:8b`.

**Call.** Ratify D-003: use native Windows audio. Default the bench to
`qwen2.5:14b-instruct` for the Phase-1 gate. Keep UV, pip, and XDG caches inside
the repo during installation so dependency downloads do not escape the ticket's
custody boundary.

## D-008 · 2026-08-21 · Gate 1 redefined around Chris's phone surface

**Controlling order.** Agent-room row `715f578f-6f3d-4a53-97f7-aee9e250512d`
redefines Gate 1 as a real two-way exchange with Chris from one of his own
surfaces. Desk-mic work is demoted to a sanity check; self-hosted LiveKit is the
priority path. Fable delivered reference commit `901c766`; Rook accepted the
direction and kept the ball with Yitan on Gammy.

**Call.** Import and harden the LiveKit reference in this repo of record. Replace
the committed change-me secret with generated credentials in gitignored
`livekit/.env`; fail closed when credentials are absent. Advertise Gammy's
Tailscale IP for RTC and use tailnet-only Tailscale Serve for valid WSS. No public
Funnel, no cloud STUN/TURN, no gateway restart, and no DB wiring in this commit.
The later capture requirement conflicts with the original no-DB boundary; per
Rook row `65ca2f51-12c8-4b98-a3e8-6f06a2905911`, capture wiring waits for Chris's
explicit exception approval.

**Verified.** LiveKit server 1.9.12 advertised `100.107.140.13`; HTTPS/WSS at
`gammy.tailad773b.ts.net:7880` returned 200 with a valid certificate. An
authenticated held probe joined `voice-bench`, saw `vp2-bot`, triggered the
participant callback, and received a Kokoro greeting generated in 0.67 seconds.
