"use client";

import { cn } from "@/lib/utils";
import { type InputHTMLAttributes, forwardRef } from "react";

const fieldBase =
  "w-full rounded-md px-3 py-2 text-[13px] placeholder:text-zinc-400 " +
  "focus:outline-none focus:ring-2 focus:ring-black/10 " +
  "transition-colors duration-150";

const fieldStyle: React.CSSProperties = {
  background: "var(--bg)",
  border: "1px solid var(--border)",
  color: "var(--text)",
};

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, className, style, ...props }, ref) => (
    <div>
      {label && (
        <label className="mb-1.5 block text-[12px] font-medium" style={{ color: "var(--text-2)" }}>
          {label}
        </label>
      )}
      <input
        ref={ref}
        className={cn(fieldBase, className)}
        style={{ ...fieldStyle, ...style }}
        {...props}
      />
    </div>
  )
);
Input.displayName = "Input";

interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ label, className, style, ...props }, ref) => (
    <div>
      {label && (
        <label className="mb-1.5 block text-[12px] font-medium" style={{ color: "var(--text-2)" }}>
          {label}
        </label>
      )}
      <textarea
        ref={ref}
        className={cn(fieldBase, "resize-none font-mono", className)}
        style={{ ...fieldStyle, ...style }}
        {...props}
      />
    </div>
  )
);
TextArea.displayName = "TextArea";
