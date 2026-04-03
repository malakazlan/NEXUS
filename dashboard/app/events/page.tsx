"use client";

import { useState, useMemo } from "react";
import { Header } from "@/components/layout/Header";
import { GlassCard } from "@/components/ui/GlassCard";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { useWebSocket } from "@/lib/useWebSocket";
import { EVENT_CATEGORIES, type NexusEvent } from "@/lib/types";
import { Radio, Pause, Play, ChevronDown, ChevronUp } from "lucide-react";

const FILTERS = [
  { key: "all",      label: "All"      },
  { key: "kernel",   label: "Kernel"   },
  { key: "agent",    label: "Agent"    },
  { key: "task",     label: "Task"     },
  { key: "tool",     label: "Tool"     },
  { key: "memory",   label: "Memory"   },
  { key: "approval", label: "Approval" },
];

export default function EventsPage() {
  const { events, connected } = useWebSocket();
  const [paused, setPaused]     = useState(false);
  const [filter, setFilter]     = useState("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const list = filter === "all" ? events : events.filter((e) => e.type.startsWith(filter));
    return paused ? [] : list;
  }, [events, filter, paused]);

  return (
    <>
      <Header
        title="Events"
        subtitle={`${events.length} captured`}
        actions={
          <Button
            variant="secondary" size="sm"
            icon={paused ? <Play size={12} /> : <Pause size={12} />}
            onClick={() => setPaused(!paused)}
          >
            {paused ? "Resume" : "Pause"}
          </Button>
        }
      />

      <div className="p-5">
        {/* Filter tabs */}
        <div
          className="mb-4 flex items-center gap-1 rounded-md p-1 w-fit"
          style={{ border: "1px solid var(--border)", background: "var(--surface)" }}
        >
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className="rounded px-2.5 py-1 text-[12px] font-medium transition-colors"
              style={{
                background: filter === f.key ? "var(--bg)" : "transparent",
                color:      filter === f.key ? "var(--text)" : "var(--text-3)",
                boxShadow:  filter === f.key ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
              }}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Log panel */}
        <GlassCard padding="none" className="overflow-hidden">
          {/* Terminal bar */}
          <div
            className="flex items-center justify-between px-4 py-2.5"
            style={{ borderBottom: "1px solid var(--border)", background: "var(--surface)" }}
          >
            <div className="flex items-center gap-3">
              <div className="flex gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#e4e4e7" }} />
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#e4e4e7" }} />
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#e4e4e7" }} />
              </div>
              <span className="font-mono text-[11px]" style={{ color: "var(--text-3)" }}>
                nexus/events
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ background: connected ? "var(--success)" : "var(--text-3)" }}
              />
              <span className="text-[11px]" style={{ color: "var(--text-3)" }}>
                {connected ? "streaming" : "offline"}
              </span>
            </div>
          </div>

          {/* Rows */}
          <div
            className="overflow-y-auto font-mono"
            style={{ maxHeight: "calc(100vh - 260px)", background: "var(--bg)" }}
          >
            {filtered.length === 0 ? (
              paused ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <Pause size={16} className="mb-2" style={{ color: "var(--text-3)" }} />
                  <p className="text-[12px]" style={{ color: "var(--text-3)" }}>
                    Paused — {events.length} buffered
                  </p>
                </div>
              ) : (
                <EmptyState
                  icon={<Radio size={16} />}
                  title="No events"
                  description="Boot the kernel and start agents to see events stream here."
                />
              )
            ) : (
              <>
                {filtered.map((event) => (
                  <EventLine
                    key={event.id} event={event}
                    expanded={expanded === event.id}
                    onToggle={() => setExpanded(expanded === event.id ? null : event.id)}
                  />
                ))}
                {connected && !paused && (
                  <div className="px-4 py-1.5">
                    <span className="cursor-blink text-[12px]" />
                  </div>
                )}
              </>
            )}
          </div>
        </GlassCard>
      </div>
    </>
  );
}

function EventLine({
  event, expanded, onToggle,
}: { event: NexusEvent; expanded: boolean; onToggle: () => void }) {
  const cat   = EVENT_CATEGORIES[event.type];
  const color = cat?.color ?? "#a1a1aa";
  const hasData = event.data && Object.keys(event.data).length > 0;

  const d = new Date(event.timestamp);
  const ts = `${d.getHours().toString().padStart(2,"0")}:${d.getMinutes().toString().padStart(2,"0")}:${d.getSeconds().toString().padStart(2,"0")}.${d.getMilliseconds().toString().padStart(3,"0")}`;

  return (
    <div>
      <button
        onClick={onToggle}
        className="group flex w-full items-center gap-3 px-4 py-1.5 text-left text-[12px] transition-colors"
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--surface)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
      >
        <span className="w-[76px] shrink-0 text-[10px]" style={{ color: "var(--text-3)" }}>{ts}</span>
        <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: color }} />
        <span
          className="shrink-0 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider"
          style={{ color, background: `${color}18` }}
        >
          {cat?.label ?? "SYS"}
        </span>
        <span style={{ color: "var(--text-2)" }}>{event.type}</span>
        <span style={{ color: "var(--text-3)" }}>{event.source}</span>
        {hasData && (
          <span className="ml-auto opacity-0 transition-opacity group-hover:opacity-100" style={{ color: "var(--text-3)" }}>
            {expanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          </span>
        )}
      </button>
      {expanded && hasData && (
        <div className="ml-[104px] mr-4 mb-1">
          <CodeBlock code={JSON.stringify(event.data, null, 2)} language="json" maxHeight="180px" />
        </div>
      )}
    </div>
  );
}
