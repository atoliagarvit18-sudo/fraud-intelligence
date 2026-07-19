import { createFileRoute } from "@tanstack/react-router";
import { motion } from "framer-motion";
import {
  Radar as RadarIcon, ShieldAlert, Clock, FileText, AudioLines, ImageIcon,
  Phone, Globe, ChevronRight, ExternalLink, CheckCircle2, Network,
  AlertTriangle, TrendingUp, Package, Wifi, WifiOff,
} from "lucide-react";
import { AppShell } from "@/components/soc/AppShell";
import { GlassCard } from "@/components/soc/GlassCard";
import { RiskGauge } from "@/components/soc/RiskGauge";
import { AgentCard } from "@/components/soc/AgentCard";
import { RiskBadge, Chip } from "@/components/soc/Badge";
import { useAnalysis } from "@/store/analysis";
import { tierColor, cases } from "@/mocks/cases";
import { toast } from "sonner";
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer, PolarRadiusAxis,
  AreaChart, Area, XAxis, YAxis, Tooltip,
} from "recharts";

export const Route = createFileRoute("/dashboard")({
  head: () => ({ meta: [{ title: "Dashboard — Fraud Intelligence Platform" }] }),
  component: Dashboard,
});

const sourceIcon = { audio: AudioLines, image: ImageIcon, text: FileText, phone: Phone, url: Globe } as const;

function Dashboard() {
  const { activeCase, selectSample } = useAnalysis();
  const c = activeCase;
  const color = tierColor(c.tier);

  const radarData = (Object.entries(c.agents) as [keyof typeof c.agents, typeof c.agents.speech][])
    .map(([k, v]) => ({ agent: k[0].toUpperCase() + k.slice(1), score: v.score }));

  const net  = (c as any).criminalNetwork;
  const pred = (c as any).victimPrediction;
  const evp  = (c as any).evidencePackage;
  const srcs = (c as any)._sources;

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl space-y-6">

        {/* Case switcher */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-[0.25em] text-muted-foreground">Case results</div>
            <h1 className="mt-1 text-2xl font-semibold" style={{ fontFamily: "var(--font-display)" }}>Verdict console</h1>
          </div>
          <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1 text-xs">
            {cases.map((cc) => (
              <button key={cc.caseId} onClick={() => selectSample(cc.caseId)}
                className={`rounded-full px-3 py-1.5 transition ${cc.caseId === c.caseId ? "bg-white/10 text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                <span className="text-mono">{cc.caseId.slice(-5)}</span>
                <span className="ml-2 hidden md:inline">· {cc.verdict}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Hero */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="grid gap-6 lg:grid-cols-[380px_1fr]">
          <GlassCard glow={color} className="flex flex-col items-center justify-center py-8">
            <RiskGauge score={c.overallRisk} tier={c.tier} />
            <div className="mt-6 text-center">
              <div className="text-lg font-semibold" style={{ color }}>{c.verdict}</div>
              <div className="mt-1 text-xs text-muted-foreground">Confidence <span className="text-mono text-foreground">{c.confidence}%</span></div>
            </div>
            {srcs && (
              <div className="mt-4 flex flex-col gap-1 w-full px-4">
                {[
                  { label: "Agent 1 (Currency)", mock: srcs.agent1Mock },
                  { label: "Agent 2 (OSINT)",    mock: srcs.agent2Mock },
                  { label: "Agent 3 (Call)",      mock: srcs.agent3Mock },
                ].map((s) => (
                  <div key={s.label} className="flex items-center justify-between text-[10px]">
                    <span className="text-muted-foreground">{s.label}</span>
                    <span className={`flex items-center gap-1 font-medium ${s.mock ? "text-yellow-500" : "text-[color:var(--risk-safe)]"}`}>
                      {s.mock ? <WifiOff size={10} /> : <Wifi size={10} />}
                      {s.mock ? "fallback" : "live"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </GlassCard>

          <GlassCard>
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
              <div>
                <div className="text-[10px] uppercase tracking-[0.25em] text-muted-foreground">Case</div>
                <div className="text-mono mt-1 text-lg font-semibold">{c.caseId}</div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <RiskBadge tier={c.tier} />
                <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] text-muted-foreground">
                  <Clock size={12} /> {new Date(c.timestamp).toUTCString().slice(5, 22)}
                </span>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Evidence</div>
              {c.sources.map((s) => { const Icon = sourceIcon[s]; return <Chip key={s}><Icon size={12} /> {s}</Chip>; })}
            </div>
            <div className="mt-4 h-56">
              <ResponsiveContainer>
                <RadarChart data={radarData} outerRadius="80%">
                  <PolarGrid stroke="rgba(255,255,255,0.1)" />
                  <PolarAngleAxis dataKey="agent" tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 11 }} />
                  <PolarRadiusAxis stroke="transparent" tick={false} domain={[0, 100]} />
                  <Radar dataKey="score" stroke={color} fill={color} fillOpacity={0.25} strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </GlassCard>
        </motion.div>

        {/* Agent verdicts */}
        <div>
          <SectionTitle icon={RadarIcon} title="Agent verdicts" subtitle="Independent scores from each specialized model" />
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {(Object.entries(c.agents) as [keyof typeof c.agents, typeof c.agents.speech][]).map(([k, v]) => (
              <AgentCard key={k} agentKey={k} data={v} />
            ))}
          </div>
        </div>

        {/* Fusion + Explainability */}
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <FusionPanel />
          <ExplainabilityPanel />
        </div>

        {/* Criminal Network + Victim Prediction */}
        {(net || pred) && (
          <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
            {net  && <CriminalNetworkCard net={net} />}
            {pred && <VictimPredictionCard pred={pred} />}
          </div>
        )}

        {/* Recommendations + Timeline */}
        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <GlassCard>
            <SectionTitle icon={ShieldAlert} title="Recommended actions" subtitle="Prioritized response for this case" inline />
            <ul className="mt-4 space-y-2">
              {c.recommendations.map((r, i) => {
                const rc = r.urgency === "critical" ? "var(--risk-critical)" : r.urgency === "warning" ? "var(--risk-medium)" : "var(--risk-safe)";
                return (
                  <li key={i} className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-3">
                    <span className="grid h-8 w-8 place-items-center rounded-lg flex-shrink-0" style={{ background: `color-mix(in oklab, ${rc} 15%, transparent)`, color: rc }}>
                      <CheckCircle2 size={16} />
                    </span>
                    <span className="flex-1 text-sm">{r.action}</span>
                    <span className="text-[10px] uppercase tracking-widest flex-shrink-0" style={{ color: rc }}>{r.urgency}</span>
                    {r.action.toLowerCase().includes("cyber crime") && (
                      <button
                        onClick={() => { toast.success("Opening cybercrime portal", { description: `Case ${c.caseId} — evidence package ready` }); window.open("https://cybercrime.gov.in", "_blank"); }}
                        className="inline-flex items-center gap-1 rounded-md border border-white/15 bg-white/5 px-2 py-1 text-[11px] hover:bg-white/10"
                      >Report <ExternalLink size={11} /></button>
                    )}
                  </li>
                );
              })}
            </ul>
          </GlassCard>

          <GlassCard>
            <SectionTitle icon={Clock} title="Activity timeline" inline />
            <ol className="mt-4 space-y-4">
              {c.timeline.map((t, i) => {
                const active = i === c.timeline.length - 1;
                return (
                  <li key={i} className="flex items-start gap-3">
                    <div className="relative mt-1">
                      <span className={`block h-2.5 w-2.5 rounded-full ${active ? "pulse-dot" : ""}`} style={{ background: active ? "var(--neon-cyan)" : color }} />
                      {i < c.timeline.length - 1 && <span className="absolute left-1/2 top-3 h-8 w-px -translate-x-1/2 bg-white/10" />}
                    </div>
                    <div className="flex-1">
                      <div className="text-sm">{t.step}</div>
                      <div className="text-mono text-[11px] text-muted-foreground">{t.timestamp}</div>
                    </div>
                    <ChevronRight size={14} className="text-muted-foreground/50" />
                  </li>
                );
              })}
            </ol>
          </GlassCard>
        </div>

        {/* Evidence Package */}
        {evp && <EvidencePackageCard evp={evp} caseId={c.caseId} />}
      </div>
    </AppShell>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionTitle({ icon: Icon, title, subtitle, inline }: { icon: any; title: string; subtitle?: string; inline?: boolean }) {
  return (
    <div className={inline ? "flex items-center justify-between" : "mb-4 flex items-center justify-between"}>
      <div className="flex items-center gap-2">
        <Icon size={16} className="text-muted-foreground" />
        <div>
          <div className="text-sm font-semibold">{title}</div>
          {subtitle && <div className="text-[11px] text-muted-foreground">{subtitle}</div>}
        </div>
      </div>
    </div>
  );
}

function FusionPanel() {
  const { activeCase: c } = useAnalysis();
  const color = tierColor(c.tier);
  const agents = Object.entries(c.agents);
  return (
    <GlassCard>
      <SectionTitle icon={RadarIcon} title="AI Fusion Engine" subtitle="How agent verdicts combine into the final decision" />
      <div className="relative h-64">
        <svg viewBox="0 0 400 240" className="h-full w-full">
          <defs><linearGradient id="fusegrad" x1="0" x2="1"><stop stopColor="var(--neon-cyan)" /><stop offset="1" stopColor="var(--neon-violet)" /></linearGradient></defs>
          {agents.map(([k, v], i) => {
            const y = 30 + i * 60;
            const strokeW = 1 + (v.confidence / 100) * 3;
            return (
              <g key={k}>
                <line x1="80" y1={y} x2="200" y2="120" stroke="url(#fusegrad)" strokeWidth={strokeW} strokeOpacity="0.6">
                  <animate attributeName="stroke-dashoffset" from="0" to="20" dur="2s" repeatCount="indefinite" />
                </line>
                <circle cx="80" cy={y} r="18" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.15)" />
                <text x="80" y={y + 4} textAnchor="middle" fontSize="10" fill="rgba(255,255,255,0.85)" fontFamily="var(--font-mono)">{v.score}</text>
                <text x="80" y={y + 32} textAnchor="middle" fontSize="9" fill="rgba(255,255,255,0.5)">{k}</text>
              </g>
            );
          })}
          <circle cx="200" cy="120" r="28" fill="url(#fusegrad)" opacity="0.9">
            <animate attributeName="r" values="26;32;26" dur="2.4s" repeatCount="indefinite" />
          </circle>
          <text x="200" y="124" textAnchor="middle" fontSize="10" fill="white" fontFamily="var(--font-mono)">FUSE</text>
          <line x1="228" y1="120" x2="330" y2="120" stroke={color} strokeWidth="2" />
          <rect x="330" y="95" width="60" height="50" rx="8" fill={`color-mix(in oklab, ${color} 25%, transparent)`} stroke={color} />
          <text x="360" y="118" textAnchor="middle" fontSize="10" fill={color} fontFamily="var(--font-mono)">VERDICT</text>
          <text x="360" y="132" textAnchor="middle" fontSize="12" fill={color} fontFamily="var(--font-mono)" fontWeight="600">{c.overallRisk}</text>
        </svg>
      </div>
    </GlassCard>
  );
}

function ExplainabilityPanel() {
  const { activeCase: c } = useAnalysis();
  return (
    <GlassCard>
      <SectionTitle icon={FileText} title="Explainability" subtitle="Signal contributions to the fused score" />
      <ul className="mt-4 space-y-3">
        {c.explainability.map((e) => (
          <li key={e.signal}>
            <div className="flex items-center justify-between text-sm">
              <span>{e.signal}</span>
              <span className="text-mono text-xs text-muted-foreground">{Math.round(e.weight * 100)}%</span>
            </div>
            <div className="mt-1.5 h-1.5 w-full rounded-full bg-white/5">
              <div className="h-full rounded-full" style={{ width: `${Math.min(e.weight * 100 * 3.5, 100)}%`, background: "linear-gradient(90deg, var(--neon-cyan), var(--neon-blue), var(--neon-violet))" }} />
            </div>
          </li>
        ))}
      </ul>
    </GlassCard>
  );
}

function StatBox({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="text-mono mt-1 text-sm font-semibold truncate" style={{ color }}>{value}</div>
    </div>
  );
}

function CriminalNetworkCard({ net }: { net: any }) {
  const strengthColor = net.evidenceStrength === "STRONG" ? "var(--risk-critical)" : net.evidenceStrength === "MEDIUM" ? "var(--risk-medium)" : "var(--risk-safe)";
  return (
    <GlassCard glow={strengthColor}>
      <SectionTitle icon={Network} title="Criminal Network Hypothesis" subtitle="AI-inferred operator cell from multi-modal signals" />
      <div className="mt-4 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <StatBox label="Cell ID"            value={net.cellId}              color="var(--neon-cyan)" />
          <StatBox label="Est. Operators"     value={net.estimatedOperators}  color="var(--risk-critical)" />
          <StatBox label="Monthly Victims"    value={`~${net.monthlyVictims}`} color="var(--risk-high)" />
          <StatBox label="Evidence Strength"  value={net.evidenceStrength}    color={strengthColor} />
        </div>
        <div className="rounded-xl border border-white/10 bg-black/20 p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground mb-2">
            <span>Network graph</span>
            <span className="text-mono">{net.graphNodes} nodes · {net.graphEdges} edges</span>
          </div>
          <div className="flex gap-2 flex-wrap">
            {(net.communication || []).slice(0, 4).map((ch: string, i: number) => (
              <span key={i} className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px]">{ch}</span>
            ))}
            {(net.digitalInfra || []).slice(0, 3).map((d: string, i: number) => (
              <span key={i} className="rounded-full border border-[color:var(--risk-high)]/30 bg-[color:var(--risk-high)]/5 px-2 py-0.5 text-[10px] text-[color:var(--risk-high)]">{d.replace(/_/g, " ")}</span>
            ))}
          </div>
        </div>
        <div className="space-y-1.5 text-[11px]">
          <div className="flex justify-between"><span className="text-muted-foreground">Geography</span><span className="text-mono">{net.geography || "Unknown"}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Modus operandi</span><span className="text-right max-w-[180px] truncate">{net.modusOperandi}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Impersonating</span><span className="text-right">{(net.impersonationTargets || []).slice(0, 2).join(", ")}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Confidence</span><span className="text-mono" style={{ color: strengthColor }}>{(net.confidence * 100).toFixed(0)}%</span></div>
        </div>
      </div>
    </GlassCard>
  );
}

function VictimPredictionCard({ pred }: { pred: any }) {
  const urgColor = pred.urgencyLevel === "IMMEDIATE" ? "var(--risk-critical)" : pred.urgencyLevel === "URGENT" ? "var(--risk-high)" : "var(--risk-medium)";
  const chartData = [
    { t: "Now", victims: 0 },
    { t: "6h",  victims: Math.round(pred.victims24hLow * 0.25) },
    { t: "12h", victims: Math.round(pred.victims24hLow * 0.55) },
    { t: "24h", victims: pred.victims24hHigh },
    { t: "36h", victims: Math.round(pred.victims48hLow * 0.7) },
    { t: "48h", victims: pred.victims48hHigh },
  ];
  return (
    <GlassCard glow={urgColor}>
      <SectionTitle icon={AlertTriangle} title="Victim Prediction Engine" subtitle="Without intervention — probabilistic projection" />
      <div className="mt-4 grid grid-cols-2 gap-3 mb-4">
        <StatBox label="24h projection"  value={`${pred.victims24hLow}–${pred.victims24hHigh}`} color="var(--risk-high)" />
        <StatBox label="48h projection"  value={`${pred.victims48hLow}–${pred.victims48hHigh}`} color="var(--risk-critical)" />
        <StatBox label="Urgency"         value={pred.urgencyLevel}         color={urgColor} />
        <StatBox label="Campaign Growth" value={pred.campaignGrowthRate}   color={pred.campaignGrowthRate === "ACCELERATING" ? "var(--risk-critical)" : "var(--risk-medium)"} />
      </div>
      <div className="h-32">
        <ResponsiveContainer>
          <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="vgrad" x1="0" x2="0" y1="0" y2="1">
                <stop offset="5%"  stopColor={urgColor} stopOpacity={0.4} />
                <stop offset="95%" stopColor={urgColor} stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="t" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 9 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 9 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: "#0a0a0f", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 11 }} itemStyle={{ color: urgColor }} />
            <Area type="monotone" dataKey="victims" stroke={urgColor} strokeWidth={2} fill="url(#vgrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      {pred.postsPerHour !== undefined && (
        <div className="mt-2 flex items-center gap-2 text-[11px] text-muted-foreground">
          <TrendingUp size={12} />
          <span>Campaign velocity: <span className="text-mono text-foreground">{pred.postsPerHour.toFixed(1)} posts/hour</span></span>
        </div>
      )}
    </GlassCard>
  );
}

function EvidencePackageCard({ evp, caseId }: { evp: any; caseId: string }) {
  return (
    <GlassCard glow="var(--risk-safe)" className="border-[color:var(--risk-safe)]/20">
      <SectionTitle icon={Package} title="Legal Evidence Package" subtitle="SHA-256 sealed · chain-of-custody verified · ready for submission" />
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <StatBox label="Package ID"     value={evp.packageId}                       color="var(--neon-cyan)" />
        <StatBox label="Evidence Items" value={`${evp.evidenceCount} items sealed`} color="var(--risk-safe)" />
        <StatBox label="Helpline"       value={evp.helpline}                         color="var(--neon-violet)" />
      </div>
      <div className="mt-4 flex flex-wrap gap-3">
        <a href="https://cybercrime.gov.in" target="_blank" rel="noopener noreferrer"
          onClick={() => toast.success("Opening National Cyber Crime Portal", { description: `Package ${evp.packageId} ready for submission` })}
          className="inline-flex items-center gap-2 rounded-xl border border-[color:var(--risk-safe)]/30 bg-[color:var(--risk-safe)]/10 px-4 py-2 text-xs font-semibold text-[color:var(--risk-safe)] hover:bg-[color:var(--risk-safe)]/20 transition">
          <ExternalLink size={14} /> File on cybercrime.gov.in
        </a>
        {evp.hasRbiAlert && (
          <button onClick={() => toast.success("RBI FICN Alert prepared", { description: "Counterfeit currency report ready for RBI regional office" })}
            className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-xs font-semibold hover:bg-white/10 transition">
            <AlertTriangle size={14} className="text-[color:var(--risk-medium)]" /> Send RBI FICN Alert
          </button>
        )}
      </div>
    </GlassCard>
  );
}
