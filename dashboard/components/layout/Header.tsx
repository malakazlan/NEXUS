"use client";

import { useWebSocket } from "@/lib/useWebSocket";
import { RefreshCw } from "lucide-react";

interface HeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function Header({ title, subtitle, actions }: HeaderProps) {
  const { connected, reconnecting } = useWebSocket();

  return (
    <header
      className="flex h-12 items-center justify-between px-5"
      style={{ borderBottom: "1px solid var(--border)", background: "var(--bg)" }}
    >
      <div className="flex items-baseline gap-2.5">
        <h1 className="text-[14px] font-semibold" style={{ color: "var(--text)" }}>
          {title}
        </h1>
        {subtitle && (
          <span className="text-[12px]" style={{ color: "var(--text-3)" }}>
            {subtitle}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        {actions}

        <div className="flex items-center gap-1.5">
          {reconnecting ? (
            <>
              <RefreshCw size={11} className="animate-spin" style={{ color: "var(--warning)" }} />
              <span className="text-[11px]" style={{ color: "var(--warning)" }}>Reconnecting</span>
            </>
          ) : (
            <>
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ background: connected ? "var(--success)" : "var(--text-3)" }}
              />
              <span className="text-[11px]" style={{ color: "var(--text-3)" }}>
                {connected ? "Live" : "Offline"}
              </span>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
