# cockpit-web

Phase 1 NovaCore Mobile Cockpit front-end (React + Vite + PWA).

## Features

- Installable PWA (`vite-plugin-pwa`) with SVG-only PWA icons
- Domain grid home page
- Domain detail page
- Daily briefing page
- Persistent voice/text bar fixed at bottom on every page
- Voice input via Web Speech API + spoken replies via browser TTS
- Supabase domain fetch (`domains` table) with API/mock fallbacks

## Run locally

```bash
cd cockpit-web
npm install
npm run dev
```

Open `http://localhost:5173`.

## Configuration

Copy `.env.example` to `.env` and set values as needed:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_BASE_URL`

If Supabase keys are not set, the app uses API fallback and local mock data.

## Build

```bash
npm run build
npm run preview
```
