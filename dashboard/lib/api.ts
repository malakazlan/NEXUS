import type {
  Agent,
  Task,
  Tool,
  HealthStatus,
  MemoryEntry,
  NexusEvent,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ─── Health ──────────────────────────────────────────────────────────────────

export const fetchHealth = () => request<HealthStatus>("/health");

// ─── Agents ──────────────────────────────────────────────────────────────────

export const fetchAgents = () => request<Agent[]>("/agents");

export const spawnAgent = (body: {
  type?: string;
  role?: string;
  capabilities?: string[];
  tools?: string[];
  model?: string;
  token_budget?: number;
}) => request<Agent>("/agents", { method: "POST", body: JSON.stringify(body) });

export const terminateAgent = (id: string) =>
  request<{ status: string }>(`/agents/${id}`, { method: "DELETE" });

// ─── Tasks ───────────────────────────────────────────────────────────────────

export const fetchTasks = (status?: string) =>
  request<Task[]>(`/tasks${status ? `?status=${status}` : ""}`);

export const submitTask = (description: string, priority = 5) =>
  request<Task>("/tasks", {
    method: "POST",
    body: JSON.stringify({ description, priority }),
  });

export const submitTaskAsync = (description: string, priority = 5) =>
  request<Task>("/tasks/async", {
    method: "POST",
    body: JSON.stringify({ description, priority }),
  });

// ─── Tools ───────────────────────────────────────────────────────────────────

export const fetchTools = () => request<Tool[]>("/tools");

export const createTool = (body: {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  tool_code: string;
  test_code: string;
}) =>
  request<{ status: string; tool_name: string }>("/tools", {
    method: "POST",
    body: JSON.stringify(body),
  });

// ─── Events ──────────────────────────────────────────────────────────────────

export const fetchEvents = (limit = 50) =>
  request<NexusEvent[]>(`/events?limit=${limit}`);

// ─── Memory ──────────────────────────────────────────────────────────────────

export const fetchMemoryKeys = () => request<string[]>("/memory");

export const fetchMemory = (key: string) =>
  request<MemoryEntry>(`/memory/${encodeURIComponent(key)}`);

export const writeMemory = (key: string, value: unknown) =>
  request<{ status: string }>("/memory", {
    method: "POST",
    body: JSON.stringify({ key, value }),
  });

// ─── Approval ────────────────────────────────────────────────────────────────

export const respondApproval = (requestId: string, approved: boolean) =>
  request<{ status: string }>(`/approval/${requestId}`, {
    method: "POST",
    body: JSON.stringify({ approved }),
  });
