# VP-2 Gammy SIP rollout plan

Status: **SCAFFOLD ONLY — NOT ACTIVATED**

## Goal

Route Twilio SIP into Gammy's self-hosted LiveKit room and the already-proven
Moonshine → local qwen → Kokoro worker, while preserving governed paired
`voice_log_turn` capture and leaving the Norbert legacy path untouched.

## Staged gates

1. **Non-disruptive scaffold**
   - Keep the resident browser Gate-1 Compose file unchanged.
   - Add a separate shared-Redis LiveKit/SIP topology.
   - Pin Redis and LiveKit SIP by tag and OCI index digest.
   - Keep credentials and phone numbers outside Git.
   - Validate Compose, image manifests, config shape, and secret hygiene without
     starting services.
2. **Public media design review**
   - Choose an explicit public SIP/RTP route for Gammy. Tailscale Serve is not a
     public UDP relay and cannot by itself carry Twilio SIP/RTP.
   - Read-only discovery on 2026-08-21 found an Internet Gateway Device via
     UPnP, and its reported WAN IPv4 matched an independent external lookup.
     This removes CGNAT as the immediate blocker and makes a bounded future
     port-map plausible; no mapping was created by the discovery.
   - Bind the reviewed public/NAT address before activation; `use_external_ip`
     stays false in the scaffold so an unreviewed address cannot be advertised.
   - Review Windows Docker Desktop UDP behavior for SIP 5060 and the bounded RTP
     range 10000–10020. Expand only if measured call concurrency requires it.
3. **Custody and relight approval**
   - Receive Twilio trunk credentials by governed external secret custody; never
     place values in room/chat/repo/logs.
   - Obtain a narrow window to replace the resident non-Redis LiveKit container
     with the shared-Redis topology. Preserve a rollback command and do not touch
     Norbert.
4. **Activation and health proof**
   - Bring up Redis, LiveKit, and SIP only in the approved window.
   - Verify Redis health, LiveKit room join, SIP health endpoint, worker residency,
     and browser regression before creating trunk/dispatch resources.
5. **Chris-owned-number call gate**
   - Configure the minimum trunk and dispatch mapping to `voice-bench`.
   - Enforce status tracking plus a hard timeout/hangup guard.
   - Place only an authorized Chris-owned-number test.
   - Require route provenance, real spoken STT/model/TTS evidence, audible reply,
     and paired capture readback before declaring PSTN PASS.

## Rollback boundary

If shared Redis, LiveKit, SIP health, room join, or browser regression fails,
stop the replacement topology and restore the original `docker-compose.yml`
LiveKit service. Do not route the test through Norbert and label it VP-2.
