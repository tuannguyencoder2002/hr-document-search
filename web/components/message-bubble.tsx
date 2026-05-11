"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User } from "lucide-react";
import type { ChatMessage } from "@/lib/types";
import { DocCard } from "./doc-card";
import { TypingIndicator } from "./typing-indicator";
import { formatMs, cn } from "@/lib/utils";

type Props = {
  message: ChatMessage;
  onHideSource: (messageId: string, idx: number) => void;
};

export function MessageBubble({ message, onHideSource }: Props) {
  const isUser = message.role === "user";
  return (
    <div className="w-full">
      <div
        className={cn(
          "flex w-full gap-3",
          isUser ? "justify-end" : "justify-start",
        )}
      >
        {!isUser && (
          <div className="mt-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-border bg-card text-primary shadow-sm">
            <Bot className="h-6 w-6" strokeWidth={2} />
          </div>
        )}

        <div
          className={cn(
            "max-w-[85%] min-w-0",
            isUser
              ? "rounded-2xl bg-secondary px-4 py-2.5 text-foreground"
              : "text-foreground",
          )}
        >
          {message.streaming && !message.content ? (
            <TypingIndicator />
          ) : (
            <div className="prose-tight text-[15px] leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content || ""}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {isUser && (
          <div className="mt-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm">
            <User className="h-6 w-6" strokeWidth={2} />
          </div>
        )}
      </div>

      {/* Sources rendered inline, centered under the assistant message */}
      {!isUser && message.sources && message.sources.length > 0 && (
        <div className="ml-14 mt-4 space-y-4">
          {message.sources.map((src, i) => {
            if (message.hidden_sources?.[i]) return null;
            return (
              <DocCard
                key={`${message.id}-src-${i}`}
                index={i + 1}
                source={src}
                onClose={() => onHideSource(message.id, i)}
              />
            );
          })}

          {(message.latency_ms || message.stage_ms) && !message.streaming && (
            <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
              {message.latency_ms !== undefined && (
                <span>⏱ {formatMs(message.latency_ms)}</span>
              )}
              {message.stage_ms?.search !== undefined && (
                <span>search {formatMs(message.stage_ms.search)}</span>
              )}
              {message.stage_ms?.rerank !== undefined && (
                <span>rerank {formatMs(message.stage_ms.rerank)}</span>
              )}
              {message.stage_ms?.generate !== undefined && (
                <span>generate {formatMs(message.stage_ms.generate)}</span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
