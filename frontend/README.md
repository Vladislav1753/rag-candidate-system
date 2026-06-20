# signal — web frontend

A modern Next.js interface for the RAG candidate system. It replaces the former
Streamlit UI and talks to the existing FastAPI backend — no backend changes are
required.

- **Search** (`/`) — describe a role in plain language, expand it with AI, and
  get reranked candidates. Each card shows a **relevance meter** built from the
  match score the pipeline computes.
- **Onboard** (`/onboard`) — drop a PDF resume to auto-fill the form via
  `/cvs/extract`, edit, then save via `/candidates/onboarding`.

## Stack

Next.js 15 (App Router) · TypeScript · Tailwind CSS v4 · Space Grotesk + Space
Mono. Browser requests hit a same-origin `/api/*` path that a runtime Route
Handler (`src/app/api/[...path]/route.ts`) forwards to the backend, so there's
no CORS or mixed-content setup. The proxy reads `BACKEND_URL` per request, so
one image works in both Docker and local dev.

## Run with the stack (Docker)

It's a service in the root `docker-compose.yml`. From the project root:

```bash
docker compose up --build      # frontend on http://localhost:3000
```

The compose service sets `BACKEND_URL=http://backend:8000` so the `/api/*` proxy
reaches the backend over the compose network.

## Run standalone (local dev)

The backend (plus Postgres + Redis) must be reachable first. Then:

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000
```

If the backend is not on `http://localhost:8000`, point the proxy at it:

```bash
BACKEND_URL=http://my-host:8000 npm run dev
```

Copy `.env.example` to `.env.local` to set `BACKEND_URL` permanently.

## Production build

```bash
npm run build && npm start
```

## Layout

```
src/
  app/
    layout.tsx          root layout, fonts, nav
    page.tsx            search
    onboard/page.tsx    onboarding
    api/[...path]/route.ts  runtime proxy to the FastAPI backend
    globals.css         design tokens (cobalt on warm paper)
  components/         Nav, CandidateCard, RelevanceMeter, Field
  lib/                api client, types, formatting helpers
```
