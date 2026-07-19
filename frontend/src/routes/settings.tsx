import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/soc/AppShell";
import { GlassCard } from "@/components/soc/GlassCard";

export const Route = createFileRoute("/settings")({
  head: () => ({ meta: [{ title: "Settings — Fraud Intelligence Platform" }] }),
  component: Settings,
});

function Settings() {
  return (
    <AppShell>
      <div className="mx-auto max-w-4xl space-y-6">
        <div>
          <div className="text-[10px] uppercase tracking-[0.25em] text-muted-foreground">Preferences</div>
          <h1 className="mt-1 text-2xl font-semibold" style={{ fontFamily: "var(--font-display)" }}>Settings</h1>
        </div>
        <GlassCard>
          <div className="text-sm font-semibold">Analyst profile</div>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <Field label="Name" value="HackTeam" />
            <Field label="Role" value="ET AI Hackathon 2.0" />
            <Field label="Team" value="Fraud Intelligence" />
            <Field label="Clearance" value="Tier 3" />
          </div>
        </GlassCard>
        <GlassCard>
          <div className="text-sm font-semibold">Alerts</div>
          <div className="mt-3 space-y-2 text-sm text-muted-foreground">
            {["High-risk verdicts", "Cluster expansion", "Model updates", "Weekly digest"].map((l) => (
              <label key={l} className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                <span>{l}</span>
                <input type="checkbox" defaultChecked className="accent-[color:var(--neon-cyan)]" />
              </label>
            ))}
          </div>
        </GlassCard>
      </div>
    </AppShell>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-3">
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm">{value}</div>
    </div>
  );
}
