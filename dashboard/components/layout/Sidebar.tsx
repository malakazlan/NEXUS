"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Bot,
  ListTodo,
  Wrench,
  Radio,
  Database,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/",       label: "Overview", icon: LayoutDashboard },
  { href: "/agents", label: "Agents",   icon: Bot             },
  { href: "/tasks",  label: "Tasks",    icon: ListTodo        },
  { href: "/tools",  label: "Tools",    icon: Wrench          },
  { href: "/events", label: "Events",   icon: Radio           },
  { href: "/memory", label: "Memory",   icon: Database        },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="fixed left-0 top-0 z-30 flex h-screen flex-col"
      style={{
        width: "var(--sidebar-w)",
        background: "var(--surface)",
        borderRight: "1px solid var(--border)",
      }}
    >
      {/* Logo */}
      <div
        className="flex h-12 items-center gap-2.5 px-4"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div
          className="flex h-5 w-5 items-center justify-center rounded"
          style={{ background: "var(--accent)" }}
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
            <path d="M5 0.5L9.5 3V7L5 9.5L0.5 7V3L5 0.5Z" fill="white" opacity="0.85"/>
            <path d="M5 3.5L8 5V7L5 8.5L2 7V5L5 3.5Z" fill="white"/>
          </svg>
        </div>
        <span
          className="text-[13px] font-semibold tracking-tight"
          style={{ color: "var(--text)" }}
        >
          NEXUS
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-2">
        <div className="space-y-px">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-2 rounded-md px-2.5 py-1.5 text-[13px] font-medium transition-colors duration-100",
                )}
                style={{
                  background: active ? "var(--surface-2)" : "transparent",
                  color: active ? "var(--text)" : "var(--text-2)",
                }}
                onMouseEnter={(e) => {
                  if (!active) (e.currentTarget as HTMLElement).style.background = "var(--surface-2)";
                }}
                onMouseLeave={(e) => {
                  if (!active) (e.currentTarget as HTMLElement).style.background = "transparent";
                }}
              >
                <Icon
                  size={14}
                  className="shrink-0"
                  style={{ color: active ? "var(--text)" : "var(--text-3)" }}
                />
                {label}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <div
        className="px-4 py-3"
        style={{ borderTop: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-1.5">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-green-500" />
          <span className="text-[11px]" style={{ color: "var(--text-3)" }}>
            Runtime active
          </span>
        </div>
      </div>
    </aside>
  );
}
