# 👋 Document Search Assistant

Hệ thống hỏi đáp **tài liệu học tập**, chạy **100% local**. Mọi câu trả lời đều kèm **nguồn tham khảo**, bấm vào link nguồn để xem nguyên văn đoạn tài liệu.

### Ví dụ câu hỏi

- Chuẩn hóa CSDL: 1NF, 2NF, 3NF khác nhau thế nào?
- Thuật toán DFS và BFS áp dụng khi nào?
- Ôn tập VSTEP: cấu trúc bài Speaking / Listening ra sao?
- Vi xử lý: nguyên lý hoạt động của ADC ngoài vi là gì?

### Thêm tài liệu tạm thời

Đính kèm file **PDF / DOCX / TXT / MD** (≤ 50MB, tối đa 10 file/lần) cùng tin nhắn — hệ thống sẽ vector hóa và ghi vào DB ngay. Dùng `scripts/ingest_folder.py` nếu muốn index cả thư mục một lượt.

### Ngăn xếp kỹ thuật

| Thành phần | Công nghệ |
|---|---|
| LLM | Ollama · Qwen3-8B |
| Embedding | BAAI/bge-m3 (dense + sparse) |
| Reranker | BAAI/bge-reranker-v2-m3 |
| Vector DB | Qdrant (hybrid search + RRF) |
| Backend | FastAPI |
| UI | Chainlit |
