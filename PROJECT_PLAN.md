# Document Search System — HR Knowledge Base

## 1. Tổng quan

Hệ thống tìm kiếm thông minh cho **tài liệu quản lý nhân sự** (HR Knowledge Base), chạy hoàn toàn local trên RTX 5060 (8GB VRAM).

**Bài toán**: Công ty có hàng trăm tài liệu HR (nội quy, quy trình, chính sách lương thưởng, sổ tay nhân viên, hợp đồng mẫu...). Nhân viên thường phải hỏi HR cùng một câu hỏi lặp đi lặp lại. Giải pháp: chatbot nội bộ tra cứu tài liệu tự động.

**Ví dụ câu hỏi thực tế**:
- "Nhân viên được nghỉ phép tối đa bao nhiêu ngày/năm?"
- "Quy trình xin nghỉ việc gồm những bước gì?"
- "Mức lương thử việc so với lương chính thức chênh lệch bao nhiêu?"
- "Khi nào được xét tăng lương?"
- "Chính sách làm việc từ xa của công ty như thế nào?"
- "Phí hủy hợp đồng trước thời hạn tính thế nào?"

---

## 2. Dữ liệu đầu vào (ví dụ thực tế)

### 2.1. Các loại tài liệu HR thường gặp

```
data/hr_docs/
├── 01_so_tay_nhan_vien_2024.pdf          # 50 trang
├── 02_noi_quy_lao_dong.pdf                # 30 trang
├── 03_quy_che_luong_thuong.docx           # 20 trang
├── 04_quy_trinh_nghi_phep.pdf             # 5 trang
├── 05_quy_trinh_onboarding.pdf            # 15 trang
├── 06_chinh_sach_wfh.docx                 # 8 trang
├── 07_hop_dong_lao_dong_mau.pdf           # 10 trang
├── 08_bang_mo_ta_cong_viec/               # Job descriptions
│   ├── jd_backend_developer.pdf
│   ├── jd_frontend_developer.pdf
│   └── jd_devops_engineer.pdf
├── 09_faq_nhan_vien.txt                   # Q&A tích luỹ
└── 10_quy_dinh_bao_mat.pdf                # 12 trang
```

### 2.2. Ví dụ nội dung (trích đoạn)

**File: `01_so_tay_nhan_vien_2024.pdf` — Trang 12**
```
Điều 5. Chế độ nghỉ phép

5.1. Nghỉ phép năm:
- Nhân viên có hợp đồng chính thức được nghỉ 12 ngày phép/năm.
- Sau mỗi 5 năm làm việc, được cộng thêm 1 ngày/năm.
- Phép năm phải được đăng ký trước ít nhất 3 ngày làm việc.
- Phép chưa dùng hết trong năm sẽ được chuyển tối đa 5 ngày sang năm sau.

5.2. Nghỉ ốm:
- Được nghỉ tối đa 30 ngày/năm có hưởng 75% lương cơ bản.
- Cần có giấy xác nhận của cơ sở y tế nếu nghỉ từ 2 ngày trở lên.
```

**File: `03_quy_che_luong_thuong.docx` — Trang 5**
```
Điều 3. Lương thử việc và chính thức

3.1. Thời gian thử việc: 2 tháng kể từ ngày ký HĐ thử việc.

3.2. Lương thử việc: 85% lương chính thức theo JD của vị trí.

3.3. Xét tăng lương:
- Đánh giá định kỳ 6 tháng/lần (tháng 6 và tháng 12).
- Mức tăng dao động 5-15% tuỳ theo hiệu suất (KPI score).
- Nhân viên đạt "Outstanding" có thể được tăng đột xuất lên 20%.
```

**File: `06_chinh_sach_wfh.docx` — Trang 2**
```
2. Điều kiện làm việc từ xa

2.1. Đối tượng áp dụng:
- Nhân viên đã qua thử việc (hợp đồng chính thức từ 3 tháng trở lên).
- Vị trí công việc phù hợp (không bao gồm: Lễ tân, Bảo vệ, Kho vận).

2.2. Tần suất:
- Tối đa 2 ngày WFH/tuần.
- Phải có sự phê duyệt của Trưởng bộ phận.
- Đăng ký trước ít nhất 1 ngày qua hệ thống HRM.
```

### 2.3. Metadata trích xuất tự động

Với mỗi chunk text, hệ thống lưu:

```json
{
  "chunk_id": "01_so_tay_nhan_vien_2024__page_12__chunk_003",
  "text": "Điều 5. Chế độ nghỉ phép. 5.1. Nghỉ phép năm: Nhân viên...",
  "metadata": {
    "source": "01_so_tay_nhan_vien_2024.pdf",
    "page": 12,
    "doc_type": "handbook",
    "department": "HR",
    "last_updated": "2024-01-15",
    "char_count": 487
  }
}
```

### 2.4. Ví dụ kết quả tìm kiếm

**Query**: `"Nhân viên được nghỉ phép tối đa bao nhiêu ngày mỗi năm?"`

**Response**:
```json
{
  "answer": "Theo quy định, nhân viên có hợp đồng chính thức được nghỉ 12 ngày phép/năm. Sau mỗi 5 năm làm việc, được cộng thêm 1 ngày/năm. Phép chưa dùng hết trong năm sẽ được chuyển tối đa 5 ngày sang năm sau [Sổ tay nhân viên 2024, Tr.12]. Ngoài ra, nhân viên còn được nghỉ ốm tối đa 30 ngày/năm có hưởng 75% lương cơ bản [Sổ tay nhân viên 2024, Tr.12].",
  "sources": [
    {
      "file": "01_so_tay_nhan_vien_2024.pdf",
      "page": 12,
      "score": 0.892,
      "excerpt": "Nhân viên có hợp đồng chính thức được nghỉ 12 ngày phép/năm..."
    }
  ],
  "processing_time_ms": 1245
}
```

---

## 3. Tech Stack

| Component | Công nghệ | Phiên bản | Vai trò |
|-----------|-----------|-----------|---------|
| **LLM** | Ollama + Qwen3-8B | qwen3:8b (Q4_K_M) | Sinh câu trả lời từ context |
| **Embedding** | BAAI/bge-m3 | 1.2GB | Dense (1024-dim) + Sparse vectors |
| **Reranker** | BAAI/bge-reranker-v2-m3 | 568M params | Cross-encoder rerank |
| **Vector DB** | Qdrant | 1.12+ | Hybrid search (dense + sparse) |
| **Framework** | LlamaIndex | 0.12+ | RAG orchestration |
| **API** | FastAPI | 0.115+ | REST API |
| **UI** | Gradio | 5.0+ | Chat interface |
| **PDF Parser** | PyMuPDF (fitz) | 1.24+ | Extract text + metadata |
| **DOCX Parser** | python-docx | 1.1+ | Word documents |
| **Language** | Python | 3.11+ | |

---

## 4. Yêu cầu hệ thống (Requirements)

### 4.1. Functional Requirements

#### FR-1: Document Ingestion
- **FR-1.1**: Hệ thống hỗ trợ upload file PDF, DOCX, TXT (tối đa 50MB/file)
- **FR-1.2**: Hệ thống tự động parse nội dung và extract metadata (tên file, số trang, loại tài liệu)
- **FR-1.3**: Hệ thống chia nhỏ văn bản (chunking) với size=512 tokens, overlap=128 tokens
- **FR-1.4**: Hệ thống chuẩn hoá unicode tiếng Việt (NFC) và loại bỏ ký tự nhiễu
- **FR-1.5**: Hệ thống index chunks vào Qdrant với cả dense + sparse vectors
- **FR-1.6**: Hệ thống hỗ trợ update/delete tài liệu đã index

#### FR-2: Search
- **FR-2.1**: Hệ thống nhận câu hỏi tiếng Việt và encode thành vector truy vấn
- **FR-2.2**: Hệ thống thực hiện hybrid search (dense ANN + sparse BM25)
- **FR-2.3**: Hệ thống fusion kết quả bằng RRF (Reciprocal Rank Fusion)
- **FR-2.4**: Hệ thống rerank top-30 thành top-5 bằng cross-encoder
- **FR-2.5**: Hệ thống trả về chunks kèm điểm số và metadata

#### FR-3: Generation
- **FR-3.1**: Hệ thống sinh câu trả lời dựa trên top-5 chunks đã rerank
- **FR-3.2**: Câu trả lời phải trích dẫn nguồn dạng `[Tên tài liệu, Trang X]`
- **FR-3.3**: Khi không tìm thấy thông tin, hệ thống trả lời rõ ràng "Tài liệu không có thông tin này"
- **FR-3.4**: Câu trả lời bằng tiếng Việt, ngắn gọn (3-5 câu)

#### FR-4: API
- **FR-4.1**: POST `/upload` — upload và index tài liệu
- **FR-4.2**: POST `/chat` — hỏi đáp đầy đủ (search + generate)
- **FR-4.3**: GET `/search` — search only, không generate
- **FR-4.4**: GET `/documents` — list tài liệu đã index
- **FR-4.5**: DELETE `/documents/{id}` — xoá tài liệu
- **FR-4.6**: GET `/health` — kiểm tra trạng thái hệ thống

#### FR-5: UI
- **FR-5.1**: Giao diện chat với lịch sử hội thoại
- **FR-5.2**: Hiển thị citations kèm link tới vị trí trong tài liệu gốc
- **FR-5.3**: Upload tài liệu qua drag-and-drop
- **FR-5.4**: Hiển thị progress khi đang index

### 4.2. Non-Functional Requirements

| ID | Yêu cầu | Giá trị mục tiêu |
|----|--------|------------------|
| NFR-1 | **Latency** — thời gian trả lời tối đa | < 5 giây cho câu hỏi đơn giản |
| NFR-2 | **Throughput** — số request đồng thời | ≥ 3 concurrent users |
| NFR-3 | **Accuracy** — độ chính xác câu trả lời (đánh giá thủ công) | ≥ 85% |
| NFR-4 | **Retrieval Recall@5** | ≥ 90% |
| NFR-5 | **VRAM usage** — peak | ≤ 7 GB (để lại margin 1GB) |
| NFR-6 | **Privacy** — dữ liệu không rời máy local | 100% offline |
| NFR-7 | **Uptime** — thời gian hoạt động liên tục | ≥ 99% |
| NFR-8 | **Storage** — dung lượng lưu trữ per 1000 pages | < 500 MB |

### 4.3. Constraints

- **Hardware**: RTX 5060 (8GB VRAM), 32GB RAM khuyến nghị
- **OS**: Windows 10/11 hoặc Linux (Ubuntu 22.04+)
- **Network**: Không bắt buộc internet (chỉ cần khi pull models lần đầu)
- **Security**: Toàn bộ data on-premise, không gửi ra ngoài

---

## 5. Kiến trúc hệ thống

### 5.1. High-level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                                 │
│                 (Nhân viên công ty)                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Gradio UI (Port 7860)                     │
│            [Chat] [Upload] [Document List]                   │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Server (Port 8000)                  │
├─────────────────────────────────────────────────────────────┤
│  Routes:                                                     │
│  • POST /upload    → Ingestion Pipeline                     │
│  • POST /chat      → Search → Rerank → Generate             │
│  • GET  /search    → Search → Rerank (no generation)        │
│  • GET  /documents → List indexed docs                      │
└───────┬──────────────────────────┬──────────────────────────┘
        │                          │
        ▼                          ▼
┌───────────────────┐    ┌────────────────────────┐
│  Qdrant (:6333)   │    │  Ollama (:11434)       │
│  Vector Database  │    │  LLM Runtime            │
├───────────────────┤    ├────────────────────────┤
│ Collection:       │    │ Model: qwen3:8b         │
│  hr_documents     │    │ Context: 32K tokens     │
│                   │    │ VRAM: ~5.5 GB           │
│ Vectors:          │    └────────────────────────┘
│  • dense (1024)   │
│  • sparse (BM25)  │    ┌────────────────────────┐
│                   │    │ Embedder + Reranker    │
│ Payload:          │    │ (in-process Python)    │
│  • text           │    ├────────────────────────┤
│  • metadata       │    │ bge-m3:          1.2GB  │
└───────────────────┘    │ bge-reranker-v2: 1.2GB  │
                         └────────────────────────┘
```

### 5.2. Ingestion Pipeline Flow

```
User uploads "so_tay_nhan_vien.pdf"
         │
         ▼
┌──────────────────────────────────────┐
│ 1. Parse (PyMuPDF)                   │
│    → text[page_1], text[page_2], ... │
│    → metadata: {file, author, date}   │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│ 2. Clean Vietnamese Text              │
│    • unicode.normalize('NFC')         │
│    • Remove control chars             │
│    • Collapse whitespace              │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│ 3. Chunk                              │
│    RecursiveCharacterTextSplitter     │
│    • chunk_size=512, overlap=128      │
│    • separators: \n\n, \n, ". ", " "  │
│    → List[Chunk]                      │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│ 4. Embed (bge-m3)                     │
│    For each chunk:                    │
│    • dense_vec: (1024,) float32       │
│    • sparse_vec: {token_id: weight}   │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│ 5. Upsert to Qdrant                   │
│    PointStruct:                       │
│    • id: chunk_id (UUID)              │
│    • vector: {                        │
│        "dense": dense_vec,            │
│        "sparse": sparse_vec}          │
│    • payload: {text, source, page}    │
└──────────────────────────────────────┘
```

### 5.3. Search + Generation Flow

```
Query: "Nhân viên được nghỉ phép bao nhiêu ngày?"
         │
         ▼
┌──────────────────────────────────────┐
│ 1. Encode query (bge-m3)             │
│    → q_dense, q_sparse                │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│ 2. Hybrid Search (Qdrant)            │
│    • dense.search(q_dense, limit=30) │
│    • sparse.search(q_sparse, lim=30) │
│    • RRF fuse → top 30               │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│ 3. Rerank (bge-reranker-v2-m3)       │
│    scores = model([                   │
│      (query, chunk) for chunk in 30  │
│    ])                                 │
│    → top 5 highest scores             │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│ 4. Build RAG Prompt                   │
│    Context:                           │
│      [Sổ tay NV, Tr.12]: "Nhân viên  │
│       được nghỉ 12 ngày phép/năm..."  │
│      [Nội quy LD, Tr.8]: "..."       │
│    Question: {user_query}             │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│ 5. Generate (Ollama → Qwen3-8B)      │
│    temperature=0.2, top_p=0.9         │
│    → Answer with citations            │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│ 6. Response                           │
│    {                                  │
│      "answer": "...",                 │
│      "sources": [...],                │
│      "latency_ms": 1245               │
│    }                                  │
└──────────────────────────────────────┘
```

---

## 6. Cấu trúc project

```
document_search/
├── src/
│   ├── __init__.py
│   ├── config.py                      # Pydantic Settings
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── parser.py                  # PDF/DOCX/TXT parser
│   │   ├── cleaner.py                 # Vietnamese text cleaner
│   │   ├── chunker.py                 # Recursive text splitter
│   │   └── indexer.py                 # Embed + upsert vào Qdrant
│   ├── search/
│   │   ├── __init__.py
│   │   ├── embedder.py                # bge-m3 wrapper
│   │   ├── retriever.py               # Qdrant hybrid search + RRF
│   │   └── reranker.py                # Cross-encoder rerank
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── llm.py                     # Ollama client
│   │   └── prompts.py                 # RAG prompt templates
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app
│   │   ├── routes.py                  # API endpoints
│   │   └── schemas.py                 # Pydantic request/response
│   └── utils/
│       ├── __init__.py
│       └── logger.py
├── ui/
│   └── app.py                         # Gradio interface
├── data/
│   └── hr_docs/                       # Raw documents (gitignored)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures
│   ├── test_parser.py                 # Unit: PDF/DOCX parser
│   ├── test_chunker.py                # Unit: chunking logic
│   ├── test_embedder.py               # Unit: embedding shape/values
│   ├── test_retriever.py              # Unit: hybrid search
│   ├── test_reranker.py               # Unit: reranking
│   ├── test_llm.py                    # Unit: LLM client
│   ├── test_api.py                    # Integration: FastAPI
│   ├── test_e2e.py                    # E2E: full pipeline
│   └── fixtures/
│       ├── sample.pdf                 # Test PDF
│       ├── sample.docx                # Test DOCX
│       └── qa_pairs.json              # Evaluation Q&A pairs
├── evaluation/
│   ├── __init__.py
│   ├── generate_qa.py                 # Auto-generate Q&A từ docs
│   └── evaluate.py                    # Tính Recall@K, Faithfulness
├── scripts/
│   ├── setup_qdrant.py                # Init Qdrant collection
│   ├── ingest_folder.py               # Batch ingest folder
│   └── reset_db.py                    # Wipe Qdrant
├── docker-compose.yml                 # Qdrant container
├── requirements.txt
├── requirements-dev.txt               # pytest, black, ruff
├── .env.example
├── .gitignore
├── README.md
└── PROJECT_PLAN.md                    # File này
```

---

## 7. API Specification

### 7.1. POST `/upload`

**Request** (multipart/form-data):
```
file: <binary PDF/DOCX/TXT>
doc_type: "handbook" | "policy" | "jd" | "faq"
department: "HR" | "IT" | "Finance"
```

**Response** (200):
```json
{
  "document_id": "doc_a1b2c3",
  "filename": "so_tay_nhan_vien.pdf",
  "pages": 50,
  "chunks_indexed": 142,
  "processing_time_ms": 18500
}
```

### 7.2. POST `/chat`

**Request**:
```json
{
  "question": "Nhân viên được nghỉ phép bao nhiêu ngày?",
  "top_k": 5,
  "department_filter": null
}
```

**Response** (200):
```json
{
  "answer": "Nhân viên chính thức được nghỉ 12 ngày phép/năm. Sau mỗi 5 năm làm việc được cộng thêm 1 ngày. Phép chưa dùng có thể chuyển tối đa 5 ngày sang năm sau [Sổ tay nhân viên 2024, Tr.12].",
  "sources": [
    {
      "document_id": "doc_a1b2c3",
      "filename": "01_so_tay_nhan_vien_2024.pdf",
      "page": 12,
      "score": 0.892,
      "excerpt": "Điều 5. Chế độ nghỉ phép. 5.1. Nghỉ phép năm: Nhân viên có hợp đồng chính thức được nghỉ 12 ngày phép/năm..."
    },
    {
      "document_id": "doc_b2c3d4",
      "filename": "02_noi_quy_lao_dong.pdf",
      "page": 8,
      "score": 0.754,
      "excerpt": "..."
    }
  ],
  "latency_ms": 1245,
  "stage_ms": {
    "embed": 45,
    "search": 120,
    "rerank": 380,
    "generate": 700
  }
}
```

### 7.3. GET `/search`

**Request**: `GET /search?q=nghỉ+phép&k=10&department=HR`

**Response** (200):
```json
{
  "query": "nghỉ phép",
  "results": [
    {
      "chunk_id": "...",
      "text": "Điều 5. Chế độ nghỉ phép...",
      "metadata": {"source": "...", "page": 12},
      "score": 0.892
    }
  ],
  "total": 10
}
```

### 7.4. GET `/documents`

**Response** (200):
```json
{
  "total": 10,
  "documents": [
    {
      "document_id": "doc_a1b2c3",
      "filename": "01_so_tay_nhan_vien_2024.pdf",
      "doc_type": "handbook",
      "department": "HR",
      "pages": 50,
      "chunks_count": 142,
      "uploaded_at": "2025-05-11T10:30:00Z"
    }
  ]
}
```

---

## 8. Testing Strategy

### 8.1. Test Pyramid

```
         ┌─────────────┐
         │     E2E     │  ← 5-10 tests (full user journey)
         │  (Gradio →  │
         │   API → DB) │
         └─────────────┘
        ┌───────────────┐
        │  Integration   │  ← 20-30 tests (API + DB)
        │  (FastAPI +    │
        │   Qdrant)      │
        └───────────────┘
     ┌─────────────────────┐
     │      Unit Tests      │  ← 50+ tests (pure logic)
     │  (parser, chunker,   │
     │   embedder, etc.)    │
     └─────────────────────┘
```

### 8.2. Unit Tests

#### `test_parser.py`

```python
def test_parse_pdf_extracts_text():
    """PDF parser phải extract đúng text và metadata."""
    docs = parse_pdf("tests/fixtures/sample.pdf")
    assert len(docs) > 0
    assert "page" in docs[0].metadata
    assert docs[0].text != ""

def test_parse_pdf_vietnamese():
    """Parser phải giữ nguyên dấu tiếng Việt."""
    docs = parse_pdf("tests/fixtures/vietnamese_sample.pdf")
    assert "nhân viên" in docs[0].text.lower()

def test_parse_docx():
    """DOCX parser tương tự PDF."""
    docs = parse_docx("tests/fixtures/sample.docx")
    assert len(docs) > 0

def test_parse_invalid_file_raises():
    """File không hợp lệ phải raise exception."""
    with pytest.raises(ValueError):
        parse_pdf("nonexistent.pdf")
```

#### `test_chunker.py`

```python
def test_chunk_size_limit():
    """Mỗi chunk không vượt quá chunk_size."""
    chunks = chunk_text("a" * 2000, chunk_size=512, overlap=128)
    assert all(len(c.text) <= 512 for c in chunks)

def test_chunk_overlap():
    """Overlap giữa 2 chunks liên tiếp phải chính xác."""
    chunks = chunk_text("...", chunk_size=512, overlap=128)
    for i in range(len(chunks) - 1):
        overlap = get_overlap(chunks[i].text, chunks[i+1].text)
        assert len(overlap) >= 100  # gần bằng 128

def test_chunk_preserves_sentences():
    """Chunk không cắt giữa câu."""
    text = "Câu 1. Câu 2. Câu 3. " * 100
    chunks = chunk_text(text, chunk_size=200, overlap=50)
    for c in chunks:
        assert c.text.endswith((". ", "."))

def test_chunk_empty_input():
    """Input rỗng trả về list rỗng."""
    assert chunk_text("") == []
```

#### `test_embedder.py`

```python
def test_embed_output_shape():
    """Dense embedding phải có shape (1024,)."""
    emb = embedder.encode("test query")
    assert emb["dense"].shape == (1024,)
    assert len(emb["sparse"]) > 0

def test_embed_l2_normalized():
    """Dense vector phải được L2 normalize."""
    emb = embedder.encode("test")
    norm = np.linalg.norm(emb["dense"])
    assert abs(norm - 1.0) < 1e-4

def test_embed_similar_texts_close():
    """Text tương đồng có vector gần nhau."""
    v1 = embedder.encode("nghỉ phép")["dense"]
    v2 = embedder.encode("xin nghỉ")["dense"]
    v3 = embedder.encode("trái cây")["dense"]
    assert cosine(v1, v2) > cosine(v1, v3)

def test_embed_batch():
    """Batch encoding hoạt động."""
    embs = embedder.encode_batch(["a", "b", "c"])
    assert len(embs) == 3
```

#### `test_retriever.py`

```python
def test_hybrid_search_returns_results(qdrant_with_data):
    """Hybrid search trả về kết quả."""
    results = retriever.search("nghỉ phép", limit=10)
    assert len(results) > 0
    assert all("text" in r for r in results)

def test_rrf_fusion_correctness():
    """RRF công thức chính xác."""
    dense_rank = [("a", 0), ("b", 1), ("c", 2)]
    sparse_rank = [("b", 0), ("a", 1), ("d", 2)]
    fused = rrf_fusion(dense_rank, sparse_rank, k=60)
    # b có rank 1 + 0 → score cao hơn a (rank 0 + 1)
    assert fused[0][0] == "b" or fused[0][0] == "a"

def test_search_with_filter(qdrant_with_data):
    """Filter theo department hoạt động."""
    results = retriever.search(
        "policy", limit=10,
        filter={"department": "HR"}
    )
    assert all(r["metadata"]["department"] == "HR" for r in results)
```

#### `test_reranker.py`

```python
def test_reranker_reorders_results():
    """Reranker thay đổi thứ tự theo relevance."""
    query = "nghỉ phép bao nhiêu ngày"
    chunks = [
        "Nhân viên được nghỉ 12 ngày phép/năm",  # Relevant
        "Chính sách WFH 2 ngày/tuần",              # Not relevant
        "Mức lương thử việc 85%",                  # Not relevant
    ]
    reranked = reranker.rerank(query, chunks, top_k=3)
    assert reranked[0] == chunks[0]

def test_reranker_top_k():
    """top_k giới hạn số kết quả."""
    result = reranker.rerank("q", ["a", "b", "c", "d", "e"], top_k=2)
    assert len(result) == 2
```

#### `test_llm.py`

```python
def test_llm_answers_based_on_context():
    """LLM trả lời đúng khi có context."""
    context = "Nhân viên được nghỉ 12 ngày phép/năm."
    answer = llm.generate(
        question="Bao nhiêu ngày phép?",
        context=context
    )
    assert "12" in answer

def test_llm_says_dont_know_when_no_info():
    """LLM trả lời 'không có thông tin' khi context không chứa đáp án."""
    context = "Chính sách làm việc từ xa..."
    answer = llm.generate(
        question="Mức lương CEO là bao nhiêu?",
        context=context
    )
    assert "không có thông tin" in answer.lower() or "không biết" in answer.lower()

def test_llm_includes_citation():
    """LLM output bao gồm citation."""
    context = "[Sổ tay NV, Tr.12]: Nhân viên được nghỉ 12 ngày..."
    answer = llm.generate("Nghỉ phép?", context)
    assert "[" in answer and "]" in answer
```

### 8.3. Integration Tests (`test_api.py`)

```python
from fastapi.testclient import TestClient

def test_upload_endpoint(client: TestClient):
    """POST /upload upload file thành công."""
    with open("tests/fixtures/sample.pdf", "rb") as f:
        r = client.post("/upload", files={"file": f})
    assert r.status_code == 200
    assert r.json()["chunks_indexed"] > 0

def test_chat_endpoint(client: TestClient):
    """POST /chat trả về answer + sources."""
    r = client.post("/chat", json={
        "question": "Nhân viên được nghỉ phép bao nhiêu ngày?",
        "top_k": 5
    })
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert len(data["sources"]) > 0

def test_search_endpoint(client: TestClient):
    """GET /search trả về chunks."""
    r = client.get("/search?q=nghỉ phép&k=5")
    assert r.status_code == 200
    assert len(r.json()["results"]) <= 5

def test_health_endpoint(client: TestClient):
    """GET /health trả về ok."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_chat_with_empty_query_returns_400(client: TestClient):
    """Query rỗng trả về 400."""
    r = client.post("/chat", json={"question": ""})
    assert r.status_code == 422
```

### 8.4. E2E Tests (`test_e2e.py`)

```python
def test_full_pipeline_hr_scenario():
    """E2E: upload HR doc → hỏi đáp → verify citation."""
    # 1. Upload
    with open("tests/fixtures/so_tay_nhan_vien.pdf", "rb") as f:
        upload_r = client.post("/upload", files={"file": f})
    assert upload_r.status_code == 200
    
    # 2. Wait indexing
    time.sleep(2)
    
    # 3. Ask question
    chat_r = client.post("/chat", json={
        "question": "Nhân viên được nghỉ phép bao nhiêu ngày/năm?"
    })
    
    # 4. Verify answer
    data = chat_r.json()
    assert "12" in data["answer"] or "mười hai" in data["answer"]
    assert data["sources"][0]["filename"] == "so_tay_nhan_vien.pdf"
    assert data["latency_ms"] < 5000  # < 5 giây

def test_full_pipeline_no_info_scenario():
    """E2E: hỏi câu không có trong tài liệu → trả lời 'không có'."""
    r = client.post("/chat", json={
        "question": "Giá cổ phiếu công ty hôm nay là bao nhiêu?"
    })
    data = r.json()
    assert "không có thông tin" in data["answer"].lower()
```

### 8.5. Evaluation (Offline Quality Metrics)

#### `evaluation/evaluate.py`

Tập test: 50 cặp Q&A chuẩn bị sẵn từ tài liệu HR thực tế.

```python
EVAL_QUESTIONS = [
    {
        "question": "Nhân viên được nghỉ phép bao nhiêu ngày/năm?",
        "expected_answer_contains": ["12 ngày"],
        "expected_source": "01_so_tay_nhan_vien_2024.pdf",
        "expected_page": 12
    },
    {
        "question": "Lương thử việc bằng bao nhiêu % lương chính thức?",
        "expected_answer_contains": ["85%"],
        "expected_source": "03_quy_che_luong_thuong.docx",
        "expected_page": 5
    },
    # ... 48 câu khác
]

def evaluate_retrieval():
    """Đo Recall@5 và MRR."""
    recall_hits, mrr_sum = 0, 0
    for item in EVAL_QUESTIONS:
        results = retriever.search(item["question"], limit=5)
        sources = [r["metadata"]["source"] for r in results]
        if item["expected_source"] in sources:
            recall_hits += 1
            rank = sources.index(item["expected_source"]) + 1
            mrr_sum += 1.0 / rank
    return {
        "recall@5": recall_hits / len(EVAL_QUESTIONS),
        "mrr": mrr_sum / len(EVAL_QUESTIONS)
    }

def evaluate_generation():
    """Đo Faithfulness (câu trả lời có trong context không)."""
    correct = 0
    for item in EVAL_QUESTIONS:
        answer = rag.query(item["question"])
        if any(ex in answer for ex in item["expected_answer_contains"]):
            correct += 1
    return {"answer_accuracy": correct / len(EVAL_QUESTIONS)}
```

**Target metrics**:
- Recall@5 ≥ 90%
- MRR ≥ 0.75
- Answer Accuracy ≥ 85%

### 8.6. Performance Tests

```python
def test_latency_under_5s():
    """Latency < 5 giây cho query đơn giản."""
    start = time.time()
    client.post("/chat", json={"question": "Nghỉ phép?"})
    assert time.time() - start < 5.0

def test_concurrent_requests():
    """Handle 3 concurrent users không crash."""
    import concurrent.futures
    questions = ["q1", "q2", "q3"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futures = [ex.submit(
            client.post, "/chat", json={"question": q}
        ) for q in questions]
        results = [f.result() for f in futures]
    assert all(r.status_code == 200 for r in results)

def test_vram_usage():
    """VRAM peak không vượt 7GB."""
    import torch
    torch.cuda.reset_peak_memory_stats()
    client.post("/chat", json={"question": "test"})
    peak_gb = torch.cuda.max_memory_allocated() / 1e9
    assert peak_gb < 7.0
```

### 8.7. Run Tests

```bash
# Unit tests only (nhanh)
pytest tests/ -v -m "not integration and not e2e"

# Integration tests (cần Qdrant running)
pytest tests/ -v -m integration

# E2E tests (cần Qdrant + Ollama running)
pytest tests/ -v -m e2e

# Coverage
pytest --cov=src --cov-report=html

# Evaluation
python -m evaluation.evaluate
```

---

## 9. Setup Guide

### 9.1. Prerequisites

```bash
# Check Python
python --version  # >= 3.11

# Check GPU
nvidia-smi  # Phải thấy RTX 5060

# Check Docker
docker --version
```

### 9.2. Install Ollama

```bash
# Windows: tải từ https://ollama.com/download
# Sau khi cài:
ollama pull qwen3:8b
ollama list  # Xác nhận model đã có
```

### 9.3. Start Qdrant

```bash
cd document_search
docker-compose up -d

# Check Qdrant running
curl http://localhost:6333/healthz
```

`docker-compose.yml`:
```yaml
version: "3.9"
services:
  qdrant:
    image: qdrant/qdrant:v1.12.0
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_data:/qdrant/storage
    environment:
      - QDRANT__LOG_LEVEL=INFO
```

### 9.4. Python Environment

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 9.5. Configuration (`.env`)

```env
# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=hr_documents

# Ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b

# Models
EMBEDDING_MODEL=BAAI/bge-m3
RERANKER_MODEL=BAAI/bge-reranker-v2-m3

# Chunking
CHUNK_SIZE=512
CHUNK_OVERLAP=128

# Search
TOP_K_RETRIEVE=30
TOP_K_RERANK=5
RRF_K=60

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### 9.6. Initialize Qdrant Collection

```bash
python scripts/setup_qdrant.py
```

### 9.7. Run Services

```bash
# Terminal 1: FastAPI
uvicorn src.api.main:app --reload --port 8000

# Terminal 2: Gradio UI
python ui/app.py

# Mở trình duyệt:
# - Gradio: http://localhost:7860
# - API docs: http://localhost:8000/docs
```

### 9.8. Ingest HR Documents

```bash
# Bỏ PDF vào data/hr_docs/
python scripts/ingest_folder.py --folder data/hr_docs/
```

---

## 10. Requirements Files

### `requirements.txt`

```
# API
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.9

# LLM
ollama==0.4.0

# Embedding & Reranker
sentence-transformers>=3.0.0
FlagEmbedding>=1.2.0
torch>=2.2.0
transformers>=4.40.0

# Vector DB
qdrant-client>=1.12.0

# Document parsing
PyMuPDF>=1.24.0
python-docx>=1.1.0

# Text processing
langchain-text-splitters>=0.2.0

# UI
gradio>=5.0.0

# Utils
pydantic>=2.6.0
pydantic-settings>=2.4.0
python-dotenv>=1.0.0
tqdm>=4.66.0
numpy>=1.26.0
```

### `requirements-dev.txt`

```
-r requirements.txt

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
httpx>=0.27.0

# Linting
black>=24.0.0
ruff>=0.3.0
mypy>=1.8.0
```

---

## 11. VRAM Budget

```
┌────────────────────────────────────┬──────────┐
│ Component                          │ VRAM     │
├────────────────────────────────────┼──────────┤
│ bge-m3 (always loaded)             │ ~1.2 GB  │
│ bge-reranker-v2-m3 (lazy load)     │ ~1.2 GB  │
│ Qwen3-8B Q4_K_M (Ollama)          │ ~5.5 GB  │
│ KV cache (4K context)              │ ~1.0 GB  │
│ PyTorch/CUDA overhead              │ ~0.5 GB  │
├────────────────────────────────────┼──────────┤
│ Peak usage (search + generate)     │ ~7.0 GB  │
│ Available on RTX 5060              │ 8.0 GB   │
│ Margin                             │ 1.0 GB   │
└────────────────────────────────────┴──────────┘
```

**Lưu ý**:
- Ollama tự unload model khi idle 5 phút → tiết kiệm VRAM khi không dùng
- Reranker load on-demand, unload sau 60s idle

---

## 12. Prompt Template

```python
RAG_PROMPT = """Bạn là trợ lý AI của bộ phận Nhân sự, chuyên trả lời câu hỏi về chính sách, quy trình và quy định của công ty dựa trên tài liệu được cung cấp.

QUY TẮC:
1. Chỉ trả lời dựa trên thông tin trong [TÀI LIỆU] bên dưới.
2. Nếu tài liệu không chứa câu trả lời, nói rõ: "Tài liệu hiện tại không có thông tin về vấn đề này. Vui lòng liên hệ bộ phận HR để được hỗ trợ."
3. Luôn trích dẫn nguồn ở cuối mỗi ý: [Tên file, Trang X]
4. Trả lời ngắn gọn, rõ ràng (3-5 câu).
5. Ngôn ngữ: tiếng Việt, trang trọng nhưng thân thiện.

[TÀI LIỆU]:
{context}

[CÂU HỎI]:
{question}

[TRẢ LỜI]:"""
```

---

## 13. Điểm nhấn kỹ thuật (cho phỏng vấn)

1. **Hybrid Search** — Dense (semantic) + Sparse (keyword) → RRF fusion. Bắt được cả ngữ nghĩa (câu hỏi tự nhiên) và từ khoá chính xác (tên policy, số hiệu văn bản).

2. **Cross-Encoder Reranking** — Pipeline hình phễu: Retrieve 30 (fast, Bi-encoder) → Rerank top-5 (accurate, Cross-encoder). Cân bằng tốc độ & chất lượng.

3. **bge-m3 multi-functionality** — 1 model output cả dense + sparse, giảm memory footprint, đồng nhất semantic space.

4. **Citation/Attribution** — Mỗi câu trả lời đều có nguồn gốc rõ ràng → user tin tưởng, dễ verify, giảm rủi ro hallucination.

5. **100% Local** — Data HR nhạy cảm không rời máy. Phù hợp compliance của các công ty tại Việt Nam (PDPL 2025).

6. **Vietnamese-aware** — Text cleaner normalize NFC, chunker preserve câu tiếng Việt, model bge-m3 train trên dữ liệu đa ngôn ngữ gồm tiếng Việt.

7. **Evaluation pipeline** — Có test set QA chuẩn để đo Recall@K, MRR, Answer Accuracy → chứng minh chất lượng đo lường được.

---

## 14. Lộ trình 3 ngày

| Ngày | Task | Deliverable |
|------|------|-------------|
| **Ngày 1** | Setup + Ingestion | Qdrant chạy, upload PDF → index thành công |
| 1 AM | Setup Qdrant Docker, Ollama, venv, project structure | `docker-compose up`, `ollama pull qwen3:8b` |
| 1 PM | Implement parser, cleaner, chunker, indexer | `python scripts/ingest_folder.py` chạy OK |
| 1 Evening | Unit tests: parser, chunker | `pytest tests/test_parser.py tests/test_chunker.py` pass |
| **Ngày 2** | Search + Generation | Hỏi đáp qua CLI hoặc script |
| 2 AM | Embedder (bge-m3), Retriever (hybrid + RRF) | Search trả về chunks đúng |
| 2 PM | Reranker, LLM (Ollama), Prompt | Sinh câu trả lời có citation |
| 2 Evening | Unit tests: embedder, retriever, reranker, llm | Pass all unit tests |
| **Ngày 3** | API + UI + Polish | Demo chạy được |
| 3 AM | FastAPI routes (upload, chat, search, health) | Postman test pass |
| 3 PM | Gradio UI | Chat UI mượt, hiển thị sources |
| 3 Evening | Integration tests + E2E + README demo | Full demo record video |

---

## 15. Câu hỏi thường gặp (cho phỏng vấn)

**Q1: Tại sao chọn Qdrant thay vì ChromaDB?**
A: Qdrant viết bằng Rust → tốc độ cao, hỗ trợ native sparse vectors cho hybrid search. ChromaDB đơn giản nhưng không có sparse vector, không phù hợp keyword matching.

**Q2: Tại sao dùng bge-m3 thay vì multilingual-e5?**
A: bge-m3 output cả dense + sparse trong 1 model → giảm memory và latency. Support 100+ ngôn ngữ, context 8K tokens, top MTEB multilingual benchmark.

**Q3: Tại sao cần reranker khi đã có hybrid search?**
A: Hybrid search dùng Bi-encoder → nhanh nhưng query và doc được encode độc lập. Cross-encoder đọc cả 2 cùng lúc, bắt được mối quan hệ tinh tế → top-5 chính xác hơn nhiều.

**Q4: Nếu câu hỏi không có trong tài liệu, model làm gì?**
A: Prompt yêu cầu trả lời "Tài liệu không có thông tin" + chỉ định temperature thấp (0.2). Ngoài ra set threshold tối thiểu cho score → nếu không hit chunk nào đạt threshold, skip LLM và báo trực tiếp.

**Q5: Làm sao scale lên 100K+ documents?**
A: Qdrant hỗ trợ shard, HNSW index scale O(log N), có thể tăng `segment_number` và dùng `on_disk=True` cho vectors lớn. Bottleneck sẽ là LLM inference → có thể dùng vLLM thay Ollama.

**Q6: Làm sao tránh prompt injection?**
A: (1) Escape user input, (2) System prompt đặt role rõ ràng, (3) Output parser validate format answer, (4) Giới hạn max_tokens output.

---

## 16. Mở rộng (v2)

- [ ] **Multi-query**: LLM sinh 3 biến thể câu hỏi → search cả 3 → merge (tăng recall)
- [ ] **Parent-child chunking**: search child (nhỏ, precise), return parent (lớn, giàu context)
- [ ] **Conversation memory**: nhớ lịch sử hội thoại, hỗ trợ follow-up questions
- [ ] **Metadata filter trong UI**: chọn department, doc_type để narrow search
- [ ] **Streaming response**: stream từng token thay vì đợi xong cả câu
- [ ] **Vietnamese word segmenter**: `NlpHUST/vi-word-segmentation` để sparse vectors chính xác hơn
- [ ] **Feedback loop**: user đánh giá thumbs up/down → log để cải thiện
- [ ] **Multi-tenant**: tách data theo công ty/phòng ban
- [ ] **OCR cho scanned PDF**: VietOCR cho tài liệu scan
