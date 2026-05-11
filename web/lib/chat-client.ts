import type { SSEEvent } from "./types";

// Toggle via localStorage.setItem("ds.debug", "1") in DevTools.
const DEBUG =
  typeof window !== "undefined" &&
  window.localStorage?.getItem("ds.debug") !== "0";

function dlog(...args: unknown[]) {
  if (DEBUG) console.log("[DS chat]", ...args);
}
function dwarn(...args: unknown[]) {
  if (DEBUG) console.warn("[DS chat]", ...args);
}

/**
 * Call POST /api/chat/stream and parse the Server-Sent Events stream.
 * Invokes `onEvent` for each parsed event.
 *
 * Enable verbose logs: `localStorage.setItem("ds.debug", "1")` in DevTools.
 * Disable:             `localStorage.setItem("ds.debug", "0")`
 */
export async function streamChat(
  question: string,
  onEvent: (evt: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const reqId = `req_${Date.now().toString(36)}`;
  const started = performance.now();
  dlog(`[${reqId}] POST /api/chat/stream —`, question.slice(0, 120));

  const res = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: 5 }),
    signal,
  });

  dlog(`[${reqId}] HTTP ${res.status} ${res.statusText}`);

  if (!res.ok || !res.body) {
    throw new Error(`Chat stream failed: ${res.status} ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let firstTokenAt: number | null = null;
  let deltaCount = 0;
  let totalChars = 0;
  let gotSources = false;

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, idx).trim();
        buffer = buffer.slice(idx + 2);
        if (!frame) continue;

        const lines = frame.split("\n");
        const dataLines = lines
          .filter((l) => l.startsWith("data:"))
          .map((l) => l.slice(5).trimStart());
        if (dataLines.length === 0) continue;
        const payload = dataLines.join("\n");

        try {
          const evt = JSON.parse(payload) as SSEEvent;

          // Per-event logs (compact)
          switch (evt.type) {
            case "sources":
              gotSources = true;
              dlog(
                `[${reqId}] 📚 sources (${evt.sources.length}) — ` +
                  `search=${evt.stage_ms.search}ms rerank=${evt.stage_ms.rerank}ms`,
              );
              if (evt.sources.length > 0) {
                console.table(
                  evt.sources.map((s, i) => ({
                    "#": i + 1,
                    file: s.filename,
                    page: s.page,
                    score: s.score?.toFixed(3),
                  })),
                );
              }
              break;
            case "delta":
              if (firstTokenAt === null) {
                firstTokenAt = performance.now() - started;
                dlog(
                  `[${reqId}] 💬 first token after ${firstTokenAt.toFixed(0)}ms`,
                );
              }
              deltaCount += 1;
              totalChars += evt.content.length;
              break;
            case "done": {
              const tokPerSec = deltaCount
                ? (deltaCount / (evt.stage_ms.generate || 1)) * 1000
                : 0;
              dlog(
                `[${reqId}] ✅ done — total=${evt.latency_ms}ms, ` +
                  `generate=${evt.stage_ms.generate}ms, ` +
                  `~${deltaCount} chunks, ${totalChars} chars, ` +
                  `${tokPerSec.toFixed(1)} chunks/s`,
              );
              if (tokPerSec > 0 && tokPerSec < 10) {
                dwarn(
                  `[${reqId}] generation speed is low. Check Ollama GPU offload.`,
                );
              }
              break;
            }
            case "error":
              dwarn(`[${reqId}] ❌ error — ${evt.message}`);
              break;
          }

          onEvent(evt);
        } catch (err) {
          dwarn(`[${reqId}] unparsable SSE frame:`, payload, err);
        }
      }
    }
  } catch (err) {
    if ((err as Error).name === "AbortError") {
      dlog(`[${reqId}] aborted by user`);
    } else {
      dwarn(`[${reqId}] stream failed`, err);
    }
    throw err;
  } finally {
    if (!gotSources) {
      dwarn(`[${reqId}] closed without receiving any sources event`);
    }
    dlog(
      `[${reqId}] stream closed — duration=${(performance.now() - started).toFixed(0)}ms`,
    );
  }
}

export function pdfUrlFor(sourcePath: string | null | undefined): string | null {
  if (!sourcePath) return null;
  return `/api/file?path=${encodeURIComponent(sourcePath)}`;
}
