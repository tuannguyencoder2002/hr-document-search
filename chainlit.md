# 👋 Trợ lý Nhân sự

Hệ thống hỏi đáp tài liệu HR nội bộ, chạy **100% local**. Toàn bộ tài liệu (PDF / DOCX) đã được index sẵn vào hệ thống — chỉ việc đặt câu hỏi. Mọi câu trả lời đều kèm **nguồn tham khảo**, bấm vào link nguồn để xem nguyên văn đoạn tài liệu.

### Ví dụ câu hỏi

- Nhân viên được nghỉ phép tối đa bao nhiêu ngày mỗi năm?
- Quy trình xin nghỉ việc gồm những bước gì?
- Lương thử việc bằng bao nhiêu phần trăm lương chính thức?
- Chính sách làm việc từ xa của công ty như thế nào?
- Phí hủy hợp đồng trước thời hạn tính như thế nào?

### Ngăn xếp kỹ thuật

| Thành phần | Công nghệ |
|---|---|
| LLM | Ollama + Qwen3-8B |
| Embedding | BAAI/bge-m3 (dense + sparse) |
| Reranker | BAAI/bge-reranker-v2-m3 |
| Vector DB | Qdrant (hybrid search) |
| Backend | FastAPI |
| UI | Chainlit |
