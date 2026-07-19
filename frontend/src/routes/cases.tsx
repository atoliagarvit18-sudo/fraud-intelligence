import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AppShell } from "@/components/soc/AppShell";
import { GlassCard } from "@/components/soc/GlassCard";
import { RiskBadge } from "@/components/soc/Badge";
import { useAnalysis } from "@/store/analysis";
import { tierColor } from "@/mocks/cases";
import { Search, Radar } from "lucide-react";

export const Route = createFileRoute("/cases")({
  head: () => ({ meta: [{ title: "Case History — Fraud Intelligence Platform" }] }),
  component: Cases,
});

function Cases() {
  const { history, selectSample } = useAnalysis();
  const nav = useNavigate();
  const empty = history.length === 0;

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-[0.25em] text-muted-foreground">Archive</div>
            <h1 className="mt-1 text-2xl font-semibold" style={{ fontFamily: "var(--font-display)" }}>Case history</h1>
          </div>
          <div className="relative w-full max-w-xs">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input placeholder="Search cases…" className="text-mono w-full rounded-lg border border-white/10 bg-white/5 py-2 pl-9 pr-3 text-xs" />
          </div>
        </div>

        {empty ? (
          <GlassCard className="grid place-items-center py-20 text-center">
            <div className="grid h-16 w-16 place-items-center rounded-2xl border border-white/10 bg-white/5">
              <Radar size={24} className="text-muted-foreground" />
            </div>
            <div className="mt-4 text-sm font-semibold">No cases yet</div>
            <p className="mt-1 max-w-sm text-xs text-muted-foreground">Run your first analysis to populate this archive with verdicts and evidence.</p>
            <button onClick={() => nav({ to: "/analysis" })} className="mt-4 rounded-lg border border-white/15 bg-white/5 px-4 py-2 text-xs hover:bg-white/10">Start analysis</button>
          </GlassCard>
        ) : (
          <div className="grid gap-3">
            {history.map((c) => {
              const color = tierColor(c.tier);
              return (
                <GlassCard
                  key={c.caseId}
                  interactive
                  glow={color}
                  onClick={() => { selectSample(c.caseId); nav({ to: "/dashboard" }); }}
                >
                  <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 sm:grid-cols-[auto_minmax(0,1fr)_auto_auto]">
                    <div className="hidden sm:block">
                      <div className="text-mono text-xs text-muted-foreground">{c.caseId}</div>
                    </div>
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold">{c.verdict}</div>
                      <div className="text-mono text-[11px] text-muted-foreground">{new Date(c.timestamp).toUTCString().slice(5, 22)}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-mono text-xl font-semibold" style={{ color }}>{c.overallRisk}</div>
                      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">score</div>
                    </div>
                    <RiskBadge tier={c.tier} />
                  </div>
                </GlassCard>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
