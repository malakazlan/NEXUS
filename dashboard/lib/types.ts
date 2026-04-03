// ─── Agent ───────────────────────────────────────────────────────────────────

export type AgentStatus =
  | "idle"
  | "running"
  | "completed"
  | "failed"
  | "terminated";

export interface Agent {
  id: string;
  type: string;
  status: AgentStatus;
  capabilities: string[];
  tools: string[];
  model: string;
  token_budget: number;
  tokens_used: number;
  current_task: string | null;
}

// ─── Task ────────────────────────────────────────────────────────────────────

export type TaskStatus =
  | "pending"
  | "assigned"
  | "running"
  | "completed"
  | "failed";

export interface Task {
  id: string;
  description: string;
  priority: number;
  status: TaskStatus;
  assigned_to: string | null;
  parent_task_id: string | null;
  result: unknown;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

// ─── Tool ────────────────────────────────────────────────────────────────────

export interface Tool {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  is_builtin: boolean;
  created_by: string | null;
  usage_count: number;
  created_at: string;
}

// ─── Event ───────────────────────────────────────────────────────────────────

export interface NexusEvent {
  id: string;
  type: string;
  source: string;
  data: Record<string, unknown>;
  timestamp: string;
}

// ─── Health ──────────────────────────────────────────────────────────────────

export interface HealthStatus {
  status: string;
  version: string;
  agents: number;
  tools: number;
}

// ─── Memory ──────────────────────────────────────────────────────────────────

export interface MemoryEntry {
  key: string;
  value: unknown;
}

// ─── Approval ────────────────────────────────────────────────────────────────

export interface ApprovalRequest {
  id: string;
  action: string;
  description: string;
  details: Record<string, unknown>;
  source: string;
}

// ─── Event type categories for coloring/icons ────────────────────────────────

export const EVENT_CATEGORIES: Record<string, { color: string; label: string }> = {
  "kernel.boot":         { color: "#22d3ee", label: "Kernel" },
  "kernel.shutdown":     { color: "#94a3b8", label: "Kernel" },
  "agent.spawned":       { color: "#34d399", label: "Agent" },
  "agent.status_changed":{ color: "#fbbf24", label: "Agent" },
  "agent.completed":     { color: "#34d399", label: "Agent" },
  "agent.failed":        { color: "#f87171", label: "Agent" },
  "agent.terminated":    { color: "#94a3b8", label: "Agent" },
  "agent.message":       { color: "#a78bfa", label: "IPC" },
  "task.created":        { color: "#60a5fa", label: "Task" },
  "task.assigned":       { color: "#fbbf24", label: "Task" },
  "task.completed":      { color: "#34d399", label: "Task" },
  "task.failed":         { color: "#f87171", label: "Task" },
  "tool.proposed":       { color: "#c084fc", label: "Tool" },
  "tool.testing":        { color: "#fbbf24", label: "Tool" },
  "tool.created":        { color: "#34d399", label: "Tool" },
  "tool.failed":         { color: "#f87171", label: "Tool" },
  "memory.write":        { color: "#60a5fa", label: "Memory" },
  "memory.read":         { color: "#94a3b8", label: "Memory" },
  "approval.requested":  { color: "#fbbf24", label: "Approval" },
  "approval.granted":    { color: "#34d399", label: "Approval" },
  "approval.denied":     { color: "#f87171", label: "Approval" },
};
