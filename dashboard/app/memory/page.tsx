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
import { fetchMemory, writeMemory } from "@/lib/api";
import { Database, Plus, Search, Key } from "lucide-react";

export default function MemoryPage() {
  const { data: keys, mutate } = useFetch<string[]>("/memory");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [selectedValue, setSelectedValue] = useState<unknown>(null);
  const [loading, setLoading]     = useState(false);
  const [showWrite, setShowWrite] = useState(false);
  const [writing, setWriting]     = useState(false);
  const [writeKey, setWriteKey]   = useState("");
  const [writeValue, setWriteValue] = useState("");
  const [search, setSearch]       = useState("");

  const filteredKeys = (keys ?? []).filter((k) =>
    k.toLowerCase().includes(search.toLowerCase())
  );

  const handleSelect = async (key: string) => {
    setSelectedKey(key);
    setLoading(true);
    try {
      const r = await fetchMemory(key);
      setSelectedValue(r.value);
    } catch { setSelectedValue("Error loading value"); }
    finally { setLoading(false); }
  };

  const handleWrite = async () => {
    if (!writeKey.trim()) return;
    setWriting(true);
    try {
      let val: unknown;
      try { val = JSON.parse(writeValue); } catch { val = writeValue; }
      await writeMemory(writeKey, val);
      await mutate();
      setShowWrite(false);
      setWriteKey(""); setWriteValue("");
    } finally { setWriting(false); }
  };

  return (
    <>
      <Header
        title="Shared Memory"
        subtitle={`${keys?.length ?? 0} keys`}
        actions={<Button icon={<Plus size={13} />} onClick={() => setShowWrite(true)}>Write Entry</Button>}
      />

      <div className="p-5" style={{ height: "calc(100vh - 48px)" }}>
        <div className="grid grid-cols-3 gap-3 h-full">
          {/* Keys */}
          <GlassCard padding="none" className="flex flex-col overflow-hidden">
            <div
              className="flex items-center gap-2 px-3 py-2.5"
              style={{ borderBottom: "1px solid var(--border)" }}
            >
              <Search size={12} style={{ color: "var(--text-3)" }} className="shrink-0" />
              <input
                className="flex-1 bg-transparent text-[12px] placeholder:text-zinc-400 focus:outline-none"
                style={{ color: "var(--text)" }}
                placeholder="Filter keys…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            <div className="flex-1 overflow-y-auto p-1">
              {filteredKeys.length === 0 ? (
                <EmptyState icon={<Database size={16} />} title="No keys"
                  description="Agents write data here during task execution." />
              ) : (
                filteredKeys.map((key) => {
                  const active = selectedKey === key;
                  return (
                    <button
                      key={key}
                      onClick={() => handleSelect(key)}
                      className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left transition-colors"
                      style={{
                        background: active ? "var(--surface-2)" : "transparent",
                        marginBottom: "1px",
                      }}
                      onMouseEnter={(e) => {
                        if (!active) (e.currentTarget as HTMLElement).style.background = "var(--surface-2)";
                      }}
                      onMouseLeave={(e) => {
                        if (!active) (e.currentTarget as HTMLElement).style.background = "transparent";
                      }}
                    >
                      <Key size={11} style={{ color: active ? "var(--text)" : "var(--text-3)" }} className="shrink-0" />
                      <span
                        className="flex-1 truncate font-mono text-[12px]"
                        style={{ color: active ? "var(--text)" : "var(--text-2)" }}
                      >
                        {key}
                      </span>
                    </button>
                  );
                })
              )}
            </div>

            <div className="px-3 py-2" style={{ borderTop: "1px solid var(--border)" }}>
              <p className="text-[11px]" style={{ color: "var(--text-3)" }}>
                {filteredKeys.length} key{filteredKeys.length !== 1 ? "s" : ""}
              </p>
            </div>
          </GlassCard>

          {/* Value */}
          <GlassCard padding="none" className="col-span-2 flex flex-col overflow-hidden">
            {selectedKey ? (
              <>
                <div className="px-5 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
                  <p className="text-[11px]" style={{ color: "var(--text-3)" }}>Key</p>
                  <p className="mt-0.5 font-mono text-[14px] font-semibold" style={{ color: "var(--text)" }}>
                    {selectedKey}
                  </p>
                </div>
                <div className="flex-1 overflow-auto p-4">
                  {loading ? (
                    <div className="shimmer h-32 rounded-md" />
                  ) : (
                    <CodeBlock
                      code={typeof selectedValue === "string" ? selectedValue : JSON.stringify(selectedValue, null, 2)}
                      language="json"
                      maxHeight="calc(100vh - 300px)"
                    />
                  )}
                </div>
              </>
            ) : (
              <div className="flex flex-1 items-center justify-center">
                <EmptyState icon={<Key size={16} />} title="Select a key"
                  description="Choose a key from the panel to inspect its value." />
              </div>
            )}
          </GlassCard>
        </div>
      </div>

      <Modal open={showWrite} onClose={() => setShowWrite(false)} title="Write to Shared Memory">
        <div className="space-y-4">
          <Input label="Key" placeholder="e.g. research_findings"
            value={writeKey} onChange={(e) => setWriteKey(e.target.value)} />
          <TextArea label="Value (JSON or plain text)" placeholder='{"findings": [...]}'
            rows={6} value={writeValue} onChange={(e) => setWriteValue(e.target.value)} />
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="secondary" onClick={() => setShowWrite(false)}>Cancel</Button>
            <Button onClick={handleWrite} disabled={writing || !writeKey.trim()}>
              {writing ? "Writing…" : "Write"}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
