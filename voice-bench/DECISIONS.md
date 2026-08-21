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

## D-007 · 2026-08-21 · Yitan resumed driving; his Gammy repo is phase-1 repo of record

**Context.** Yitan posted CLAIM_PROGRESS at 17:08Z (agent_chat 74ed24a5): VP-2 built and
running on Gammy in his own repo `C:/Users/cdion/vp-2-voice-bench` (branch
vp2/phase1-gammy, commit fc0a23d), 7/7 smoke PASS including a deterministic
Moonshine→Ollama(qwen2.5:14b)→Kokoro→Moonshine chain. This also confirms D-003's
assumptions: Gammy is Windows and the native-Python path works. Physical mic→speaker
gate still open — his mic routing produced no pickup.

**Call.** Per the swap protocol, Fable is navigator again; Yitan drives. Two parallel
implementations exist (this branch's `voice-bench/` and his on-box repo). Proposed in
the room (35bcdc00): HIS repo is the phase-1 repo of record — it is on the hardware and
further along the gate; this branch stays as reviewed reference to cherry-pick from.
Navigator asks pending with Yitan: push his branch somewhere reviewable, and record the
repo-of-record call + on-Gammy path in his DECISIONS.md.

## D-008 · 2026-08-21 · Gate 1 redefined by Chris; LiveKit path promoted — Fable drives reference again

**Context.** At 17:30:59Z (agent_chat 715f578f) Chris, via voice relay, redefined Gate 1:
a real two-way spoken exchange with CHRIS from one of HIS surfaces (phone/NovaCore app
first, Twilio SIP later, desk press-to-talk as fallback) — not a human at Gammy's desk
mic. Desk-mic debugging is demoted to sanity check; self-hosted LiveKit (originally
phase 2) is now the priority path. At 17:55:59Z Rook flagged HANDOFF_OVERDUE: no Yitan
progress since the redefinition. Per the pair protocol, Fable drives reference work again.

**Call.** Built on this branch, verified as far as this container allows:
- `src/bot_livekit.py` — same sovereign pipeline over `LiveKitTransport`; bot mints its
  own room token; greets on first participant join. Imports verified; JWT minting
  verified. Needs a live LiveKit server + Ollama to run, i.e. Gammy.
- `livekit/docker-compose.yml` + `livekit/livekit.yaml` — self-hosted LiveKit v1.9
  (Apache-2.0) for Docker Desktop on Gammy; LAN-only defaults (no cloud STUN/TURN),
  dev key with a change-me 34-byte secret.
- `scripts/livekit_token.py` — mints client tokens for Chris's surfaces; prints a
  LiveKit Meet URL for a quick phone-browser test (client UI only; media stays LAN).

**Recorded conflict, deliberately NOT implemented here.** The redefinition also orders
every turn captured "through watchtower into the hot layer" — but the original written
work order says "do NOT wire anything to the DB in this phase," and watchtower/hot-layer
is Gammy-side NovaCore infra this container knows nothing about. Both positions stand in
the log per protocol; the capture wiring belongs to the driver on Gammy under Chris's
confirmation of which instruction now controls. Nothing in this branch touches any DB.

## D-009 · 2026-08-21 · GATE 1 PASSED; driver swap for phase 3

**Context.** 20:24Z on Gammy: Chris spoke from his phone browser over tailnet-only
self-hosted LiveKit; Moonshine transcribed, qwen2.5:14b answered ("Five plus five is
ten."), Kokoro spoke it back; both turns written through voice_log_turn. Yitan applied
the review fix (merge segmented user turns instead of raising) in 570de48 with
GATE1_PASSED.md. Verified three ways: Yitan's runtime evidence, Rook's DB check, and
Fable's independent hot_layer readback (rows 9cd7d761/053ea6d3, paired, dyed).

**Call.** Phase gate reached → driver/navigator swap per protocol. Proposed in room
(2d79d9ce): Fable drives the phase 3 reference on this branch (Superwhisper S1-mini
GGUF cleanup AFTER STT; raw and cleaned stored separately, raw never overwritten);
Yitan owns remaining phase-2 surfaces (NovaCore app client; Twilio SIP held until
Chris authorizes charged calls). Review note logged for later surfaces: the LiveKit
data-channel text bridge accepts typed input from any room participant — fine while
rooms are private-token-only, revisit before SIP participants join.

## D-010 · 2026-08-21 · Twilio authorized; legacy-call provenance lesson; SIP scaffold approved

**Context.** Chris authorized charged Twilio TEST calls (Chris-owned numbers only,
creds outside git, capture applies). Rook's 21:43Z test call reached Chris but rode the
LEGACY Norbert/OpenClaw/XAI path while announcing itself as "the V2 pipeline" — Chris
ruled it does NOT count as a VP-2 phone gate and set the build target: Twilio SIP →
Gammy LiveKit → sovereign loop → voice_log_turn, leaving Norbert untouched as the
independent fallback ring. Yitan scaffolded the bridge at 8116169 (shared-Redis
LiveKit+SIP replacement topology, digest-pinned, external secrets, no-start validator).

**Provenance lesson (marble, per Chris):** a call must announce the pipeline it
actually is. Surfaces get labeled by their real path, and a gate claim requires the
claimed path's provenance — capture rows alone don't prove which pipeline ran.

**Call (room 1af31176).** Scaffold APPROVED with conditions: (1) inbound 5060 and RTP
firewalled to Twilio's published signaling/media CIDRs, never 0.0.0.0/0 — public SIP
ports are scanner-found in minutes; (2) manual router port-forward, not UPnP-created;
(3) trunk objects created with IP ACL + number restriction + dispatch pinned to the
voice-bench room. Custody: Fable holds no Twilio secrets and moves none through
room/DB/git — handoff is Chris writing the env file on Gammy directly (preferred) or a
Rook seat-to-seat encrypted transfer; the room only ever sees presence-not-values.
Relight window approved in principle; Chris picks the moment since it briefly drops the
browser surface.
