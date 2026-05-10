# PIPELINE — HR Document Search

Tài liệu này mô tả **chi tiết lưu đồ xử lý** của hệ thống RAG cho tài liệu nhân sự.
Tất cả các sơ đồ đều dùng [Mermaid](https://mermaid.js.org/) — GitHub / VS Code preview render trực tiếp.

---

## 1. Kiến trúc tổng quan

```mermaid
flowchart TB
    User((👤 Nhân viên))

    subgraph UI["Chainlit UI :7860"]
      Chat[💬 Chat]
      Upload[📤 Drag-drop upload]
      Cite[🔗 Citation side panel]
    end

    subgraph API["FastAPI :8000"]
      Rupload["POST /upload"]
      Rchat["POST /chat"]
      Rsearch["GET /search"]
      Rdocs["GET /documents"]
      Rhealth["GET /health"]
    end

    subgraph Services["Local services"]
      Qdrant[("🧭 Qdrant :6333<br/>Collection: hr_documents<br/>dense(1024)+sparse")]
      Ollama[("🧠 Ollama :11434<br/>qwen3:8b Q4_K_M")]
    end

    subgraph Models["In-process (Python)"]
      BGE[["bge-m3<br/>dense + sparse"]]
      RR[["bge-reranker-v2-m3<br/>cross-encoder"]]
    end

    User --> UI
    UI -->|HTTP JSON| API
    Rupload --> BGE --> Qdrant
    Rchat --> BGE --> Qdrant --> RR --> Ollama --> Rchat
    Rsearch --> BGE --> Qdrant
    Rhealth --> Qdrant
    Rhealth --> Ollama
```

---

## 2. Luồng Ingestion (POST /upload)

Mục tiêu: biến 1 file tài liệu (PDF/DOCX/TXT) thành nhiều `PointStruct` trong Qdrant.

```mermaid
flowchart TD
    A[User upload file<br/>qua UI hoặc POST /upload] --> B{Validate<br/>extension + size ≤ 50MB}
    B -- "❌ reject" --> Err1[400 / 413]
    B -- "✅" --> C[Save to tempfile]
    C --> D[parse_file]
    D -->|PDF| D1[PyMuPDF<br/>per-page text]
    D -->|DOCX| D2[python-docx<br/>paragraphs + tables]
    D -->|TXT| D3[read utf-8]
    D1 --> E[List ParsedDocument<br/>text + metadata]
    D2 --> E
    D3 --> E
    E --> F[clean_text per doc<br/>NFC + strip ctrl + collapse ws]
    F --> G[chunk_documents<br/>RecursiveCharacterTextSplitter<br/>chunk_size=512, overlap=128]
    G --> H[List Chunk<br/>text + metadata<br/>chunk_index, char_count,<br/>source, page, doc_type, department]
    H --> I[Batch loop batch_size=16]
    I --> J[embedder.encode_batch]
    J --> J1[dense 1024-d<br/>L2 normalized]
    J --> J2[sparse token_id → weight]
    J1 --> K[Build PointStruct]
    J2 --> K
    K --> L[client.upsert<br/>collection=hr_documents]
    L --> M[Return UploadResponse<br/>document_id, pages,<br/>chunks_indexed, ms]
```

**Ví dụ dữ liệu qua từng bước**:

| Bước | Input | Output |
|------|-------|--------|
| parse | `so_tay_nhan_vien.pdf` (50 trang) | 50 `ParsedDocument` |
| clean | 50 doc có lẫn `\x00`, NFD | 50 doc sạch, NFC |
| chunk | 50 doc × ~2000 chars | ~142 `Chunk` (~512 chars, overlap 128) |
| embed | 142 chunk | `dense: (142, 1024)` + `sparse: List[dict]` |
| upsert | 142 point | 1 Qdrant collection +142 points |

---

## 3. Luồng Search + Generation (POST /chat)

```mermaid
flowchart TD
    Q["Câu hỏi tiếng Việt<br/>ví dụ: 'Nghỉ phép bao nhiêu ngày?'"] --> E1[bge-m3 encode query]
    E1 --> E1a[q_dense 1024-d]
    E1 --> E1b[q_sparse]

    E1a --> S[Qdrant query_batch_points]
    E1b --> S
    S --> S1[dense.search top-30]
    S --> S2[sparse.search top-30]

    S1 --> RRF["RRF fusion<br/>score = Σ 1/(k+rank+1)<br/>k=60"]
    S2 --> RRF
    RRF --> R30[Top 30 fused chunks<br/>{id, score, text, metadata}]

    R30 --> RR[bge-reranker-v2-m3<br/>cross-encoder score pairs]
    RR --> R5[Top 5 chunks<br/>+ rerank_score]

    R5 --> P[build_prompt<br/>system + context + question]
    P --> LLM[Ollama qwen3:8b<br/>temperature=0.2<br/>top_p=0.9]
    LLM --> ANS[Answer với citation<br/>Sổ tay NV, Trang 12]

    ANS --> RESP["ChatResponse<br/>{answer, sources[], latency_ms, stage_ms}"]
```

**Giải thích 2 giai đoạn tìm kiếm**:

```mermaid
graph LR
    subgraph Stage1["Giai đoạn 1: Retrieve (fast, bi-encoder)"]
      direction TB
      All[(~10K chunks)] -.-> Dense[Dense ANN<br/>O log N]
      All -.-> Sparse[Sparse BM25-like]
      Dense --> Fuse[RRF]
      Sparse --> Fuse
      Fuse --> Top30[Top 30]
    end

    subgraph Stage2["Giai đoạn 2: Rerank (slow, cross-encoder)"]
      direction TB
      Top30 --> Pairs["30 pairs<br/>(query, chunk)"]
      Pairs --> CE[Cross-encoder<br/>O n compute]
      CE --> Top5[Top 5]
    end
```

Lý do pipeline **hình phễu**:
- Stage 1 nhanh nhưng encode query và doc độc lập → chỉ bắt được semantic thô.
- Stage 2 chậm hơn ~10× nhưng đọc query + chunk đồng thời → bắt được quan hệ tinh tế.
- Kết hợp lại: cân bằng tốc độ & độ chính xác.

---

## 4. Cấu trúc dữ liệu trong Qdrant

```mermaid
erDiagram
    COLLECTION_HR_DOCUMENTS ||--o{ POINT : contains
    POINT {
        uuid id
        vector dense "1024-d cosine"
        sparse_vector sparse "token_id to weight"
        json payload
    }
    POINT ||--|| PAYLOAD : has
    PAYLOAD {
        string text "cleaned chunk text"
        string document_id "doc_abc123"
        json metadata
    }
    PAYLOAD ||--|| METADATA : has
    METADATA {
        string source "01_so_tay_nhan_vien.pdf"
        int page "12"
        string file_type "pdf"
        string doc_type "handbook"
        string department "HR"
        int chunk_index
        int char_count
    }
```

**Ví dụ 1 point**:

```json
{
  "id": "a1b2c3d4-...",
  "vector": {
    "dense": [0.021, -0.113, ..., 0.087],
    "sparse": { "12345": 0.87, "67890": 0.42 }
  },
  "payload": {
    "text": "Điều 5. Chế độ nghỉ phép. 5.1. Nghỉ phép năm: Nhân viên...",
    "document_id": "doc_a1b2c3",
    "metadata": {
      "source": "01_so_tay_nhan_vien_2024.pdf",
      "page": 12,
      "file_type": "pdf",
      "doc_type": "handbook",
      "department": "HR",
      "chunk_index": 3,
      "char_count": 487
    }
  }
}
```

---

## 5. Sequence diagram — /chat end-to-end

```mermaid
sequenceDiagram
    autonumber
    participant U as User (Gradio)
    participant API as FastAPI /chat
    participant E as BGEEmbedder
    participant Q as Qdrant
    participant R as Reranker
    participant L as Ollama

    U->>API: POST /chat { question, top_k }
    API->>E: encode(question)
    E-->>API: { dense, sparse }
    API->>Q: query_batch_points(dense, sparse, limit=30)
    Q-->>API: dense_hits[], sparse_hits[]
    API->>API: rrf_fusion → top 30
    API->>R: rerank(q, top30, top_k=5)
    R-->>API: top 5 + rerank_score
    API->>API: build_prompt(question, top5)
    API->>L: chat(system+user prompt)
    L-->>API: answer with citations
    API-->>U: { answer, sources, latency_ms, stage_ms }
```

---

## 6. Thứ tự module (dependency graph)

```mermaid
flowchart LR
    config[config.py]
    logger[utils/logger.py]

    parser[ingestion/parser.py]
    cleaner[ingestion/cleaner.py]
    chunker[ingestion/chunker.py]
    indexer[ingestion/indexer.py]

    embedder[search/embedder.py]
    retriever[search/retriever.py]
    reranker[search/reranker.py]

    prompts[generation/prompts.py]
    llm[generation/llm.py]

    schemas[api/schemas.py]
    routes[api/routes.py]
    main[api/main.py]
    ui[ui/app.py]

    config --> embedder
    config --> retriever
    config --> reranker
    config --> llm
    config --> indexer

    parser --> indexer
    cleaner --> indexer
    chunker --> indexer
    embedder --> indexer
    embedder --> retriever

    prompts --> llm
    retriever --> routes
    reranker --> routes
    llm --> routes
    indexer --> routes
    schemas --> routes
    routes --> main
    main -.->|HTTP| ui
```

---

## 7. VRAM timeline (ví dụ 1 request /chat)

```mermaid
gantt
    title VRAM allocation during /chat (RTX 5060 8GB)
    dateFormat X
    axisFormat %s ms

    section bge-m3
    Loaded (1.2GB always)   :done, 0, 5000

    section bge-reranker
    Lazy load (1.2GB)       :active, 100, 500
    Stay in VRAM            :active, 600, 2000
    Idle unload optional    :crit, 2600, 2700

    section Qwen3-8B (Ollama)
    Already loaded (5.5GB)  :done, 0, 5000
    KV cache (+1GB)         :active, 800, 2000

    section Peak
    Peak ≈ 7.0 GB           :milestone, 1000, 0
```

---

## 8. Error & edge-case handling

```mermaid
flowchart TD
    Start[POST /chat question] --> E{question rỗng?}
    E -- yes --> E400[422 Unprocessable]
    E -- no --> R[retrieve top-30]
    R --> R0{len == 0?}
    R0 -- yes --> FB["Trả template:<br/>'Tài liệu không có thông tin'<br/>(SKIP LLM để tiết kiệm VRAM)"]
    R0 -- no --> RR[rerank top-5]
    RR --> RR0{max score < threshold?}
    RR0 -- yes --> FB
    RR0 -- no --> G[generate]
    G --> G0{LLM timeout?}
    G0 -- yes --> G504[504 Gateway Timeout]
    G0 -- no --> OK[200 ChatResponse]
```

---

## 9. So sánh latency từng stage (kỳ vọng)

| Stage | Thời gian | Ghi chú |
|-------|-----------|---------|
| Embed query | ~40 ms | bge-m3, GPU |
| Hybrid search | ~100 ms | Qdrant `query_batch_points` |
| Rerank top-30 → top-5 | ~350 ms | cross-encoder, GPU |
| LLM generate (~150 tokens) | ~700 ms | Qwen3-8B Q4_K_M trên RTX 5060 |
| **Tổng** | **~1.2 s** | Mục tiêu NFR-1: < 5s |

---

## 10. Tài liệu liên quan

- [PROJECT_PLAN.md](PROJECT_PLAN.md) — kế hoạch chi tiết đầy đủ
- [README.md](README.md) — setup & usage
- Source code: `src/ingestion`, `src/search`, `src/generation`, `src/api`
