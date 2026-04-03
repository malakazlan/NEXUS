"use client";

import type { ReactNode } from "react";

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div
        className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg"
        style={{ background: "var(--surface-2)", color: "var(--text-3)" }}
      >
        {icon}
      </div>
      <p className="text-[13px] font-medium" style={{ color: "var(--text)" }}>{title}</p>
      <p className="mt-1 max-w-xs text-[12px]" style={{ color: "var(--text-3)" }}>{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
