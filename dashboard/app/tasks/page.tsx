"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { GlassCard } from "@/components/ui/GlassCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { TextArea } from "@/components/ui/Input";
import { EmptyState } from "@/components/ui/EmptyState";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { useFetch } from "@/lib/useFetch";
import { submitTask } from "@/lib/api";
import { timeAgo, truncate } from "@/lib/utils";
import type { Task } from "@/lib/types";
import {
  ListTodo, Plus, Clock, ChevronDown, ChevronUp,
  AlertCircle, CheckCircle2, User, ArrowUpDown,
} from "lucide-react";

const P_COLOR: Record<number, string> = {
  1: "#dc2626", 2: "#dc2626", 3: "#ea580c",
  4: "#d97706", 5: "#71717a", 6: "#71717a",
  7: "#71717a",  8: "#2563eb", 9: "#2563eb", 10: "#2563eb",
};

export default function TasksPage() {
  const { data: tasks, mutate } = useFetch<Task[]>("/tasks");
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating]     = useState(false);
  const [description, setDescription] = useState("");
  const [priority, setPriority]     = useState(5);
  const [expanded, setExpanded]     = useState<string | null>(null);
  const [sortBy, setSortBy]         = useState<"time" | "priority">("time");

  const sorted = [...(tasks ?? [])].sort((a, b) =>
    sortBy === "priority"
      ? a.priority - b.priority
      : new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const counts = {
    pending:   tasks?.filter((t) => t.status === "pending").length   ?? 0,
    running:   tasks?.filter((t) => t.status === "running").length   ?? 0,
    completed: tasks?.filter((t) => t.status === "completed").length ?? 0,
    failed:    tasks?.filter((t) => t.status === "failed").length    ?? 0,
  };

  const handleCreate = async () => {
    if (!description.trim()) return;
    setCreating(true);
    try {
      await submitTask(description, priority);
      await mutate();
      setShowCreate(false);
      setDescription("");
      setPriority(5);
    } finally { setCreating(false); }
  };

  return (
    <>
      <Header
        title="Tasks"
        subtitle={`${tasks?.length ?? 0} total`}
        actions={
          <Button icon={<Plus size={13} />} onClick={() => setShowCreate(true)}>
            New Task
          </Button>
        }
      />

      <div className="p-5">
        {/* Summary */}
        <div
          className="mb-4 flex items-center justify-between rounded-md px-4 py-2.5"
          style={{ border: "1px solid var(--border)", background: "var(--surface)" }}
        >
          <div className="flex items-center gap-5">
            {Object.entries(counts).map(([s, n]) => (
              <div key={s} className="flex items-center gap-2">
                <StatusBadge status={s} />
                <span className="text-[12px] font-semibold" style={{ color: "var(--text)" }}>{n}</span>
              </div>
            ))}
          </div>
          <button
            className="flex items-center gap-1.5 text-[12px] transition-opacity hover:opacity-60"
            style={{ color: "var(--text-3)" }}
            onClick={() => setSortBy(sortBy === "time" ? "priority" : "time")}
          >
            <ArrowUpDown size={12} />
            {sortBy === "time" ? "Sort by priority" : "Sort by time"}
          </button>
        </div>

        {sorted.length === 0 ? (
          <EmptyState
            icon={<ListTodo size={18} />}
            title="No tasks"
            description="Submit a task and NEXUS agents will pick it up automatically."
            action={<Button icon={<Plus size={13} />} onClick={() => setShowCreate(true)}>Submit Task</Button>}
          />
        ) : (
          <div className="space-y-1.5">
            {sorted.map((task) => (
              <TaskRow
                key={task.id}
                task={task}
                expanded={expanded === task.id}
                onToggle={() => setExpanded(expanded === task.id ? null : task.id)}
              />
            ))}
          </div>
        )}
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Submit Task">
        <div className="space-y-4">
          <TextArea
            label="Description"
            placeholder="Research the top 5 trending AI papers this week and summarize key findings…"
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />

          <div>
            <label className="mb-1.5 block text-[12px] font-medium" style={{ color: "var(--text-2)" }}>
              Priority —{" "}
              <span style={{ color: P_COLOR[priority] }}>{priority}</span>
              <span className="ml-1" style={{ color: "var(--text-3)" }}>(1 = highest)</span>
            </label>
            <input
              type="range" min={1} max={10} value={priority}
              onChange={(e) => setPriority(Number(e.target.value))}
              className="w-full accent-zinc-900"
            />
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <Button variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={creating || !description.trim()}>
              {creating ? "Submitting…" : "Submit"}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}

function TaskRow({
  task, expanded, onToggle,
}: { task: Task; expanded: boolean; onToggle: () => void }) {
  const pc = P_COLOR[task.priority] ?? "#71717a";

  return (
    <div
      className="rounded-md overflow-hidden"
      style={{ border: "1px solid var(--border)", background: "var(--bg)" }}
    >
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors"
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--surface)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
      >
        <span
          className="shrink-0 rounded px-1.5 py-0.5 font-mono text-[11px] font-semibold"
          style={{ color: pc, background: `${pc}12` }}
        >
          P{task.priority}
        </span>

        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px]" style={{ color: "var(--text)" }}>{task.description}</p>
          <div className="mt-0.5 flex items-center gap-3 text-[11px]" style={{ color: "var(--text-3)" }}>
            <span className="flex items-center gap-1"><Clock size={9} />{timeAgo(task.created_at)}</span>
            {task.assigned_to && (
              <span className="flex items-center gap-1"><User size={9} />{truncate(task.assigned_to, 20)}</span>
            )}
          </div>
        </div>

        <StatusBadge status={task.status} />
        <span className="ml-1" style={{ color: "var(--text-3)" }}>
          {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </span>
      </button>

      {expanded && (
        <div
          className="px-4 pb-4 pt-3 space-y-3"
          style={{ borderTop: "1px solid var(--border-subtle)" }}
        >
          <div className="grid grid-cols-3 gap-3 text-[12px]">
            <div>
              <p style={{ color: "var(--text-3)" }}>Task ID</p>
              <p className="font-mono mt-0.5" style={{ color: "var(--text-2)" }}>{task.id}</p>
            </div>
            {task.assigned_to && (
              <div>
                <p style={{ color: "var(--text-3)" }}>Assigned to</p>
                <p className="font-mono mt-0.5" style={{ color: "var(--text-2)" }}>{task.assigned_to}</p>
              </div>
            )}
            {task.completed_at && (
              <div>
                <p style={{ color: "var(--text-3)" }}>Completed</p>
                <p className="mt-0.5" style={{ color: "var(--text-2)" }}>{timeAgo(task.completed_at)}</p>
              </div>
            )}
          </div>

          {task.result != null && (
            <div>
              <div className="mb-1.5 flex items-center gap-1.5">
                <CheckCircle2 size={12} style={{ color: "var(--success)" }} />
                <span className="text-[11px] font-medium" style={{ color: "var(--success)" }}>Result</span>
              </div>
              <CodeBlock
                code={typeof task.result === "string" ? task.result : JSON.stringify(task.result, null, 2)}
                maxHeight="200px"
              />
            </div>
          )}

          {task.error && (
            <div>
              <div className="mb-1.5 flex items-center gap-1.5">
                <AlertCircle size={12} style={{ color: "var(--danger)" }} />
                <span className="text-[11px] font-medium" style={{ color: "var(--danger)" }}>Error</span>
              </div>
              <div className="rounded-md px-3 py-2" style={{ background: "#fef2f2", border: "1px solid #fecaca" }}>
                <p className="font-mono text-[12px]" style={{ color: "#991b1b" }}>{task.error}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
