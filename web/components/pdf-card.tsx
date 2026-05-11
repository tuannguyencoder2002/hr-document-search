"use client";

import { X, ExternalLink } from "lucide-react";
import type { Source } from "@/lib/types";
import { pdfUrlFor } from "@/lib/chat-client";
import { cn } from "@/lib/utils";

type Props = {
  index: number;
  source: Source;
  onClose: () => void;
};

export function PdfCard({ index, source, onClose }: Props) {
  const url = pdfUrlFor(source.source_path);
  const isPdf = source.file_type === "pdf" && url;
  // PDF.js viewer in Chrome supports #page=N to open on a specific page.
  const viewerUrl = isPdf && source.page ? `${url}#page=${source.page}&zoom=page-width` : url;

  return (
    <div
      className={cn(
        "relative w-full overflow-hidden rounded-xl border border-border bg-card shadow-sm",
        "mx-auto",
      )}
    >
      <div className="flex items-center justify-between gap-2 border-b border-border bg-muted/40 px-4 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-primary/10 text-[11px] font-semibold text-primary">
            {index}
          </span>
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
            >
              <ExternalLink className="h-4 w-4" />
            </a>
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

      {isPdf ? (
        <iframe
          src={viewerUrl!}
          className="block h-[640px] w-full border-0"
          title={`PDF ${source.filename}`}
        />
      ) : (
        <div className="whitespace-pre-wrap px-4 py-3 text-sm text-muted-foreground">
          {source.excerpt}
        </div>
      )}
    </div>
  );
}
