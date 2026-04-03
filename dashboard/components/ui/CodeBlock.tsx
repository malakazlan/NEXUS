"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";

interface CodeBlockProps {
  code: string;
  language?: string;
  maxHeight?: string;
}

export function CodeBlock({ code, language = "json", maxHeight = "300px" }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-md overflow-hidden" style={{ border: "1px solid var(--border)" }}>
      <div
        className="flex items-center justify-between px-3 py-1.5"
        style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)" }}
      >
        <span className="font-mono text-[10px] uppercase tracking-wider" style={{ color: "var(--text-3)" }}>
          {language}
        </span>
        <button
          onClick={handleCopy}
          className="flex h-5 w-5 items-center justify-center rounded transition-colors hover:bg-zinc-100"
          style={{ color: "var(--text-3)" }}
        >
          {copied ? <Check size={11} /> : <Copy size={11} />}
        </button>
      </div>
      <pre
        className="overflow-auto p-3 text-[12px] leading-relaxed font-mono"
        style={{ maxHeight, background: "var(--surface)", color: "var(--text-2)" }}
      >
        <code>{code}</code>
      </pre>
    </div>
  );
}
