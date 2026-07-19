import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/soc/AppShell";
import { GlassCard } from "@/components/soc/GlassCard";
import { useAnalysis } from "@/store/analysis";
import { CheckCircle2, ExternalLink } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/recommendations")({
  head: () => ({ meta: [{ title: "Recommendations — Fraud Intelligence Platform" }] }),
  component: Recs,
});

function Recs() {
  const { activeCase } = useAnalysis();
  return (
    <AppShell>
      <div className="mx-auto max-w-4xl">
        <div className="mb-6">
          <div className="text-[10px] uppercase tracking-[0.25em] text-muted-foreground">Response playbook</div>
          <h1 className="mt-1 text-2xl font-semibold" style={{ fontFamily: "var(--font-display)" }}>Recommended actions</h1>
          <p className="mt-2 text-sm text-muted-foreground">Case <span className="text-mono">{activeCase.caseId}</span> · {activeCase.verdict}</p>
        </div>
        <div className="grid gap-3">
          {activeCase.recommendations.map((r, i) => {
            const rc = r.urgency === "critical" ? "var(--risk-critical)" : r.urgency === "warning" ? "var(--risk-medium)" : "var(--risk-safe)";
            return (
              <GlassCard key={i} glow={rc}>
                <div className="flex items-center gap-3">
                  <span className="grid h-10 w-10 place-items-center rounded-xl" style={{ background: `color-mix(in oklab, ${rc} 15%, transparent)`, color: rc }}>
                    <CheckCircle2 size={18} />
                  </span>
                  <div className="flex-1">
                    <div className="text-sm font-medium">{r.action}</div>
                    <div className="text-[10px] uppercase tracking-widest" style={{ color: rc }}>{r.urgency}</div>
                  </div>
                  {r.action.toLowerCase().includes("cyber crime") && (
                    <button
                      onClick={() => toast.success("Report submitted (demo)", { description: `Case ${activeCase.caseId} forwarded to Cyber Crime Portal` })}
                      className="inline-flex items-center gap-1 rounded-md border border-white/15 bg-white/5 px-3 py-1.5 text-xs hover:bg-white/10"
                    >Report <ExternalLink size={12} /></button>
                  )}
                </div>
              </GlassCard>
            );
          })}
        </div>
      </div>
    </AppShell>
  );
}
