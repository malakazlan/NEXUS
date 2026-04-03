"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { GlassCard } from "@/components/ui/GlassCard";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input, TextArea } from "@/components/ui/Input";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { EmptyState } from "@/components/ui/EmptyState";
import { useFetch } from "@/lib/useFetch";
import { createTool } from "@/lib/api";
import { timeAgo } from "@/lib/utils";
import type { Tool } from "@/lib/types";
import { Wrench, Plus, Cpu, ChevronDown, ChevronUp, Hash, Clock, User, Zap } from "lucide-react";

const DEFAULT_SCHEMA = `{\n  "type": "object",\n  "properties": {},\n  "required": []\n}`;

export default function ToolsPage() {
  const { data: tools, mutate } = useFetch<Tool[]>("/tools");
  const [showCreate, setShowCreate] = useState(false);
  const [expanded, setExpanded]     = useState<string | null>(null);
  const [creating, setCreating]     = useState(false);
  const [createError, setCreateError] = useState("");
  const [form, setForm] = useState({
    name: "", description: "", input_schema: DEFAULT_SCHEMA, tool_code: "", test_code: "",
  });

  const builtinTools = tools?.filter((t) => t.is_builtin)  ?? [];
  const dynamicTools = tools?.filter((t) => !t.is_builtin) ?? [];

  const handleCreate = async () => {
    setCreating(true);
    setCreateError("");
    try {
      let schema: Record<string, unknown>;
      try { schema = JSON.parse(form.input_schema); }
      catch { setCreateError("Invalid JSON in input schema"); setCreating(false); return; }
      await createTool({ name: form.name, description: form.description, input_schema: schema, tool_code: form.tool_code, test_code: form.test_code });
      await mutate();
      setShowCreate(false);
      setForm({ name: "", description: "", input_schema: DEFAULT_SCHEMA, tool_code: "", test_code: "" });
    } catch (e: unknown) {
      setCreateError(e instanceof Error ? e.message : "Creation failed");
    } finally { setCreating(false); }
  };

  return (
    <>
      <Header
        title="MCP Tools"
        subtitle={`${builtinTools.length} built-in · ${dynamicTools.length} self-created`}
        actions={<Button icon={<Plus size={13} />} onClick={() => setShowCreate(true)}>Create Tool</Button>}
      />

      <div className="p-5 space-y-6">
        {dynamicTools.length > 0 && (
          <section>
            <div className="mb-3 flex items-center gap-2">
              <Zap size={13} style={{ color: "var(--text-2)" }} />
              <h2 className="section-label">Self-Evolved</h2>
              <span
                className="rounded px-1.5 py-0.5 font-mono text-[10px]"
                style={{ background: "var(--surface-2)", color: "var(--text-3)", border: "1px solid var(--border)" }}
              >
                {dynamicTools.length}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {dynamicTools.map((t) => (
                <ToolCard key={t.name} tool={t} expanded={expanded === t.name}
                  onToggle={() => setExpanded(expanded === t.name ? null : t.name)} />
              ))}
            </div>
          </section>
        )}

        {builtinTools.length > 0 && (
          <section>
            <div className="mb-3 flex items-center gap-2">
              <Cpu size={13} style={{ color: "var(--text-3)" }} />
              <h2 className="section-label">Built-in</h2>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {builtinTools.map((t) => (
                <ToolCard key={t.name} tool={t} expanded={expanded === t.name}
                  onToggle={() => setExpanded(expanded === t.name ? null : t.name)} />
              ))}
            </div>
          </section>
        )}

        {!tools?.length && (
          <EmptyState icon={<Wrench size={18} />} title="No tools"
            description="Boot the NEXUS kernel to register built-in MCP tools." />
        )}
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Dynamic Tool" width="max-w-2xl">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Name" placeholder="csv_parser" value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <Input label="Description" placeholder="Parse CSV data into JSON array" value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <TextArea label="Input Schema (JSON)" rows={4} value={form.input_schema}
            onChange={(e) => setForm({ ...form, input_schema: e.target.value })} />
          <TextArea label="Tool Code (Python async)" rows={8}
            placeholder={`async def csv_parser(data: str) -> dict:\n    ...`}
            value={form.tool_code} onChange={(e) => setForm({ ...form, tool_code: e.target.value })} />
          <TextArea label="Test Code (pytest)" rows={5}
            placeholder={`from tool import csv_parser\nimport asyncio\n\ndef test_basic():\n    ...`}
            value={form.test_code} onChange={(e) => setForm({ ...form, test_code: e.target.value })} />

          {createError && (
            <p className="rounded-md px-3 py-2 text-[12px]"
              style={{ background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b" }}>
              {createError}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <Button variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={creating || !form.name || !form.tool_code || !form.test_code}>
              {creating ? "Running tests…" : "Create Tool"}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}

function ToolCard({ tool, expanded, onToggle }: { tool: Tool; expanded: boolean; onToggle: () => void }) {
  return (
    <div
      className="rounded-md overflow-hidden"
      style={{ border: "1px solid var(--border)", background: "var(--bg)" }}
    >
      <button
        onClick={onToggle}
        className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors"
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--surface)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
      >
        <div
          className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded"
          style={{ background: "var(--surface-2)", color: "var(--text-3)" }}
        >
          {tool.is_builtin ? <Cpu size={13} /> : <Zap size={13} />}
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="font-mono text-[13px] font-medium" style={{ color: "var(--text)" }}>
            {tool.name}
          </h3>
          <p className="mt-0.5 text-[12px] leading-snug" style={{ color: "var(--text-3)" }}>
            {tool.description}
          </p>
          <div className="mt-1.5 flex items-center gap-3 text-[10px]" style={{ color: "var(--text-3)" }}>
            <span className="flex items-center gap-1"><Hash size={9} />{tool.usage_count} calls</span>
            <span className="flex items-center gap-1"><Clock size={9} />{timeAgo(tool.created_at)}</span>
            {tool.created_by && <span className="flex items-center gap-1"><User size={9} />{tool.created_by}</span>}
          </div>
        </div>

        <span className="mt-0.5" style={{ color: "var(--text-3)" }}>
          {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </span>
      </button>

      {expanded && (
        <div className="px-4 pb-4" style={{ borderTop: "1px solid var(--border-subtle)" }}>
          <p className="section-label mt-3 mb-2">Input Schema</p>
          <CodeBlock code={JSON.stringify(tool.input_schema, null, 2)} language="json" maxHeight="200px" />
        </div>
      )}
    </div>
  );
}
