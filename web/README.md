# Document Search Assistant — Web UI

Next.js 14 + React 18 + Tailwind + shadcn-style components. Frontend-only;
the FastAPI backend (port 8000) handles all search / RAG / LLM streaming.

## Setup

```bash
cd web
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000.

The dev server proxies `/api/*` to `http://localhost:8000/*` (override via
`NEXT_PUBLIC_API_URL`).

## Architecture

- `app/page.tsx` — main chat page, manages message state + streaming.
- `components/chat-input.tsx` — pill-shaped input with Enter/Shift+Enter.
- `components/message-bubble.tsx` — renders user/assistant messages with
  inline PDF previews and per-source ✕ close buttons.
- `components/pdf-card.tsx` — one PDF viewer card (640px iframe, opens
  at the right page via `#page=N`).
- `components/typing-indicator.tsx` — bouncing dots while waiting.
- `lib/chat-client.ts` — SSE parser for `POST /api/chat/stream`.
- `lib/types.ts` — shared types with the FastAPI schemas.

## Required backend endpoints

- `POST /chat/stream` — SSE stream of `sources` → `delta` × N → `done`.
- `GET /file?path=...` — serves the original PDF for the iframe.

Both live in `src/api/routes.py` of the Python project.

## Build

```bash
npm run build
npm start
```
