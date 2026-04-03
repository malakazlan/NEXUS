"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { GlassCard } from "@/components/ui/GlassCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { EmptyState } from "@/components/ui/EmptyState";
import { useFetch } from "@/lib/useFetch";
import { spawnAgent, terminateAgent } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import type { Agent } from "@/lib/types";
import { Bot, Plus, Trash2, Sparkles } from "lucide-react";

const AGENT_TYPES = [
  { value: "orchestrator", label: "Orchestrator", desc: "Decomposes & delegates tasks" },
  { value: "researcher",   label: "Researcher",   desc: "Web search & analysis"        },
  { value: "coder",        label: "Coder",         desc: "Code generation & tools"      },
  { value: "analyst",      label: "Analyst",       desc: "Data analysis"                },
];

export default function AgentsPage() {
  const { data: agents, mutate } = useFetch<Agent[]>("/agents");
  const [showSpawn, setShowSpawn]       = useState(false);
  const [spawning, setSpawning]         = useState(false);
  const [selectedType, setSelectedType] = useState("researcher");
  const [model, setModel]               = useState("");

  const handleSpawn = async () => {
    setSpawning(true);
    try {
      await spawnAgent({ type: selectedType, model: model || undefined });
      await mutate();
      setShowSpawn(false);
    } finally { setSpawning(false); }
  };

  return (
    <>
      <Header
        title="Agents"
        subtitle={`${agents?.length ?? 0} registered`}
        actions={
          <Button icon={<Plus size={13} />} onClick={() => setShowSpawn(true)}>
            Spawn Agent
          </Button>
        }
      />

      <div className="p-5">
        {!agents?.length ? (
          <EmptyState
            icon={<Bot size={18} />}
            title="No agents"
            description="Spawn an agent to begin. Agents are autonomous workers that use tools, communicate, and can self-evolve."
            action={<Button icon={<Plus size={13} />} onClick={() => setShowSpawn(true)}>Spawn Agent</Button>}
          />
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {agents.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                onTerminate={async () => { await terminateAgent(agent.id); await mutate(); }}
              />
            ))}
          </div>
        )}
      </div>

      <Modal open={showSpawn} onClose={() => setShowSpawn(false)} title="Spawn Agent">
        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-[12px] font-medium" style={{ color: "var(--text-2)" }}>
              Agent Type
            </label>
            <div className="grid grid-cols-2 gap-2">
              {AGENT_TYPES.map((t) => {
                const active = selectedType === t.value;
                return (
                  <button
                    key={t.value}
                    onClick={() => setSelectedType(t.value)}
                    className="rounded-md p-3 text-left transition-colors"
                    style={{
                      border:     `1px solid ${active ? "var(--text)" : "var(--border)"}`,
                      background: active ? "var(--surface-2)" : "var(--bg)",
                    }}
                  >
                    <p className="text-[12px] font-medium" style={{ color: "var(--text)" }}>{t.label}</p>
                    <p className="mt-0.5 text-[11px]" style={{ color: "var(--text-3)" }}>{t.desc}</p>
                  </button>
                );
              })}
            </div>
          </div>

          <Input
            label="Model override (optional)"
            placeholder="gpt-4o-mini, claude-haiku-4-5-20251001…"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          />

          <div className="flex justify-end gap-2 pt-1">
            <Button variant="secondary" onClick={() => setShowSpawn(false)}>Cancel</Button>
            <Button onClick={handleSpawn} disabled={spawning} icon={<Sparkles size={13} />}>
              {spawning ? "Spawning…" : "Spawn"}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}

function AgentCard({ agent, onTerminate }: { agent: Agent; onTerminate: () => void }) {
  const canTerminate = agent.status === "running" || agent.status === "idle";

  return (
    <GlassCard className="group" hover>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md"
            style={{ background: "var(--surface-2)", color: "var(--text-2)" }}
          >
            <Bot size={15} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-[13px] font-semibold capitalize" style={{ color: "var(--text)" }}>
                {agent.type}
              </h3>
              <StatusBadge status={agent.status} pulse={agent.status === "running"} />
            </div>
            <p className="mt-0.5 font-mono text-[10px]" style={{ color: "var(--text-3)" }}>
              {agent.id}
            </p>
          </div>
        </div>

        {canTerminate && (
          <button
            onClick={onTerminate}
            className="flex h-6 w-6 items-center justify-center rounded opacity-0 transition-all group-hover:opacity-100 hover:bg-red-50"
            style={{ color: "var(--text-3)" }}
          >
            <Trash2 size={12} />
          </button>
        )}
      </div>

      {/* Stats grid */}
      <div
        className="mt-4 grid grid-cols-3 divide-x overflow-hidden rounded-md"
        style={{ border: "1px solid var(--border)" }}
      >
        {[
          { label: "Model",  value: agent.model || "default" },
          { label: "Tokens", value: `${formatNumber(agent.tokens_used)} / ${formatNumber(agent.token_budget)}` },
          { label: "Tools",  value: String(agent.tools?.length ?? 0) },
        ].map((s) => (
          <div key={s.label} className="px-3 py-2" style={{ background: "var(--surface)" }}>
            <p className="text-[10px]" style={{ color: "var(--text-3)" }}>{s.label}</p>
            <p className="mt-0.5 truncate text-[12px] font-medium" style={{ color: "var(--text-2)" }}>
              {s.value}
            </p>
          </div>
        ))}
      </div>

      {agent.capabilities?.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {agent.capabilities.map((cap) => (
            <span
              key={cap}
              className="rounded px-1.5 py-0.5 text-[10px]"
              style={{ background: "var(--surface-2)", color: "var(--text-3)", border: "1px solid var(--border)" }}
            >
              {cap}
            </span>
          ))}
        </div>
      )}

      {agent.current_task && (
        <div
          className="mt-3 rounded-md px-3 py-2"
          style={{ background: "#fffbeb", border: "1px solid #fde68a" }}
        >
          <p className="text-[10px] font-medium" style={{ color: "#92400e" }}>Working on</p>
          <p className="mt-0.5 truncate text-[12px]" style={{ color: "#78350f" }}>
            {agent.current_task}
          </p>
        </div>
      )}
    </GlassCard>
  );
}
