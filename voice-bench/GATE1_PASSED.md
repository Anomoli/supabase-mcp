# VP-2 Gate 1 — PASS

**Date:** 2026-08-21  
**Surface:** Chris's phone browser over tailnet-only self-hosted LiveKit  
**Room:** `voice-bench`  
**Classification:** **PASS**

## Acceptance condition

Chris speaks from his own phone surface, the sovereign local pipeline transcribes and answers him, Chris hears the answer, and the completed exchange is captured through the governed write-only voice door.

## Proven path

`Chris phone microphone → self-hosted LiveKit → explicit Silero VAD → Moonshine STT → local Ollama qwen2.5:14b-instruct → Kokoro TTS → LiveKit → Chris phone speaker`

## Real spoken exchange

- Moonshine user transcript: `Hello there, can you do? Math problem of five plus five?`
- Local Ollama response: `Five plus five is ten.`
- Chris confirmed through Telegram immediately afterward: `Its working!`

Additional live exchanges followed, including `Excellent.`, `What model are you?`, and `Do you have a name?`, each producing a spoken response.

## Runtime evidence

- Silero emitted user speech start and stop events.
- Moonshine completed the real phone transcription.
- Ollama produced the answer locally.
- Kokoro generated the response and LiveKit output emitted bot-speaking start/stop events.
- Earlier duplex meter on the same phone path measured:
  - User input: 8,999 frames, peak RMS 17,537, 4,901 frames above RMS 100.
  - Bot output: 8,999 frames, peak RMS 7,828, 826 frames above RMS 100.
- Fresh browser join restored audible phone playback; no Hermes or LiveKit-server restart was required.

## Governed capture readback

The paired real exchange was read back from Wingman `hot_layer` after `voice_log_turn` completed:

- User row: `9cd7d761-2c15-4bc4-b95a-76225f613457`
- Assistant row: `053ea6d3-f50b-4737-84ba-054ce13f4dbc`
- Shared DB timestamp: `2026-08-21T20:24:26.490592+00:00`
- Source dye: `retell-voice`

The live runtime remains write-only with respect to Wingman. This readback was an external gate verification, not a database read introduced into the voice loop.

## Gate result

**PASS:** A genuine two-way phone-originated spoken exchange traversed the complete sovereign local model path, the answer was audible to Chris, and both sides were captured through the governed voice door.
