export type Source = {
  document_id: string | null;
  filename: string;
  source_path: string | null;
  page: number | null;
  file_type: string | null;
  score: number;
  excerpt: string;
};

export type StageMs = {
  search?: number;
  rerank?: number;
  generate?: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  stage_ms?: StageMs;
  latency_ms?: number;
  // Per-source "hidden by user" flags so the ✕ close button can hide
  // individual PDF previews without touching chat history.
  hidden_sources?: Record<number, boolean>;
  streaming?: boolean;
};

export type SSEEvent =
  | { type: "sources"; sources: Source[]; stage_ms: StageMs }
  | { type: "delta"; content: string }
  | { type: "done"; latency_ms: number; stage_ms: StageMs }
  | { type: "error"; message: string };
