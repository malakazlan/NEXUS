"use client";

import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  width?: string;
}

export function Modal({ open, onClose, title, children, width = "max-w-lg" }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div
        className={`relative ${width} w-full mx-4 rounded-lg animate-in`}
        style={{
          background: "var(--bg)",
          border: "1px solid var(--border)",
          boxShadow: "0 8px 30px rgba(0,0,0,0.12)",
        }}
      >
        <div
          className="flex items-center justify-between px-5 py-3.5"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <h2 className="text-[13px] font-semibold" style={{ color: "var(--text)" }}>
            {title}
          </h2>
          <button
            onClick={onClose}
            className="flex h-6 w-6 items-center justify-center rounded transition-colors hover:bg-zinc-100"
            style={{ color: "var(--text-3)" }}
          >
            <X size={13} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
