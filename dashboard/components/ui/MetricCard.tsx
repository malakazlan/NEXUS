"use client";

import { GlassCard } from "./GlassCard";
import type { ReactNode } from "react";

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: ReactNode;
  sub?: string;
}

export function MetricCard({ label, value, icon, sub }: MetricCardProps) {
  return (
    <GlassCard className="flex items-start gap-3" hover>
      <div
        className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md"
        style={{ background: "var(--surface-2)", color: "var(--text-2)" }}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-[12px]" style={{ color: "var(--text-3)" }}>{label}</p>
        <p className="mt-0.5 text-[22px] font-semibold tracking-tight" style={{ color: "var(--text)" }}>
          {value}
        </p>
        {sub && <p className="text-[11px]" style={{ color: "var(--text-3)" }}>{sub}</p>}
      </div>
    </GlassCard>
  );
}
