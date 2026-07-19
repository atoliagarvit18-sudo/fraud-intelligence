import { cn } from "@/lib/utils";
import type { HTMLAttributes, ReactNode } from "react";

interface Props extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  interactive?: boolean;
  glow?: string; // css color
}

export function GlassCard({ children, className, interactive, glow, style, ...rest }: Props) {
  return (
    <div
      className={cn(
        "glass relative overflow-hidden p-5",
        interactive && "glass-hover cursor-pointer",
        className,
      )}
      style={{
        ...(glow
          ? {
              boxShadow: `0 0 0 1px color-mix(in oklab, ${glow} 35%, transparent), 0 20px 60px -20px color-mix(in oklab, ${glow} 40%, transparent)`,
            }
          : {}),
        ...style,
      }}
      {...rest}
    >
      {glow ? (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 h-px"
          style={{ background: `linear-gradient(90deg, transparent, ${glow}, transparent)` }}
        />
      ) : null}
      {children}
    </div>
  );
}
