"use client";

import { Header } from "@/components/layout/Header";
import { MetricCard } from "@/components/ui/MetricCard";
import { GlassCard } from "@/components/ui/GlassCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useFetch } from "@/lib/useFetch";
import { useWebSocket } from "@/lib/useWebSocket";
import { timeAgo } from "@/lib/utils";
import {
  EVENT_CATEGORIES,
  type Agent,
  type Task,
  type Tool,
  type HealthStatus,
  type NexusEvent,
} from "@/lib/types";
import { Bot, Wrench, ListTodo, Zap, ArrowRight } from "lucide-react";
import Link from "next/link";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import { useMemo } from "react";

export default function OverviewPage() {
  const { data: health } = useFetch<HealthStatus>("/health");
  const { data: agents } = useFetch<Agent[]>("/agents");
  const { data: tasks }  = useFetch<Task[]>("/tasks");
  const { data: tools }  = useFetch<Tool[]>("/tools");
  const { events, connected } = useWebSocket();

  const activeAgents   = agents?.filter((a) => a.status === "running").length ?? 0;
  const completedTasks = tasks?.filter((t)  => t.status === "completed").length ?? 0;
  const dynamicTools   = tools?.filter((t)  => !t.is_builtin).length ?? 0;

  const chartData = useMemo(() => {
    if (!events.length) return [];
    const grouped = new Map<string, number>();
    for (const e of events.slice(0, 60)) {
      const d = new Date(e.timestamp);
      const key = `${d.getHours().toString().padStart(2,"0")}:${d.getMinutes().toString().padStart(2,"0")}`;
      grouped.set(key, (grouped.get(key) ?? 0) + 1);
    }
    return Array.from(grouped.entries()).map(([time, count]) => ({ time, count })).reverse();
  }, [events]);

  return (
    <>
      <Header
        title="Overview"
        subtitle={health ? `${health.agents} agents · ${health.tools} tools` : undefined}
      />

      <div className="p-5 space-y-4">
        {/* Metrics */}
        <div className="grid grid-cols-4 gap-3">
          <MetricCard label="Active Agents"    value={activeAgents}      icon={<Bot size={15} />} />
          <MetricCard label="Tasks Completed"  value={completedTasks}    icon={<ListTodo size={15} />} />
          <MetricCard
            label="MCP Tools"
            value={tools?.length ?? 0}
            icon={<Wrench size={15} />}
            sub={dynamicTools > 0 ? `${dynamicTools} self-created` : undefined}
          />
          <MetricCard label="Events Captured"  value={events.length}     icon={<Zap size={15} />} />
        </div>

        <div className="grid grid-cols-3 gap-3">
          {/* Chart */}
          <GlassCard className="col-span-2">
            <div className="mb-4 flex items-center justify-between">
              <p className="section-label">Event Activity</p>
              <div className="flex items-center gap-1.5">
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ background: connected ? "var(--success)" : "var(--text-3)" }}
                />
                <span className="text-[11px]" style={{ color: "var(--text-3)" }}>
                  {connected ? "real-time" : "disconnected"}
                </span>
              </div>
            </div>

            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={170}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%"   stopColor="#09090b" stopOpacity={0.08} />
                      <stop offset="100%" stopColor="#09090b" stopOpacity={0}    />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time"
                    tick={{ fill: "#a1a1aa", fontSize: 10, fontFamily: "Inter" }}
                    axisLine={false} tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: "#a1a1aa", fontSize: 10, fontFamily: "Inter" }}
                    axisLine={false} tickLine={false} width={18}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#fff",
                      border: "1px solid #e4e4e7",
                      borderRadius: "6px",
                      fontSize: "12px",
                      color: "#09090b",
                      fontFamily: "Inter",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
                    }}
                    cursor={{ stroke: "#e4e4e7" }}
                  />
                  <Area
                    type="monotone" dataKey="count"
                    stroke="#09090b" strokeWidth={1.5}
                    fill="url(#grad)" dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div
                className="flex h-[170px] items-center justify-center rounded-md text-[12px]"
                style={{ border: "1px dashed var(--border)", color: "var(--text-3)" }}
              >
                Waiting for events…
              </div>
            )}
          </GlassCard>

          {/* Feed */}
          <GlassCard padding="none" className="overflow-hidden flex flex-col">
            <div
              className="flex items-center justify-between px-4 py-3"
              style={{ borderBottom: "1px solid var(--border)" }}
            >
              <p className="section-label">Live Feed</p>
              <Link
                href="/events"
                className="flex items-center gap-1 text-[11px] transition-colors hover:opacity-60"
                style={{ color: "var(--text-3)" }}
              >
                All <ArrowRight size={10} />
              </Link>
            </div>
            <div className="flex-1 overflow-y-auto py-1">
              {events.length === 0 ? (
                <p className="py-8 text-center text-[12px]" style={{ color: "var(--text-3)" }}>
                  No events yet
                </p>
              ) : (
                events.slice(0, 20).map((e) => <FeedRow key={e.id} event={e} />)
              )}
            </div>
          </GlassCard>
        </div>

        {/* Bottom */}
        <div className="grid grid-cols-2 gap-3">
          <SectionCard title="Agents" href="/agents" empty={!agents?.length} emptyMsg="No agents running">
            {agents?.slice(0, 6).map((agent) => (
              <div key={agent.id} className="row-item">
                <Bot size={13} className="shrink-0" style={{ color: "var(--text-3)" }} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[13px] font-medium capitalize" style={{ color: "var(--text)" }}>
                    {agent.type}
                  </p>
                  <p className="truncate font-mono text-[10px]" style={{ color: "var(--text-3)" }}>
                    {agent.id}
                  </p>
                </div>
                <StatusBadge status={agent.status} />
              </div>
            ))}
          </SectionCard>

          <SectionCard title="Recent Tasks" href="/tasks" empty={!tasks?.length} emptyMsg="No tasks submitted">
            {tasks?.slice(0, 6).map((task) => (
              <div key={task.id} className="row-item">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[13px]" style={{ color: "var(--text)" }}>
                    {task.description}
                  </p>
                  <p className="text-[11px]" style={{ color: "var(--text-3)" }}>
                    P{task.priority} · {timeAgo(task.created_at)}
                  </p>
                </div>
                <StatusBadge status={task.status} />
              </div>
            ))}
          </SectionCard>
        </div>
      </div>
    </>
  );
}

function FeedRow({ event }: { event: NexusEvent }) {
  const color = EVENT_CATEGORIES[event.type]?.color ?? "#a1a1aa";
  return (
    <div
      className="flex items-center gap-2.5 px-4 py-1.5 transition-colors"
      style={{ cursor: "default" }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--surface-2)"; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
    >
      <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: color }} />
      <span className="flex-1 truncate text-[12px]" style={{ color: "var(--text-2)" }}>
        {event.type}
      </span>
      <span className="shrink-0 text-[10px]" style={{ color: "var(--text-3)" }}>
        {timeAgo(event.timestamp)}
      </span>
    </div>
  );
}

function SectionCard({
  title, href, children, empty, emptyMsg,
}: {
  title: string; href: string; children: React.ReactNode; empty: boolean; emptyMsg: string;
}) {
  return (
    <GlassCard padding="none" className="overflow-hidden flex flex-col">
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <p className="section-label">{title}</p>
        <Link
          href={href}
          className="flex items-center gap-1 text-[11px] transition-opacity hover:opacity-60"
          style={{ color: "var(--text-3)" }}
        >
          Manage <ArrowRight size={10} />
        </Link>
      </div>
      <div className="flex-1 p-1">
        {empty ? (
          <p className="py-8 text-center text-[12px]" style={{ color: "var(--text-3)" }}>
            {emptyMsg}
          </p>
        ) : children}
      </div>
    </GlassCard>
  );
}
