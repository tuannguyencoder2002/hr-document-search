# HR Document Search — Local RAG System

He thong hoi dap thong minh cho tai lieu nhan su, chay 100% local tren RTX 5060 (8GB VRAM).

## Tech Stack

- **LLM**: Ollama + Qwen3-8B (Q4_K_M)
- **Embedding**: BAAI/bge-m3 (dense + sparse)
- **Reranker**: BAAI/bge-reranker-v2-m3
- **Vector DB**: Qdrant (hybrid search)
- **Framework**: LlamaIndex / FastAPI / Chainlit

Chi tiet day du tai [PROJECT_PLAN.md](PROJECT_PLAN.md).

## Cau truc

```
src/
├── config.py           # Pydantic Settings
├── ingestion/          # parser, cleaner, chunker, indexer
├── search/             # embedder (bge-m3), retriever (hybrid+RRF), reranker
├── generation/         # Ollama LLM + prompt templates
├── api/                # FastAPI app + routes + schemas
└── utils/logger.py
app/chainlit_app.py     # Chainlit UI
.chainlit/config.toml   # UI theme (white, professional)
public/custom.css       # Custom styling
scripts/                # setup_qdrant, ingest_folder, reset_db
evaluation/evaluate.py  # Recall@K, MRR, Answer Accuracy
tests/                  # pytest unit tests
```

## Setup

### 1. Prerequisites

```bash
python --version   # >= 3.11
docker --version
# Ollama: https://ollama.com/download
ollama pull qwen3:8b
```

### 2. Start Qdrant

```bash
docker-compose up -d
curl http://localhost:6333/healthz
```

### 3. Python env

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

### 4. Init Qdrant collection

```bash
python -m scripts.setup_qdrant
```

## Chay

```bash
# Terminal 1: API
uvicorn src.api.main:app --reload --port 8000

# Terminal 2: UI (Chainlit)
chainlit run app/chainlit_app.py --port 7860
```

- UI:        http://localhost:7860
- API docs:  http://localhost:8000/docs

> Chainlit UI co the chay standalone (khong can FastAPI) vi no goi truc tiep pipeline embedder/retriever/reranker/LLM.
> Neu chi muon UI: `chainlit run app/chainlit_app.py`

## Ingest tai lieu

```bash
# Bo PDF/DOCX vao data/hr_docs/ roi:
python -m scripts.ingest_folder --folder data/hr_docs --doc-type handbook --department HR
```

## Test

```bash
# Unit tests (khong can Qdrant/Ollama)
pip install -r requirements-dev.txt
pytest tests/ -v

# Evaluation (can index va services chay)
python -m evaluation.evaluate --qa tests/fixtures/qa_pairs.json
```

## API endpoints

| Method | Path | Mo ta |
|--------|------|-------|
| POST | `/upload` | Upload + index file (PDF/DOCX/TXT) |
| POST | `/chat` | Hoi dap (search + rerank + generate) |
| GET  | `/search` | Search only |
| GET  | `/documents` | List tai lieu da index |
| DELETE | `/documents/{id}` | Xoa tai lieu |
| GET  | `/health` | Trang thai Qdrant + Ollama |

## License

MIT
