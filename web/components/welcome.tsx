"use client";

import { Sparkles } from "lucide-react";

type Props = {
  onPick: (prompt: string) => void;
};

const EXAMPLES = [
  "Chuẩn hóa CSDL: 1NF, 2NF và 3NF khác nhau thế nào?",
  "So sánh thuật toán DFS và BFS?",
  "Tổng quan về .NET Framework và các thành phần chính?",
  "Cấu trúc bài thi VSTEP phần Speaking gồm những phần nào?",
];

export function Welcome({ onPick }: Props) {
  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center px-4 pb-6 pt-16 text-center">
      <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
        <Sparkles className="h-6 w-6" strokeWidth={2} />
      </div>
      <h1 className="text-2xl font-semibold tracking-tight text-foreground">
        Trợ lý tài liệu
      </h1>
      <p className="mt-2 max-w-md text-[15px] leading-relaxed text-muted-foreground">
        Đặt câu hỏi về bất kỳ tài liệu nào đã được index. Mỗi câu trả lời đều
        kèm nguồn tham khảo với PDF có thể xem ngay trong cuộc trò chuyện.
      </p>

      <div className="mt-8 grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
        {EXAMPLES.map((q) => (
          <button
            key={q}
            onClick={() => onPick(q)}
            className="group rounded-xl border border-border bg-card px-4 py-3 text-left text-sm text-foreground shadow-sm transition hover:border-primary/40 hover:shadow-md"
          >
            <span className="line-clamp-2">{q}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
