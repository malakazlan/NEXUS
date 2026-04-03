"use client";

const STATUS_CONFIG: Record<string, { dot: string; color: string; bg: string; border: string }> = {
  running:    { dot: "#16a34a", color: "#15803d", bg: "#f0fdf4", border: "#bbf7d0" },
  idle:       { dot: "#a1a1aa", color: "#71717a", bg: "#fafafa", border: "#e4e4e7" },
  completed:  { dot: "#16a34a", color: "#15803d", bg: "#f0fdf4", border: "#bbf7d0" },
  failed:     { dot: "#dc2626", color: "#b91c1c", bg: "#fef2f2", border: "#fecaca" },
  terminated: { dot: "#d4d4d8", color: "#a1a1aa", bg: "#fafafa", border: "#e4e4e7" },
  pending:    { dot: "#a1a1aa", color: "#71717a", bg: "#fafafa", border: "#e4e4e7" },
  assigned:   { dot: "#d97706", color: "#b45309", bg: "#fffbeb", border: "#fde68a" },
};

interface StatusBadgeProps {
  status: string;
  pulse?: boolean;
}

export function StatusBadge({ status, pulse = false }: StatusBadgeProps) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.idle;
  const shouldPulse = pulse || status === "running";

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-medium capitalize"
      style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}` }}
    >
      <span className="relative flex h-1.5 w-1.5 shrink-0">
        <span className="absolute inset-0 rounded-full" style={{ background: cfg.dot }} />
        {shouldPulse && (
          <span className="dot-ping absolute inset-0 rounded-full" style={{ background: cfg.dot }} />
        )}
      </span>
      {status}
    </span>
  );
}
