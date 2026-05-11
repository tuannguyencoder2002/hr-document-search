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

  const hideSource = useCallback((messageId: string, idx: number) => {
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
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
    setMessages((prev) =>
      prev.map((m) => (m.streaming ? { ...m, streaming: false } : m)),
    );
  }, []);

  const submit = useCallback(async (question: string) => {
    if (streaming) return;
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
