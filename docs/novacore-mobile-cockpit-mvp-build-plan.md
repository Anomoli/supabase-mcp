# NovaCore Mobile Cockpit — MVP Build Plan (Phase 1)

This document translates the approved design spec into an executable implementation plan with concrete backlog items, data contracts, and acceptance criteria.

---

## 1) MVP Scope (Build Now)

Deliver the following end-to-end flow:

1. Chris opens installed PWA on Galaxy S24.
2. Home grid loads domain tiles from Supabase.
3. Chris opens a domain and sees summary + tasks + recent activity.
4. Chris speaks (or types) in persistent command bar.
5. Backend forwards input to OpenClaw gateway and returns response.
6. PWA renders response and speaks reply using browser TTS.

Out-of-scope for Phase 1:

- Geofence ingestion and confidence decay automation (Phase 2)
- LiveKit full-duplex realtime voice (Phase 2)
- People page and reminder automation (Phase 3)

---

## 2) Suggested Repository Layout

```text
novacore-cockpit/
  apps/
    cockpit-web/                 # React + Vite PWA
      src/
        pages/
          Home.tsx
          DomainDetail.tsx
          Briefing.tsx
        components/
          DomainTile.tsx
          VoiceTextBar.tsx
          HealthPanel.tsx
        lib/
          api.ts
          speech.ts
          supabase.ts
      public/
        manifest.webmanifest
        icons/
      vite.config.ts
  services/
    cockpit-api/                 # Express or FastAPI
      src/
        routes/
          domains.ts
          briefing.ts
          voice.ts
          tasker.ts
          context.ts
        services/
          openclaw.ts
          domains.ts
          context-score.ts
        index.ts
```

---

## 3) Delivery Backlog (5-Day Sprint)

## Day 1 — Foundation

- [ ] Scaffold `cockpit-web` (React + TypeScript + Vite)
- [ ] Configure PWA manifest + service worker (basic offline shell)
- [ ] Scaffold `cockpit-api` service
- [ ] Add env config (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `OPENCLOW_URL`)
- [ ] Add `/healthz` endpoint

## Day 2 — Domains + Briefing

- [ ] Implement `GET /api/domains`
- [ ] Implement `GET /api/domains/:id`
- [ ] Implement `GET /api/domains/:id/activity`
- [ ] Implement `GET /api/briefing`
- [ ] Build Home and Domain pages with loading/empty/error states

## Day 3 — Voice/Text Loop

- [ ] Implement persistent `VoiceTextBar`
- [ ] Add Web Speech API (speech-to-text)
- [ ] Add `POST /api/voice` and `POST /api/text`
- [ ] Forward requests to OpenClaw gateway with context payload
- [ ] Render + speak responses via `speechSynthesis`

## Day 4 — Stabilization

- [ ] Add briefing page and navigation polish
- [ ] Add request logging + basic rate limit on voice/text endpoints
- [ ] Add error telemetry events (Sentry or structured logs)
- [ ] Validate installability on Galaxy S24

## Day 5 — Deploy + Verify

- [ ] Nginx reverse proxy to cockpit web/api
- [ ] ngrok static domain + TLS validation
- [ ] Smoke test all core endpoints
- [ ] Run acceptance checklist on phone

---

## 4) API Contract Details

## `GET /api/domains`

**Response 200**

```json
[
  {
    "id": "finance",
    "name": "Finance",
    "icon": "bank",
    "unreadCount": 2,
    "urgent": true
  }
]
```

## `GET /api/domains/:id`

**Response 200**

```json
{
  "id": "finance",
  "name": "Finance",
  "icon": "bank",
  "confidence": 78,
  "summary": "HELOC documents received, awaiting signature.",
  "tasks": [
    {
      "id": "task_1",
      "title": "Review HELOC terms",
      "priority": "high",
      "dueAt": "2026-02-26T14:00:00Z"
    }
  ],
  "subdomains": [{ "id": "finance_tax", "name": "Tax" }]
}
```

## `GET /api/domains/:id/activity`

**Response 200**

```json
[
  {
    "id": "evt_123",
    "createdAt": "2026-02-25T15:34:00Z",
    "source": "rook",
    "text": "Called lender and confirmed timeline."
  }
]
```

## `POST /api/voice`

**Request body**

```json
{
  "transcript": "what's the status of the heloc",
  "context": { "page": "domain", "domainId": "finance" }
}
```

**Response 200**

```json
{
  "reply": "HELOC is in underwriting; signature requested by Friday.",
  "route": "finance",
  "confidence": 0.91
}
```

## `POST /api/text`

Same shape as `/api/voice`, with `text` instead of `transcript`.

## `GET /api/briefing`

**Response 200**

```json
{
  "date": "2026-02-26",
  "calendar": [
    {
      "title": "Cooper's Landing walkthrough",
      "start": "2026-02-26T13:00:00Z",
      "end": "2026-02-26T14:00:00Z"
    }
  ],
  "urgent": ["Approve wire transfer"],
  "overnight": ["Rook closed 2 open follow-ups"],
  "decisions": ["Choose lender package"],
  "weather": { "tempF": 28, "summary": "Light snow" }
}
```

---

## 5) Data Model Additions (Supabase)

## `domains` (existing, minimum fields)

- `id text primary key`
- `name text not null`
- `icon text`
- `parent_id text null references domains(id)`
- `sort_order int default 0`

## `domain_tasks`

- `id uuid primary key`
- `domain_id text references domains(id)`
- `title text not null`
- `priority text check (priority in ('low','med','high','urgent'))`
- `status text check (status in ('open','done')) default 'open'`
- `due_at timestamptz null`
- `created_at timestamptz default now()`

## `hot_layer_events`

- `id uuid primary key`
- `domain_id text references domains(id)`
- `source text not null`
- `content text not null`
- `created_at timestamptz default now()`

## `context_state`

- `id int primary key default 1`
- `score int not null default 70`
- `current_domain_id text null references domains(id)`
- `dnd boolean not null default false`
- `activity text null`
- `last_signal_at timestamptz default now()`

---

## 6) Acceptance Criteria (Definition of Done)

A build is Phase-1 complete when all criteria pass:

- [ ] PWA is installable on Galaxy S24 and opens full-screen.
- [ ] Home grid renders within 2 seconds on LTE after warm start.
- [ ] Domain detail page loads summary/tasks/activity without errors.
- [ ] Voice transcription succeeds in Chrome Android and can be retried on failure.
- [ ] Text fallback works in silent environments.
- [ ] API returns deterministic JSON shape matching this contract.
- [ ] Rook response is spoken aloud and visible in text transcript.
- [ ] ngrok HTTPS endpoint serves both web UI and API successfully.

---

## 7) Engineering Guardrails

- Keep voice-first UX: command bar must remain visible on every page.
- Prioritize resilience over polish for MVP (clear errors, retries, fallback to text).
- Avoid lock-in: keep OpenClaw integration behind one service adapter.
- Log every user interaction with timestamp + page context for debugging.
- Do not block render on optional data (weather/overnight summaries can degrade gracefully).

---

## 8) Immediate Next Step (Tonight)

If implementing right now, start in this order:

1. Bootstrap `cockpit-api` with `/api/domains` returning static mock data.
2. Build `cockpit-web` Home page that consumes `/api/domains`.
3. Add persistent `VoiceTextBar` with text submit first.
4. Wire `POST /api/text` to OpenClaw and display reply.
5. Add speech input and TTS once text round-trip is stable.

This yields a usable “talk to Rook from phone” loop on night one, then data depth can be layered in.
