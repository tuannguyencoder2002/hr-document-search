# Document Search Assistant

He thong RAG tim kiem + hoi dap tren tai lieu hoc tap, chay 100% local.
Backend Python (FastAPI + Qdrant + Ollama), UI Next.js 14.

## Tech stack

| Tang | Cong nghe |
|------|-----------|
| LLM | Ollama + Qwen3-4B (hoac 8B) |
| Embedding | BAAI/bge-m3 (dense 1024-d + sparse) |
| Reranker | BAAI/bge-reranker-v2-m3 |
| Image search | CLIP ViT-B/32 (multilingual text + image) |
| Vector DB | Qdrant (hybrid search, local embedded) |
| Backend | FastAPI + SSE streaming |
| UI | Next.js 14 + Tailwind + shadcn-style components |

## Cau truc

```
src/                      # Python backend
├── config.py             # Pydantic Settings
├── ingestion/            # parser, cleaner, chunker, indexer, manifest
├── search/               # embedder (bge-m3), retriever (hybrid+RRF),
│                         # reranker, clip_embedder, image_retriever
├── generation/           # Ollama LLM + prompt + intent shortcut
├── api/                  # FastAPI app + routes + schemas
├── utils/                # logger, ollama_health
└── hf_offline.py         # HF Hub hygiene (telemetry off)
web/                      # Next.js 14 frontend
├── app/page.tsx          # Main chat page
├── components/           # Header, MessageBubble, PdfCard, ChatInput...
└── lib/chat-client.ts    # SSE parser for /chat/stream
scripts/                  # setup_qdrant, ingest_folder, reset_db,
│                         # fix_ollama_gpu
evaluation/               # Recall@K, MRR, Answer Accuracy
tests/                    # pytest unit tests
```

## Setup

### 1. Prerequisites

```bash
python --version   # >= 3.11
node --version     # >= 18
# Ollama: https://ollama.com/download
ollama pull qwen3:4b
```

### 2. Qdrant (mode local, khong can Docker)

Mac dinh `QDRANT_MODE=local` trong `.env`, du lieu vector nam trong
`./qdrant_data/`. Neu muon chay qua Docker, `docker compose up -d`.

### 3. Python env

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# hoac: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # Windows (hoac cp tren linux/mac)
```

### 4. Ingest tai lieu

```bash
# Bo PDF / DOCX vao data/corpus/, sau do:
python -m scripts.ingest_folder --folder data/corpus
```

Lan thu 2 tro di, script incremental: chi embed cac file moi / da thay doi.

### 5. Fix Ollama GPU (1 lan duy nhat)

```bash
scripts\fix_ollama_gpu.bat
```

Set cac env var he thong (`OLLAMA_NUM_GPU=99`, `OLLAMA_FLASH_ATTENTION=1`),
restart Ollama, pre-load model. Sau do `ollama ps` phai thay 100% GPU.

## Chay

Mo 2 terminal:

```bash
# Terminal 1: API (port 8000)
3_run_api.bat
# tuong duong: uvicorn src.api.main:app --reload --port 8000
```

```bash
# Terminal 2: UI (port 3000)
5_run_web.bat
# tuong duong: cd web && npm install && npm run dev
```

- UI:       http://localhost:3000
- API docs: http://localhost:8000/docs

## API endpoints

| Method | Path | Mo ta |
|--------|------|-------|
| POST | `/upload` | Upload + index 1 file |
| POST | `/chat` | Hoi dap blocking (tra ve JSON day du) |
| POST | `/chat/stream` | **SSE streaming** — frontend Next.js dung cai nay |
| GET  | `/search` | Search only (khong sinh cau tra loi) |
| GET  | `/file?path=...` | Serve PDF cho iframe viewer |
| GET  | `/documents` | List tai lieu da index |
| DELETE | `/documents/{id}` | Xoa tai lieu |
| GET  | `/health` | Trang thai Qdrant + Ollama |

## Test

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Evaluation pipeline:

```bash
python -m evaluation.evaluate --qa tests/fixtures/qa_pairs.json
```

## Tai lieu lien quan

- [PROJECT_PLAN.md](PROJECT_PLAN.md) — ke hoach goc + tech choices
- [PIPELINE.md](PIPELINE.md) — luu do Mermaid ingestion + search + generation
- [web/README.md](web/README.md) — chi tiet frontend

## License

MIT
