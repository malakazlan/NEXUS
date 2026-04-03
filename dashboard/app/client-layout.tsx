"use client";

import { Sidebar } from "@/components/layout/Sidebar";
import type { ReactNode } from "react";

export function ClientLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ marginLeft: "228px", minHeight: "100vh" }}>
        {children}
      </main>
    </div>
  );
}
