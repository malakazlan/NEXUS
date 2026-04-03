"use client";

import { cn } from "@/lib/utils";
import { type ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  padding?: "none" | "sm" | "md" | "lg";
}

export function GlassCard({
  children,
  className,
  hover = false,
  padding = "md",
}: CardProps) {
  return (
    <div
      className={cn(
        "card",
        hover && "card-hover",
        padding === "sm"  && "p-4",
        padding === "md"  && "p-5",
        padding === "lg"  && "p-6",
        padding === "none" && "",
        className
      )}
    >
      {children}
    </div>
  );
}
