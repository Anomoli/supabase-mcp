# NovaCore Mobile Cockpit — Design Spec v1.0

_Written: Feb 25, 2026 by Rook_  
_Status: APPROVED FOR BUILD — Chris green-lit Phase 1 tonight_

> Implementation companion: see `docs/novacore-mobile-cockpit-mvp-build-plan.md` for concrete sprint tasks, API payload contracts, and definition-of-done criteria.

---

## Vision

A voice-first PWA that serves as Chris's direct line to Rook and his entire life operating system. One app, always ready, phone in pocket — talk and the system handles the rest.

**Core principle:** You don't navigate to talk. You just talk. The app handles routing, context, and structure.

---

## Architecture

| Layer        | Technology                                          | Hosted            |
| ------------ | --------------------------------------------------- | ----------------- |
| Frontend     | React PWA (installable, offline-capable)            | Norbert via Nginx |
| Voice        | LiveKit WebRTC (Phase 2) / Web Speech API (Phase 1) | Norbert           |
| Backend API  | Express or FastAPI on Norbert                       | Norbert           |
| Database     | Supabase (existing NovaCore stack)                  | Cloud             |
| AI Layer     | OpenClaw Gateway → Rook                             | Norbert           |
| Sensor Layer | Tasker (Android) → webhooks to Norbert              | Phone → Norbert   |
| Access       | ngrok static domain or Tailscale                    | Norbert           |

**PWA** — bookmark to home screen, no app store. Served via HTTPS (ngrok provides this).

---

## UI Design

### Home Screen — Domain Grid

- **Samsung Galaxy-style tile grid** — 3-4 columns of domain tiles
- Each tile: icon + domain name + optional badge (unread count, urgent flag)
- Top-level domains from Supabase `domains` table (Meta, AI_Systems, Business, Life, etc.)
- Tap tile → drill into domain detail page
- Long-press tile → quick actions (add note, set reminder)
- Pull-down → refresh / daily briefing summary

### Domain Detail Page

- **Header:** Domain name + icon + confidence score (context awareness)
- **Summary card:** AI-generated summary of recent activity in this domain
- **Tasks:** Open items, ordered by priority
- **Subdomain tree:** Collapsible child domains
- **Recent activity feed:** Last 5-10 entries from hot_layer for this domain
- **Swipe left/right** → navigate between sibling domains

### Daily Briefing Page

- Morning dashboard view — one screen, everything you need
- Calendar (today + tomorrow)
- Urgent items across all domains
- What Rook handled overnight
- Decisions needed (items awaiting Chris's input)
- Weather snapshot

### People Page (Future)

- Contact cards with context
- Last conversation summary
- Pending items related to that person
- Quick call/text actions

---

## Persistent Voice/Text Bar

**Present on EVERY page.** Fixed at bottom of screen.

- **Mic button** — tap to talk (push-to-talk), or toggle for always-on
- **Text field** — tap to type (silent mode — job sites, meetings)
- **Context indicator** — shows current domain/page so you know what Rook sees
- **Send button** — submits text input

**Context awareness:** When you're on the Finance domain page and say "what's the status of the HELOC?" — Rook knows you're in Finance context. When you're on the home grid and say the same thing, Rook routes it to Finance automatically. Both work, but context makes responses sharper.

**Voice output:** Rook replies via TTS through the app speaker/earbuds. Conversation flows voice-to-voice.

---

## Context Awareness Agent

A background agent that maintains a real-time confidence score of Chris's current state.

### Confidence Score System

- **Score range:** 0-100
- **Threshold for ping:** Below 40 triggers a lightweight check-in
- **Decay rate:** Variable by time of day
  - Work hours (7:30 AM - 5:30 PM): Fast decay (~5 points/15 min without signal)
  - Evening (5:30 PM - 11 PM): Medium decay (~3 points/30 min)
  - Night (11 PM - 7:30 AM): Slow decay (~1 point/hour), DND mode
- **Signal sources that boost score:**
  - Location change (Tasker geofence) → +20
  - Voice/text input in cockpit → +30
  - Phone sensor data (screen on, app switch) → +10
  - Calendar event start/end → +15

### Ping Behavior

- Below 40: Soft check — push notification or gentle voice prompt
- Below 20: "Hey, haven't heard from you in a while. Everything good?"
- Score of 0: Something's wrong — escalate (text Vanessa? emergency?)
- **Never ping during DND/night unless score drops to 0**

### Data Sources (via Tasker)

- GPS location → geofence matching (job sites, home, etc.)
- Phone state (screen on/off, DND, battery)
- Bluetooth connections (truck, earbuds = driving/available)
- Notification stream (emails, texts, app alerts)
- Activity recognition (still, walking, driving, running)

---

## Tasker Integration

Tasker runs on the Galaxy S24 and pushes events to Norbert via HTTP.

### Webhook Endpoint

```http
POST https://novacore-chris.ngrok.app/api/tasker/event
Content-Type: application/json

{
  "event": "geofence_enter",
  "location": "coopers_landing",
  "timestamp": "2026-02-25T16:30:00Z",
  "meta": { "battery": 72, "wifi": false }
}
```

### Event Types

| Event               | Trigger                       | Score Impact                  |
| ------------------- | ----------------------------- | ----------------------------- |
| `geofence_enter`    | Arrive at known location      | +20, update location          |
| `geofence_exit`     | Leave known location          | +15, update location          |
| `screen_on`         | Phone unlocked                | +5                            |
| `screen_off`        | Phone locked                  | 0 (neutral)                   |
| `bluetooth_connect` | Paired device connected       | +10, infer activity           |
| `dnd_on`            | Do Not Disturb enabled        | Set DND flag                  |
| `dnd_off`           | Do Not Disturb disabled       | Clear DND flag                |
| `notification`      | Intercepted notification      | +5, log for context           |
| `battery_low`       | Battery < 15%                 | Flag, reduce non-urgent pings |
| `activity_change`   | Still/walking/driving/running | Update activity state         |

### Known Geofences (Initial Set)

- Home (Grand Rapids)
- Cooper's Landing (job site)
- Mason Manor
- Triplex
- Greenville property
- Land & Co office
- Bowling alley
- Dentist office
- _Add more as discovered in conversation_

---

## Phase Plan

### Phase 1 — MVP (This Week)

**Goal:** Something usable in Chris's hands ASAP

- [ ] React PWA shell with service worker (installable)
- [ ] Domain grid home screen (tiles from Supabase `domains` table)
- [ ] Domain detail page (summary + tasks + recent activity from hot_layer)
- [ ] Persistent voice/text bar using Web Speech API (browser STT)
- [ ] Voice input → OpenClaw gateway API → Rook response → TTS playback
- [ ] Basic daily briefing page (calendar + urgent items)
- [ ] Nginx config on Norbert + HTTPS via ngrok
- [ ] Bookmark to home screen on Galaxy S24

**Tech:** React + Vite, Supabase JS client, Web Speech API, OpenClaw webhook

### Phase 2 — Sensory Layer (Week 2)

- [ ] Tasker profiles + webhook tasks on Galaxy S24
- [ ] Event ingestion endpoint on Norbert
- [ ] Context awareness agent (confidence score + decay + ping logic)
- [ ] Geofence setup for known locations
- [ ] Push notifications via service worker
- [ ] LiveKit WebRTC integration (replace Web Speech API with real-time voice)

### Phase 3 — Full Cockpit (Week 3+)

- [ ] People page with contact context
- [ ] To-do / task management integrated with domains
- [ ] Internal calendar view (read/write to NCC)
- [ ] Reminder system (set via voice, delivered via push)
- [ ] Health data integration (if available from Samsung Health)
- [ ] Always-on voice mode (phone in pocket, earbuds, continuous conversation)
- [ ] Offline mode — queue inputs when no signal, sync when back

---

## API Endpoints (Phase 1)

| Method | Path                        | Purpose                                     |
| ------ | --------------------------- | ------------------------------------------- |
| GET    | `/api/domains`              | List top-level domains with icons           |
| GET    | `/api/domains/:id`          | Domain detail + subdomains                  |
| GET    | `/api/domains/:id/activity` | Recent hot_layer entries for domain         |
| GET    | `/api/briefing`             | Today's daily briefing data                 |
| POST   | `/api/voice`                | Send voice transcript to Rook, get response |
| POST   | `/api/text`                 | Send text input to Rook, get response       |
| POST   | `/api/tasker/event`         | Receive Tasker webhook events               |
| GET    | `/api/context`              | Current context awareness state + score     |

---

## Design Principles

1. **Voice is primary, visual is secondary.** The app works with your eyes closed.
2. **Zero navigation required.** Talk and the system routes.
3. **One-hand operable.** Big touch targets, thumb-reachable controls.
4. **Context-aware by default.** Rook always knows where you are in the app AND in the world.
5. **Sovereign.** All on Norbert. No third-party AI. No data leaving your infrastructure.
6. **Progressive.** Each phase adds capability without breaking what exists.

---

## System Health Panel (Watchdog Dashboard)

A mission-control status board visible in the cockpit. Every critical service listed with real-time health.

### Display Per Service

| Column            | Description                            |
| ----------------- | -------------------------------------- |
| Service Name      | e.g. "OpenClaw Gateway"                |
| Status Indicator  | 🟢 Green / 🟡 Yellow / 🔴 Red          |
| Last Heartbeat    | Timestamp of last check-in             |
| Time Since        | Live timer (e.g. "12s ago", "3m ago")  |
| Expected Interval | How often this service should check in |
| Action            | Manual restart button (future)         |

### Color Logic

- **🟢 Green:** Last heartbeat within expected interval
- **🟡 Yellow:** Last heartbeat > 75% of expected interval (approaching stale)
- **🔴 Red:** Last heartbeat > expected interval (presumed down, watchdog should restart)

### Monitored Services (Initial)

| Service              | Expected Interval | Health Check Method                  |
| -------------------- | ----------------- | ------------------------------------ |
| OpenClaw Gateway     | 30s               | HTTP health endpoint `:18789/health` |
| Watchtower           | 60s               | HTTP health endpoint `:8847/`        |
| Watchdog             | 5 min             | Writes timestamp file each run       |
| SearXNG (Docker)     | 5 min             | HTTP `:8888`                         |
| VAPI Bridge (Docker) | 5 min             | HTTP `:3142`                         |
| Context Agent        | 60s               | (Phase 2)                            |

### How the Watchdog Reports

The watchdog script (runs every 5 min) writes a JSON status file after each check:

```json
// C:\Users\cdion\.openclaw\watchdog-status.json
{
  "lastRun": "2026-02-25T16:50:00Z",
  "services": {
    "gateway": { "status": "green", "lastSeen": "2026-02-25T16:50:00Z" },
    "watchtower": { "status": "green", "lastSeen": "2026-02-25T16:49:58Z" },
    "searxng": { "status": "green", "lastSeen": "2026-02-25T16:50:01Z" }
  }
}
```

The cockpit reads this file (or a Supabase mirror) to render the health panel.

### Watchdog Watches Itself

The watchdog gets its own row. The cockpit checks the `lastRun` timestamp from the status file. If it's stale (>10 min), the watchdog row goes red — meaning nothing is watching anything. Chris can see this at a glance.

---

## Open Questions

- [ ] Icon set for domains — custom SVGs or emoji?
- [ ] Color scheme — dark mode default? Match Galaxy theme?
- [ ] Notification sound — custom Rook sound?
- [ ] Voice wake word? ("Hey Rook" to activate mic without touching phone?)
- [ ] Samsung Health API access — possible via Tasker plugin?

---

_This spec is alive. Update as we build and learn._
