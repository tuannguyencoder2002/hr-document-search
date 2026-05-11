"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Header } from "@/components/header";
import { Welcome } from "@/components/welcome";
import { MessageBubble } from "@/components/message-bubble";
import { ChatInput } from "@/components/chat-input";
import { streamChat } from "@/lib/chat-client";
import type { ChatMessage } from "@/lib/types";

function uid(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Keep the view pinned to the latest message.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  // One-time startup banner with debug-toggle hint.
  useEffect(() => {
    console.log(
      "%c[DS] Document Search Assistant UI",
      "font-weight:600;color:#0F172A;",
    );
    console.log(
      "%c[DS] verbose logs: localStorage.setItem('ds.debug','1')  |  disable: '0'",
      "color:#64748B;",
    );
  }, []);

  const hideSource = useCallback((messageId: string, idx: number) => {
    console.log("[DS ui] hide source", { messageId, idx });
    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId
          ? {
              ...m,
              hidden_sources: { ...(m.hidden_sources || {}), [idx]: true },
            }
          : m,
      ),
    );
  }, []);

  const stop = useCallback(() => {
    console.log("[DS ui] stop requested");
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
    setMessages((prev) =>
      prev.map((m) => (m.streaming ? { ...m, streaming: false } : m)),
    );
  }, []);

  const submitImageSearch = useCallback(async (text: string, image: File) => {
    const userMsg: ChatMessage = {
      id: uid(),
      role: "user",
      content: text || "🖼 Tìm ảnh tương tự",
    };
    const assistantMsg: ChatMessage = {
      id: uid(),
      role: "assistant",
      content: "",
      streaming: true,
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setStreaming(true);

    try {
      const formData = new FormData();
      formData.append("file", image);
      formData.append("top_k", "5");

      console.log("[DS ui] POST /api/image-search", image.name);
      const res = await fetch("/api/image-search", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        throw new Error(`Image search failed: ${res.status}`);
      }
      const data = await res.json();
      console.log("[DS ui] image-search results:", data.total, "hits in", data.latency_ms, "ms");

      // Convert image-search results to Source format for DocCard rendering.
      const sources = (data.results || []).map((r: any) => ({
        document_id: r.id,
        filename: r.filename || "unknown",
        source_path: r.source_path,
        page: r.page,
        file_type: r.source_path?.endsWith(".pdf") ? "pdf" : "docx",
        score: r.score,
        excerpt: r.caption || "",
      }));

      const content = data.total > 0
        ? `Tìm thấy **${data.total}** ảnh tương tự trong tài liệu (${data.latency_ms} ms).`
        : "Không tìm thấy ảnh tương tự trong tài liệu đã index.";

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsg.id
            ? { ...m, content, sources, streaming: false, latency_ms: data.latency_ms }
            : m,
        ),
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      console.warn("[DS ui] image-search error:", msg);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsg.id
            ? { ...m, content: `> **Lỗi:** ${msg}`, streaming: false }
            : m,
        ),
      );
    } finally {
      setStreaming(false);
    }
  }, []);

  const submit = useCallback(async (question: string, image?: File) => {
    if (streaming) return;
    console.log("[DS ui] submit", question.slice(0, 120), image ? `+image(${image.name})` : "");

    // If an image is attached, route to image-search endpoint instead of text RAG.
    if (image) {
      await submitImageSearch(question, image);
      return;
    }

    const userMsg: ChatMessage = {
      id: uid(),
      role: "user",
      content: question,
    };
    const assistantMsg: ChatMessage = {
      id: uid(),
      role: "assistant",
      content: "",
      streaming: true,
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamChat(
        question,
        (evt) => {
          if (evt.type === "sources") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, sources: evt.sources, stage_ms: evt.stage_ms }
                  : m,
              ),
            );
          } else if (evt.type === "delta") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, content: (m.content || "") + evt.content }
                  : m,
              ),
            );
          } else if (evt.type === "done") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? {
                      ...m,
                      streaming: false,
                      latency_ms: evt.latency_ms,
                      stage_ms: evt.stage_ms,
                    }
                  : m,
              ),
            );
          } else if (evt.type === "error") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? {
                      ...m,
                      streaming: false,
                      content:
                        (m.content || "") +
                        `\n\n> **Lỗi:** ${evt.message}`,
                    }
                  : m,
              ),
            );
          }
        },
        controller.signal,
      );
    } catch (err) {
      if ((err as any)?.name !== "AbortError") {
        const message =
          err instanceof Error ? err.message : "Unknown error";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? {
                  ...m,
                  streaming: false,
                  content: `> **Không gọi được server:** ${message}`,
                }
              : m,
          ),
        );
      }
    } finally {
      abortRef.current = null;
      setStreaming(false);
    }
  }, [streaming]);

  const hasMessages = messages.length > 0;

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header />

      <main className="flex flex-1 flex-col">
        {!hasMessages ? (
          <Welcome onPick={submit} />
        ) : (
          <div className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">
            <div className="flex flex-col gap-8">
              {messages.map((m) => (
                <MessageBubble
                  key={m.id}
                  message={m}
                  onHideSource={hideSource}
                />
              ))}
              <div ref={bottomRef} />
            </div>
          </div>
        )}

        <ChatInput
          onSubmit={submit}
          onStop={stop}
          streaming={streaming}
          disabled={streaming}
        />
      </main>
    </div>
  );
}
