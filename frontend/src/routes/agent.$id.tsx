import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { AudioLines, FileText, ScanEye, Network, ArrowLeft } from "lucide-react";
import { AppShell } from "@/components/soc/AppShell";
import { GlassCard } from "@/components/soc/GlassCard";
import { RiskBadge, Chip } from "@/components/soc/Badge";
import { useAnalysis } from "@/store/analysis";
import { tierColor, tierFromScore, type AgentKey } from "@/mocks/cases";

export const Route = createFileRoute("/agent/$id")({
  head: ({ params }) => ({ meta: [{ title: `${params.id[0].toUpperCase() + params.id.slice(1)} Agent — Fraud Intelligence` }] }),
  component: AgentPage,
  notFoundComponent: () => (
    <AppShell><div className="p-8 text-center text-muted-foreground">Unknown agent.</div></AppShell>
  ),
});

const meta: Record<AgentKey, { title: string; agentName: string; icon: typeof AudioLines }> = {
  speech: { title: "Speech Intelligence Agent", agentName: "Agent 3 — Call & Audio Analysis Engine", icon: AudioLines },
  text: { title: "OSINT Campaign Intelligence Agent", agentName: "Agent 2 — Reddit, Telegram & Cybercrime Complaints Scraper", icon: FileText },
  visual: { title: "Visual Intelligence Agent", agentName: "Agent 1 — Currency CV & Document Forensics", icon: ScanEye },
  network: { title: "Network & Fusion Intelligence Agent", agentName: "Agent 4 — Multi-Agent Correlation Engine", icon: Network },
};

function AgentPage() {
  const { id } = Route.useParams();
  const { activeCase } = useAnalysis();
  if (!(id in meta)) throw notFound();
  const key = id as AgentKey;
  const info = meta[key];
  const data = activeCase.agents[key];
  const tier = tierFromScore(data.score);
  const color = tierColor(tier);

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl space-y-6">
        <Link to="/dashboard" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          <ArrowLeft size={12} /> Back to dashboard
        </Link>

        <GlassCard glow={color}>
          <div className="flex flex-wrap items-center gap-4">
            <div className="grid h-14 w-14 place-items-center rounded-2xl border" style={{ borderColor: color, color, background: `color-mix(in oklab, ${color} 12%, transparent)` }}>
              <info.icon size={24} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-xs uppercase tracking-widest text-muted-foreground">{info.agentName}</div>
              <h1 className="text-2xl font-semibold" style={{ fontFamily: "var(--font-display)" }}>{info.title}</h1>
            </div>
            <div className="flex flex-col items-end">
              <div className="flex items-center gap-3">
                <div>
                  <div className="text-mono text-3xl font-semibold" style={{ color }}>{data.score}</div>
                  <div className="text-[10px] uppercase tracking-widest text-muted-foreground text-right">Risk</div>
                </div>
                <div className="h-10 w-px bg-white/10" />
                <div>
                  <div className="text-mono text-3xl font-semibold">{data.confidence}%</div>
                  <div className="text-[10px] uppercase tracking-widest text-muted-foreground text-right">Confidence</div>
                </div>
              </div>
              <div className="mt-2"><RiskBadge tier={tier} /></div>
            </div>
          </div>
          <p className="mt-4 text-sm text-muted-foreground">{data.summary}</p>
        </GlassCard>

        {key === "speech" && <SpeechDetail />}
        {key === "text" && <TextDetail />}
        {key === "visual" && <VisualDetail />}
        {key === "network" && <NetworkDetail />}
      </div>
    </AppShell>
  );
}

function SpeechDetail() {
  const { activeCase } = useAnalysis();
  const d = activeCase.details.speech;
  return (
    <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
      <GlassCard>
        <div className="text-sm font-semibold">Transcript</div>
        <div className="mt-3 space-y-2">
          {d.transcript.length === 0 && <div className="text-xs text-muted-foreground">No audio submitted.</div>}
          {d.transcript.map((t, i) => (
            <div key={i} className={`text-mono rounded-lg border p-3 text-xs leading-relaxed ${t.speaker === "Caller" ? "border-[color:var(--risk-critical)]/30 bg-[color:var(--risk-critical)]/5" : "border-white/10 bg-white/5"}`}>
              <div className="mb-1 text-[10px] uppercase tracking-widest text-muted-foreground">{t.speaker}</div>
              {t.line}
            </div>
          ))}
        </div>
        <div className="mt-6 text-sm font-semibold">LLM Reasoning</div>
        <p className="mt-2 rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-muted-foreground">{d.reasoning}</p>
      </GlassCard>
      <div className="space-y-6">
        <GlassCard>
          <div className="text-sm font-semibold">Keyword detection</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {d.keywords.map((k) => (
              <Chip key={k.term} tone={k.severity === "critical" || k.severity === "high" ? "danger" : k.severity === "medium" ? "warn" : "ok"}>
                {k.term}
              </Chip>
            ))}
          </div>
        </GlassCard>
        <GlassCard>
          <div className="text-sm font-semibold">Semantic similarity</div>
          <div className="mt-3 flex items-center gap-3">
            <div className="text-mono text-2xl">{Math.round(d.similarity * 100)}%</div>
            <div className="h-1.5 flex-1 rounded-full bg-white/5">
              <div className="h-full rounded-full" style={{ width: `${d.similarity * 100}%`, background: "linear-gradient(90deg, var(--neon-cyan), var(--risk-critical))" }} />
            </div>
          </div>
          <div className="mt-2 text-[11px] text-muted-foreground">Match to known scam scripts</div>
        </GlassCard>
        <GlassCard>
          <div className="text-sm font-semibold">Voice analysis</div>
          <div className="mt-3 flex h-16 items-end gap-0.5">
            {Array.from({ length: 64 }).map((_, i) => (
              <span key={i} className="flex-1 rounded-full" style={{ height: `${20 + Math.abs(Math.sin(i * 0.5)) * 90}%`, background: "var(--neon-cyan)", opacity: 0.6 }} />
            ))}
          </div>
          <div className="mt-3 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Synthetic voice probability</span>
            <span className="text-mono" style={{ color: "var(--risk-high)" }}>{Math.round(d.syntheticVoiceProb * 100)}%</span>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}

function TextDetail() {
  const { activeCase } = useAnalysis();
  const d = activeCase.details.text;
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <GlassCard>
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Scraped OSINT Entities</div>
          <span className="inline-flex items-center gap-1 rounded-full border border-[color:var(--neon-cyan)]/30 bg-[color:var(--neon-cyan)]/10 px-2.5 py-0.5 text-[10px] text-[color:var(--neon-cyan)]">
            ● Live MongoDB Feed
          </span>
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {d.entities.map((e) => (
            <div key={e.label} className="rounded-lg border border-white/10 bg-white/5 p-3">
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{e.label}</div>
              <div className="text-mono mt-1 text-sm">{e.value}</div>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-3 border-t border-white/10 flex flex-wrap items-center justify-between text-xs text-muted-foreground">
          <span>Active Collectors:</span>
          <div className="flex gap-1.5">
            <span className="rounded-md bg-white/10 px-2 py-0.5 text-[10px]">Reddit r/India</span>
            <span className="rounded-md bg-white/10 px-2 py-0.5 text-[10px]">Telegram Channels</span>
            <span className="rounded-md bg-white/10 px-2 py-0.5 text-[10px]">Cybercrime Portal</span>
          </div>
        </div>
      </GlassCard>
      <GlassCard>
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Campaign Threat Cluster</div>
          <RiskBadge tier={d.threatLevel} />
        </div>
        <div className="mt-4 text-[10px] uppercase tracking-widest text-muted-foreground">Matched Campaign Type</div>
        <div className="mt-1 text-lg font-semibold" style={{ fontFamily: "var(--font-display)" }}>{d.category}</div>
        <div className="mt-4 text-[10px] uppercase tracking-widest text-muted-foreground">Scraped Threat Keywords</div>
        <div className="mt-2 flex flex-wrap gap-2">
          {d.keywords.map((k) => <Chip key={k} tone="danger">{k}</Chip>)}
        </div>
      </GlassCard>
      <GlassCard className="lg:col-span-2">
        <div className="text-sm font-semibold">OSINT Scraper & MongoDB Correlation Reasoning</div>
        <p className="mt-2 text-sm text-muted-foreground">{d.reasoning}</p>
      </GlassCard>
    </div>
  );
}

function VisualDetail() {
  const { activeCase } = useAnalysis();
  const d = activeCase.details.visual;
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <GlassCard>
        <div className="text-sm font-semibold">OCR result</div>
        <pre className="text-mono mt-3 whitespace-pre-wrap rounded-lg border border-white/10 bg-black/40 p-3 text-xs">{d.ocr || "No text extracted."}</pre>
      </GlassCard>
      <GlassCard>
        <div className="text-sm font-semibold">Suspicious regions</div>
        <div className="relative mt-3 aspect-[4/3] overflow-hidden rounded-lg border border-white/10 bg-gradient-to-br from-white/5 to-black/40">
          <div className="grid-bg absolute inset-0 opacity-40" />
          <div className="absolute inset-4 rounded-md border border-white/15 bg-white/5 p-3">
            <div className="text-mono text-[10px] uppercase tracking-widest text-muted-foreground">Government of India</div>
            <div className="text-mono mt-2 text-xs">Central Bureau of Investigation</div>
            <div className="mt-3 h-12 w-16 rounded-sm border border-white/10 bg-white/5" />
          </div>
          {d.fakeId.regions.map((r, i) => (
            <div
              key={i}
              className="absolute border-2 border-dashed"
              style={{
                left: `${r.x}%`, top: `${r.y}%`, width: `${r.w}%`, height: `${r.h}%`,
                borderColor: "var(--risk-critical)",
                boxShadow: `0 0 20px color-mix(in oklab, var(--risk-critical) 40%, transparent)`,
              }}
            >
              <span className="absolute -top-5 left-0 text-[10px] uppercase tracking-widest" style={{ color: "var(--risk-critical)" }}>anomaly</span>
            </div>
          ))}
        </div>
      </GlassCard>
      <GlassCard>
        <MetricRow label="Forgery detection" value={d.forgery.verdict} confidence={d.forgery.confidence} />
      </GlassCard>
      <GlassCard>
        <MetricRow label="Fake ID detection" value={d.fakeId.verdict} confidence={d.fakeId.confidence} />
      </GlassCard>
    </div>
  );
}

function MetricRow({ label, value, confidence }: { label: string; value: string; confidence: number }) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold">{label}</div>
        <div className="text-mono text-xs text-muted-foreground">{Math.round(confidence * 100)}%</div>
      </div>
      <div className="mt-2 text-lg" style={{ color: confidence > 0.6 ? "var(--risk-critical)" : "var(--muted-foreground)" }}>{value}</div>
      <div className="mt-3 h-1.5 w-full rounded-full bg-white/5">
        <div className="h-full rounded-full" style={{ width: `${confidence * 100}%`, background: "linear-gradient(90deg, var(--neon-cyan), var(--risk-critical))" }} />
      </div>
    </div>
  );
}

function NetworkDetail() {
  const { activeCase } = useAnalysis();
  const d = activeCase.details.network;
  const rows = [
    { label: "Phone", value: d.phone, flagged: d.flags.phone },
    { label: "Bank account", value: d.bank, flagged: d.flags.bank },
    { label: "Email", value: d.email, flagged: d.flags.email },
    { label: "IP address", value: d.ip, flagged: d.flags.ip },
  ];
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <GlassCard>
        <div className="text-sm font-semibold">Network entities</div>
        <div className="mt-3 space-y-2">
          {rows.map((r) => (
            <div key={r.label} className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 p-3">
              <div>
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{r.label}</div>
                <div className="text-mono mt-1 text-sm">{r.value}</div>
              </div>
              {r.flagged ? <Chip tone="danger">flagged</Chip> : <Chip tone="ok">clean</Chip>}
            </div>
          ))}
        </div>
      </GlassCard>
      <GlassCard>
        <div className="text-sm font-semibold">Relationship graph</div>
        <div className="relative mt-3 h-64">
          <svg viewBox="0 0 400 240" className="h-full w-full">
            <defs>
              <linearGradient id="ng" x1="0" x2="1"><stop stopColor="var(--neon-cyan)" /><stop offset="1" stopColor="var(--risk-critical)" /></linearGradient>
            </defs>
            {[
              { x: 60, y: 60, label: "phone" },
              { x: 60, y: 180, label: "email" },
              { x: 200, y: 120, label: "account" },
              { x: 320, y: 60, label: "IP" },
              { x: 320, y: 180, label: "cluster" },
            ].map((n, i, arr) => (
              <g key={i}>
                {i < arr.length - 1 && <line x1={n.x} y1={n.y} x2={arr[(i + 1) % arr.length].x} y2={arr[(i + 1) % arr.length].y} stroke="url(#ng)" strokeOpacity="0.5" strokeWidth="1.5">
                  <animate attributeName="stroke-dashoffset" from="0" to="16" dur="1.6s" repeatCount="indefinite" />
                </line>}
                <line x1={n.x} y1={n.y} x2={200} y2={120} stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
                <circle cx={n.x} cy={n.y} r={n.label === "cluster" ? 20 : 14} fill={n.label === "cluster" ? "var(--risk-critical)" : "rgba(255,255,255,0.08)"} stroke="rgba(255,255,255,0.3)" />
                <text x={n.x} y={n.y + 34} textAnchor="middle" fontSize="10" fill="rgba(255,255,255,0.7)" fontFamily="var(--font-mono)">{n.label}</text>
              </g>
            ))}
          </svg>
        </div>
      </GlassCard>
      <GlassCard className="lg:col-span-2" glow="var(--risk-critical)">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Known scam cluster</div>
            <div className="text-mono mt-1 text-lg font-semibold">{d.cluster.id}</div>
            <p className="mt-2 max-w-xl text-sm text-muted-foreground">{d.cluster.description}</p>
          </div>
          <div className="text-right">
            <div className="text-mono text-3xl font-semibold" style={{ color: "var(--risk-critical)" }}>{d.cluster.reports}</div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Prior reports</div>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
