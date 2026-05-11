"use client";

import { ArrowUp, Square } from "lucide-react";
import {
  KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import { cn } from "@/lib/utils";

type Props = {
  onSubmit: (value: string) => void;
  onStop?: () => void;
  disabled?: boolean;
  streaming?: boolean;
};

export function ChatInput({ onSubmit, onStop, disabled, streaming }: Props) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea as user types.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }, [value]);

  const send = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="sticky bottom-0 left-0 right-0 border-t border-border bg-background/95 backdrop-blur">
      <div className="mx-auto max-w-3xl px-4 py-3">
        <div
          className={cn(
            "relative flex items-end gap-2 rounded-2xl border border-border bg-card px-3 py-2 shadow-sm",
            "focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/15",
            "transition-all",
          )}
        >
          <textarea
            ref={ref}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={onKey}
            rows={1}
            placeholder=""
            className="max-h-[200px] flex-1 resize-none bg-transparent px-1 py-2 text-[15px] leading-6 outline-none placeholder:text-muted-foreground"
            aria-label="Chat input"
          />

          {streaming ? (
            <button
              type="button"
              onClick={onStop}
              aria-label="Dừng"
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground transition hover:opacity-90"
            >
              <Square className="h-4 w-4" fill="currentColor" />
            </button>
          ) : (
            <button
              type="button"
              onClick={send}
              disabled={!value.trim() || disabled}
              aria-label="Gửi"
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:bg-border disabled:text-muted-foreground"
            >
              <ArrowUp className="h-4 w-4" strokeWidth={2.5} />
            </button>
          )}
        </div>
        <p className="mt-2 px-1 text-center text-[11px] text-muted-foreground">
          Mô hình ngôn ngữ có thể sai. Hãy kiểm tra thông tin quan trọng.
        </p>
      </div>
    </div>
  );
}
