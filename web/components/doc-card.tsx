"use client";

import { X, ExternalLink, FileText, FileType2, Loader2, FolderOpen } from "lucide-react";
import { useState } from "react";
import type { Source } from "@/lib/types";
import { previewUrlFor } from "@/lib/chat-client";
import { cn } from "@/lib/utils";

type Props = {
  index: number;
  source: Source;
  onClose: () => void;
};

export function DocCard({ index, source, onClose }: Props) {
  const { url, kind } = previewUrlFor(source.source_path, source.file_type);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

  // PDF.js viewer in Chrome supports #page=N for deep-linking the page.
  const pageParam =
    kind === "pdf" && source.page ? `#page=${source.page}&zoom=page-width` : "";
  const iframeSrc = url ? `${url}${pageParam}` : "";

  const ext = (source.file_type || "").toLowerCase();
  const Icon = ext === "pdf" ? FileType2 : FileText;

  return (
    <div
      className={cn(
        "group relative mx-auto w-full overflow-hidden rounded-xl border border-border bg-card shadow-sm",
        "animate-in fade-in slide-in-from-bottom-2 duration-300",
        "hover:border-primary/30 hover:shadow-md transition-all",
      )}
    >
      <div className="flex items-center justify-between gap-2 border-b border-border bg-muted/40 px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/10 text-xs font-semibold text-primary">
            {index}
          </span>
          <Icon className="h-4 w-4 shrink-0 text-muted-foreground" strokeWidth={2} />
          <span className="truncate text-sm font-medium text-foreground">
            {source.filename}
          </span>
          {source.page ? (
            <span className="shrink-0 rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              Trang {source.page}
            </span>
          ) : null}
          <span className="shrink-0 rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            {source.score.toFixed(3)}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {url ? (
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition hover:bg-accent hover:text-foreground"
              title="Mở trong tab mới"
              aria-label="Mở trong tab mới"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          ) : null}
          {source.source_path ? (
            <button
              type="button"
              onClick={() => {
                fetch(`http://localhost:8000/open-file?path=${encodeURIComponent(source.source_path!)}`)
                  .then((r) => { if (!r.ok) console.warn("[DS] open-file failed:", r.status); })
                  .catch((e) => console.warn("[DS] open-file error:", e));
              }}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition hover:bg-accent hover:text-foreground"
              title="Mở file gốc trên máy"
              aria-label="Mở file gốc trên máy"
            >
              <FolderOpen className="h-4 w-4" />
            </button>
          ) : null}
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng tài liệu này"
            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition hover:bg-destructive hover:text-destructive-foreground"
            title="Đóng"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {kind === "none" || !url ? (
        <div className="whitespace-pre-wrap px-4 py-3 text-sm text-muted-foreground">
          {source.excerpt || "Không có xem trước cho định dạng này."}
        </div>
      ) : (
        <div className="relative">
          {!loaded && !failed && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 bg-card/80 backdrop-blur-sm animate-in fade-in duration-200">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <span className="text-xs text-muted-foreground">Đang tải tài liệu…</span>
            </div>
          )}
          {failed && (
            <div className="flex flex-col items-center justify-center gap-2 px-4 py-12 text-sm text-muted-foreground">
              <span>Không xem trước được. {source.excerpt}</span>
              <a href={url} target="_blank" rel="noreferrer" className="underline">
                Mở trong tab mới
              </a>
            </div>
          )}
          <iframe
            src={iframeSrc}
            className={cn(
              "block h-[640px] w-full border-0 transition-opacity duration-300",
              loaded ? "opacity-100" : "opacity-0",
            )}
            title={`Preview ${source.filename}`}
            onLoad={() => setLoaded(true)}
            onError={() => setFailed(true)}
          />
        </div>
      )}
    </div>
  );
}
