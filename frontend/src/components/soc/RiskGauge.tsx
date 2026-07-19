import { useEffect, useState } from "react";
import { tierColor, tierFromScore, tierLabel, type RiskTier } from "@/mocks/cases";

interface Props {
  score: number;
  size?: number;
  label?: string;
  tier?: RiskTier;
}

export function RiskGauge({ score, size = 240, label, tier }: Props) {
  const t = tier ?? tierFromScore(score);
  const color = tierColor(t);
  const [v, setV] = useState(0);

  useEffect(() => {
    const start = performance.now();
    const dur = 1200;
    let raf = 0;
    const step = (now: number) => {
      const k = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - k, 3);
      setV(score * eased);
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [score]);

  const r = size / 2 - 14;
  const c = 2 * Math.PI * r;
  const off = c - (v / 100) * c * 0.75;

  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-[135deg]">
        <defs>
          <linearGradient id="rg-grad" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.9" />
            <stop offset="100%" stopColor="var(--neon-blue)" stopOpacity="0.9" />
          </linearGradient>
          <filter id="rg-glow"><feGaussianBlur stdDeviation="4" /></filter>
        </defs>
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="12"
          strokeDasharray={`${c * 0.75} ${c}`} strokeLinecap="round"
        />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="url(#rg-grad)" strokeWidth="12"
          strokeDasharray={`${c * 0.75} ${c}`} strokeDashoffset={off - c * 0.25}
          strokeLinecap="round"
          filter="url(#rg-glow)"
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center">
          <div className="text-mono text-5xl font-semibold tracking-tight neon-text" style={{ color }}>
            {Math.round(v)}
          </div>
          <div className="mt-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">
            {label ?? "Risk Score"}
          </div>
          <div className="mt-3 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-widest"
            style={{ borderColor: color, color }}>
            <span className="h-1.5 w-1.5 rounded-full pulse-dot" style={{ background: color }} />
            {tierLabel(t)}
          </div>
        </div>
      </div>
    </div>
  );
}
