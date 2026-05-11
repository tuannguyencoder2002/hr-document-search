import { FileSearch } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-30 w-full border-b border-border bg-background/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-3 px-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <FileSearch className="h-5 w-5" strokeWidth={2.5} />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-[15px] font-semibold tracking-tight text-foreground">
            Document Search Assistant
          </span>
          <span className="text-[11px] text-muted-foreground">
            Local RAG · Qwen3 · bge-m3
          </span>
        </div>
      </div>
    </header>
  );
}
