import type { ReactNode } from "react";
import { tierColor, tierLabel, type RiskTier } from "@/mocks/cases";
import { cn } from "@/lib/utils";

export function RiskBadge({ tier, className }: { tier: RiskTier; className?: string }) {
  const c = tierColor(tier);
  return (
    <span
      className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-widest", className)}
      style={{ borderColor: c, color: c, background: `color-mix(in oklab, ${c} 12%, transparent)` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: c, boxShadow: `0 0 10px ${c}` }} />
      {tierLabel(tier)}
    </span>
  );
}

export function Chip({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "danger" | "warn" | "ok" }) {
  const tones = {
    default: "border-white/15 bg-white/5 text-foreground/80",
    danger: "border-[color:var(--risk-critical)] text-[color:var(--risk-critical)] bg-[color:var(--risk-critical)]/10",
    warn: "border-[color:var(--risk-medium)] text-[color:var(--risk-medium)] bg-[color:var(--risk-medium)]/10",
    ok: "border-[color:var(--risk-safe)] text-[color:var(--risk-safe)] bg-[color:var(--risk-safe)]/10",
  } as const;
  return <span className={cn("inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px]", tones[tone])}>{children}</span>;
}
