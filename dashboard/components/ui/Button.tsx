"use client";

import { cn } from "@/lib/utils";
import { type ButtonHTMLAttributes, type ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md";
  icon?: ReactNode;
}

const variants: Record<string, React.CSSProperties> = {
  primary:   { background: "var(--accent)",   color: "var(--accent-fg)", border: "1px solid var(--accent)" },
  secondary: { background: "var(--bg)",       color: "var(--text-2)",    border: "1px solid var(--border)" },
  danger:    { background: "transparent",     color: "var(--danger)",    border: "1px solid #fecaca"       },
  ghost:     { background: "transparent",     color: "var(--text-2)",    border: "1px solid transparent"   },
};

const sizes: Record<string, string> = {
  sm: "h-7 px-2.5 text-[12px] gap-1.5 rounded",
  md: "h-8 px-3   text-[13px] gap-2   rounded-md",
};

export function Button({
  variant = "primary",
  size = "md",
  icon,
  children,
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center font-medium transition-opacity duration-100",
        sizes[size],
        "disabled:opacity-40 disabled:cursor-not-allowed",
        "hover:opacity-80",
        className
      )}
      style={variants[variant]}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
