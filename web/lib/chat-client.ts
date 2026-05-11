import type { SSEEvent } from "./types";

/**
 * Call POST /api/chat/stream and parse the Server-Sent Events stream.
 * Invokes `onEvent` for each parsed event.
 */
export async function streamChat(
  question: string,
  onEvent: (evt: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: 5 }),
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`Chat stream failed: ${res.status} ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by \n\n.
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 2);
      if (!frame) continue;

      // Each frame is "data: <json>" (sometimes multi-line).
      const lines = frame.split("\n");
      const dataLines = lines
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trimStart());
      if (dataLines.length === 0) continue;
      const payload = dataLines.join("\n");

      try {
        const evt = JSON.parse(payload) as SSEEvent;
        onEvent(evt);
      } catch (err) {
        console.warn("Could not parse SSE payload", payload, err);
      }
    }
  }
}

export function pdfUrlFor(sourcePath: string | null | undefined): string | null {
  if (!sourcePath) return null;
  return `/api/file?path=${encodeURIComponent(sourcePath)}`;
}
