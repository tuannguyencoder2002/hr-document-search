"use client";

import { ArrowUp, Square, ImagePlus, X } from "lucide-react";
import {
  ChangeEvent,
  DragEvent,
  KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import { cn } from "@/lib/utils";

type Props = {
  onSubmit: (value: string, image?: File) => void;
  onStop?: () => void;
  disabled?: boolean;
  streaming?: boolean;
};

const ACCEPTED_IMAGES = ["image/jpeg", "image/png", "image/webp", "image/bmp", "image/gif"];

export function ChatInput({ onSubmit, onStop, disabled, streaming }: Props) {
  const [value, setValue] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Auto-resize textarea.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }, [value]);

  // Generate preview URL for attached image.
  useEffect(() => {
    if (!image) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(image);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [image]);

  const send = () => {
    const trimmed = value.trim();
    if (!trimmed && !image) return;
    if (disabled) return;
    onSubmit(trimmed, image || undefined);
    setValue("");
    setImage(null);
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const handleFile = (file: File | null | undefined) => {
    if (!file) return;
    if (!ACCEPTED_IMAGES.includes(file.type)) return;
    if (file.size > 10 * 1024 * 1024) return; // 10MB max
    setImage(file);
    console.log("[DS ui] image attached:", file.name, file.type, file.size);
  };

  const onFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    handleFile(e.target.files?.[0]);
    e.target.value = ""; // reset so same file can be re-selected
  };

  // Paste image from clipboard.
  const onPaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of Array.from(items)) {
      if (item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) {
          handleFile(file);
          e.preventDefault();
          return;
        }
      }
    }
  };

  // Drag & drop.
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer?.files?.[0];
    if (file && file.type.startsWith("image/")) {
      handleFile(file);
    }
  };

  return (
    <div className="sticky bottom-0 left-0 right-0 border-t border-border bg-background/95 backdrop-blur">
      <div className="mx-auto max-w-3xl px-4 py-3">
        {/* Image preview chip */}
        {preview && image && (
          <div className="mb-2 flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-3 py-2 animate-in fade-in slide-in-from-bottom-1 duration-200">
            <img
              src={preview}
              alt="Attached"
              className="h-12 w-12 rounded-md object-cover border border-border"
            />
            <span className="flex-1 truncate text-sm text-muted-foreground">
              {image.name}
            </span>
            <button
              type="button"
              onClick={() => setImage(null)}
              className="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-destructive hover:text-destructive-foreground transition"
              aria-label="Xóa ảnh"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          className={cn(
            "relative flex items-end gap-2 rounded-2xl border bg-card px-3 py-2 shadow-sm",
            "focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/15",
            "transition-all",
            dragOver
              ? "border-primary ring-2 ring-primary/20 bg-primary/5"
              : "border-border",
          )}
        >
          {/* Image attach button */}
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={disabled || streaming}
            aria-label="Đính kèm ảnh"
            title="Đính kèm ảnh để tìm hình tương tự"
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition hover:bg-accent hover:text-foreground disabled:opacity-40"
          >
            <ImagePlus className="h-5 w-5" />
          </button>
          <input
            ref={fileRef}
            type="file"
            accept={ACCEPTED_IMAGES.join(",")}
            onChange={onFileChange}
            className="hidden"
            aria-hidden
          />

          <textarea
            ref={ref}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={onKey}
            onPaste={onPaste}
            rows={1}
            placeholder={image ? "Mô tả thêm (tùy chọn)…" : ""}
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
              disabled={(!value.trim() && !image) || disabled}
              aria-label="Gửi"
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:bg-border disabled:text-muted-foreground"
            >
              <ArrowUp className="h-4 w-4" strokeWidth={2.5} />
            </button>
          )}
        </div>
        <p className="mt-2 px-1 text-center text-[11px] text-muted-foreground">
          Gửi ảnh để tìm hình tương tự trong tài liệu · Ctrl+V dán ảnh từ clipboard
        </p>
      </div>
    </div>
  );
}
