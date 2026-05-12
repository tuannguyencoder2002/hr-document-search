# PIPELINE — Document Search Assistant

Tài liệu mô tả **chi tiết lưu đồ xử lý** của hệ thống RAG tìm kiếm tài liệu.
Sơ đồ dùng [Mermaid](https://mermaid.js.org/) — GitHub / VS Code preview render trực tiếp.

---

## 1. Kiến trúc tổng quan

```mermaid
flowchart TB
    User((👤 Người dùng))

    subgraph UI["Next.js 14 :3000"]
      Chat[💬 Chat + Streaming]
      ImgSearch[� Image Search]
      DocView[� Inline PDF/DOCX Viewer]
    end

    subgraph API["FastAPI :8000"]
      Stream["POST /chat/stream (SSE)"]
      ImgAPI["POST /image-search"]
      FileAPI["GET /file · /preview · /open-file"]
      Upload["POST /upload"]
      Search["GET /search"]
      Health["GET /health"]
    end

    subgraph Models["In-process Python (GPU)"]
      BGE[["bge-m3\ndense 1024-d + sparse"]]
      RR[["bge-reranker-v2-m3\ncross-encoder"]]
      CLIP[["CLIP ViT-B/32\nimage + text 512-d"]]
    end

    subgraph Services["Local Services"]
      Qdrant[("🧭 Qdrant (embedded)\nhr_documents\nhr_images")]
      Ollama[("🧠 Ollama\nQwen3-4B · GPU 100%")]
    end

    User --> UI
    UI -->|HTTP / SSE| API
    Stream --> BGE --> Qdrant
    Stream --> RR
    Stream --> Ollama
    ImgAPI --> CLIP --> Qdrant
    Upload --> BGE --> Qdrant
    Upload --> CLIP --> Qdrant
    FileAPI --> User
```

---

## 2. Luồng Ingestion (POST /upload hoặc scripts/ingest_folder.py)

```mermaid
flowchart TD
    A[User thêm file vào data/corpus/] --> B{Validate\nextension + size ≤ 50MB}
    B -- "❌" --> Err[400 / 413]
    B -- "✅" --> C[parse_file]

    C -->|PDF| C1[PyMuPDF\nper-page text + images]
    C -->|DOCX| C2[python-docx\nparagraphs + tables + images]
    C -->|TXT/MD| C3[read utf-8]

    C1 --> D[List ParsedDocument]
    C2 --> D
    C3 --> D

    D --> E[clean_text\nNFC + strip ctrl + collapse ws]
    E --> F[chunk_documents\nRecursiveCharacterTextSplitter\nchunk_size=512, overlap=128]
    F --> G[List Chunk + metadata]

    G --> H[bge-m3 encode_batch]
    H --> H1[dense 1024-d L2-normalized]
    H --> H2[sparse token_id → weight]
    H1 --> I[Qdrant upsert\ncollection: hr_documents]
    H2 --> I

    C1 --> J[extract_images\nfilter < 80x80px]
    C2 --> J
    J --> K[CLIP ViT-B/32 encode_image]
    K --> L[Qdrant upsert\ncollection: hr_images]

    I --> M[Return summary\ndocument_id, chunks, images]
    L --> M
```

### Incremental Ingest (Manifest)

```mermaid
flowchart LR
    File[file.pdf] --> Hash[SHA256]
    Hash --> Check{manifest\nhas same hash?}
    Check -- yes --> Skip[Skip ✓]
    Check -- no/new --> Ingest[Full ingest]
    Ingest --> Update[Update manifest]
    Check -- hash changed --> Delete[Delete old chunks]
    Delete --> Ingest
```

---

## 3. Luồng Search + Generation (POST /chat/stream)

```mermaid
flowchart TD
    Q["Query: 'Cấu trúc bài thi VSTEP?'"] --> Intent{Intent\ndetection}
    Intent -- greeting/thanks --> Quick["Trả lời template\n(skip RAG)"]
    Intent -- rag --> E1

    E1[bge-m3 encode query] --> E1a[q_dense 1024-d]
    E1[bge-m3 encode query] --> E1b[q_sparse]

    E1a --> S[Qdrant query_batch_points]
    E1b --> S
    S --> S1[dense.search top-30]
    S --> S2[sparse.search top-30]

    S1 --> RRF["RRF fusion\nscore = Σ 1/(k+rank+1)\nk=60"]
    S2 --> RRF
    RRF --> R30[Top 30 fused chunks]

    R30 --> RR[bge-reranker-v2-m3\ncross-encoder score]
    RR --> R5[Top 5 reranked]

    R5 --> Filter{score ≥ 0.35?}
    Filter -- all below --> NoInfo["'Không tìm thấy thông tin'"]
    Filter -- pass --> Dedup[Dedup by file+page]

    Dedup --> P[Build RAG prompt\nsystem + context + question]
    P --> LLM[Ollama Qwen3-4B stream\nnum_gpu=99, num_ctx=4096]
    LLM --> Think{"<think> filter"}
    Think --> SSE["SSE stream tokens\n→ Frontend render"]

    Dedup --> Sources["Emit sources event\n→ Frontend DocCards"]
```

---

## 4. Luồng Image Search (POST /image-search)

```mermaid
flowchart TD
    Img[User gửi ảnh vào chat] --> Upload[POST /image-search\nmultipart/form-data]
    Upload --> Encode[CLIP ViT-B/32\nencode_image → 512-d]
    Encode --> Search[Qdrant query\ncollection: hr_images\ncosine similarity]
    Search --> Hits[Top-5 ảnh tương tự]
    Hits --> Response["JSON response:\nimage_url, source_url,\npage, score, caption"]
    Response --> UI[Frontend render\nDocCard + PDF viewer\nmở đúng trang]
```

---

## 5. Cấu trúc dữ liệu trong Qdrant

### Collection: hr_documents

```mermaid
erDiagram
    POINT {
        uuid id
        vector dense "1024-d cosine"
        sparse_vector sparse "token_id → weight"
    }
    POINT ||--|| PAYLOAD : has
    PAYLOAD {
        string text "cleaned chunk"
        string document_id
        json metadata
    }
    PAYLOAD ||--|| METADATA : has
    METADATA {
        string source "LTTQ_Huong.pdf"
        string source_path "data/corpus/.../file.pdf"
        int page
        string file_type "pdf|docx|txt"
        string doc_type
        int chunk_index
        int char_count
    }
```

### Collection: hr_images

```mermaid
erDiagram
    POINT {
        uuid id
        vector image "512-d cosine (CLIP)"
    }
    POINT ||--|| PAYLOAD : has
    PAYLOAD {
        string document_id
        json metadata
    }
    PAYLOAD ||--|| METADATA : has
    METADATA {
        string source "LTTQ_Huong.pdf"
        string source_path
        int page
        int figure_index
        string caption "page text preview"
        string image_path "extracted PNG path"
        int width
        int height
    }
```

---

## 6. Sequence Diagram — /chat/stream end-to-end

```mermaid
sequenceDiagram
    autonumber
    participant U as User (Browser)
    participant FE as Next.js :3000
    participant API as FastAPI :8000
    participant E as BGE-M3
    participant Q as Qdrant
    participant R as Reranker
    participant L as Ollama

    U->>FE: Nhập câu hỏi + Enter
    FE->>API: POST /chat/stream {question, top_k}
    API->>E: encode(question)
    E-->>API: {dense, sparse}
    API->>Q: query_batch_points(dense, sparse, limit=30)
    Q-->>API: dense_hits[], sparse_hits[]
    API->>API: RRF fusion → top 30
    API->>R: rerank(query, top30, top_k=5)
    R-->>API: top 5 + scores
    API->>API: dedup by file+page
    API-->>FE: SSE: {type:"sources", sources:[...]}
    FE->>FE: Render DocCards (PDF viewer)
    API->>L: chat(stream=True, messages=[...])
    loop Token stream
        L-->>API: {delta: "token"}
        API-->>FE: SSE: {type:"delta", content:"token"}
        FE->>FE: Append to message bubble
    end
    API-->>FE: SSE: {type:"done", latency_ms, stage_ms}
    FE->>FE: Show timing footer
```

---

## 7. VRAM Budget (RTX 5060, 8GB)

```
┌────────────────────────────────────┬──────────┐
│ Component                          │ VRAM     │
├────────────────────────────────────┼──────────┤
│ bge-m3 (always loaded)             │ ~1.2 GB  │
│ bge-reranker-v2-m3 (lazy load)     │ ~1.2 GB  │
│ Qwen3-4B Q4_K_M (Ollama, 100%)    │ ~3.5 GB  │
│ KV cache (4K context)              │ ~0.5 GB  │
│ CLIP ViT-B/32 (on-demand)          │ ~0.6 GB  │
│ PyTorch/CUDA overhead              │ ~0.5 GB  │
├────────────────────────────────────┼──────────┤
│ Peak (all loaded)                  │ ~7.5 GB  │
│ Available                          │ 8.0 GB   │
│ Margin                             │ 0.5 GB   │
└────────────────────────────────────┴──────────┘
```

---

## 8. File Serving Flow

```mermaid
flowchart LR
    Click["User click source link"] --> FE["Frontend builds URL"]
    FE --> |PDF| FileAPI["GET :8000/file?path=..."]
    FE --> |DOCX/TXT| PreviewAPI["GET :8000/preview?path=..."]
    FileAPI --> Inline["Content-Disposition: inline\nRFC 5987 UTF-8 filename"]
    PreviewAPI --> HTML["mammoth → styled HTML"]
    Inline --> Iframe["<iframe> renders PDF"]
    HTML --> Iframe2["<iframe> renders HTML"]

    Click2["User click 📂"] --> OpenAPI["GET :8000/open-file?path=..."]
    OpenAPI --> OS["os.startfile() → default app"]
```

---

## 9. Frontend Component Tree

```
app/page.tsx (ChatPage)
├── components/header.tsx         — Logo + subtitle
├── components/welcome.tsx        — 4 example prompts
├── components/message-bubble.tsx — User/Assistant messages
│   ├── components/doc-card.tsx   — PDF/DOCX inline viewer
│   │   ├── iframe (PDF or HTML preview)
│   │   ├── Loading spinner
│   │   └── Buttons: ↗ new tab · 📂 open local · ✕ close
│   └── components/typing-indicator.tsx — Bouncing dots
├── components/chat-input.tsx     — Textarea + image attach
│   ├── Image preview chip
│   ├── 📷 attach button
│   └── ↑ send / ■ stop buttons
└── lib/
    ├── chat-client.ts            — SSE parser + console logs
    ├── types.ts                  — ChatMessage, Source, SSEEvent
    └── utils.ts                  — cn(), formatMs()
```

---

## 10. Latency Breakdown (kỳ vọng sau GPU fix)

| Stage | Thời gian | Ghi chú |
|-------|-----------|---------|
| Embed query | ~50 ms | bge-m3, GPU |
| Hybrid search | 200-800 ms | Qdrant embedded |
| Rerank top-30 → top-5 | 150-300 ms | cross-encoder, GPU |
| LLM generate (~150 tokens) | 3-8 s | Qwen3-4B, 100% GPU |
| Image search (CLIP) | 30-100 ms | after first load |
| **Total text query** | **4-10 s** | |
| **Total image query** | **1-6 s** | |

---

## 11. Tài liệu liên quan

- [README.md](README.md) — setup & usage
- [PROJECT_PLAN.md](PROJECT_PLAN.md) — kế hoạch gốc
- [web/README.md](web/README.md) — frontend architecture
- [report/](report/) — báo cáo Word
- Source: `src/ingestion`, `src/search`, `src/generation`, `src/api`
