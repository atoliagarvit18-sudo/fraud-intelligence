import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AudioLines, FileText, ScanEye, Network, Check, Loader2, Zap, ArrowRight } from "lucide-react";
import { AppShell } from "@/components/soc/AppShell";
import { GlassCard } from "@/components/soc/GlassCard";
import { tierColor, tierFromScore } from "@/mocks/cases";
import { useAnalysis } from "@/store/analysis";

export const Route = createFileRoute("/processing")({
  head: () => ({ meta: [{ title: "Processing — Fraud Intelligence Platform" }] }),
  component: Processing,
});

const STAGES = [
  { key: "speech",  label: "Speech Intelligence",  icon: AudioLines, agentLabel: "Agent 3 — Call Analysis" },
  { key: "visual",  label: "Visual Intelligence",   icon: ScanEye,    agentLabel: "Agent 1 — Currency CV" },
  { key: "text",    label: "OSINT Campaign Intel",  icon: FileText,   agentLabel: "Agent 2 — Reddit/Telegram Scraper" },
  { key: "network", label: "Network Intelligence",  icon: Network,    agentLabel: "Agent 4 — Fusion Engine" },
] as const;

const BOOT_LOGS = [
  "[SYSTEM] session initialized · multi-agent orchestrator starting",
  "[AGENT1] loading OpenCV currency classifier...",
  "[AGENT1] processing note image — deskewing, feature extraction",
  "[AGENT2] connecting to MongoDB fraud_intelligence.events...",
  "[AGENT2] scraping live feeds: Reddit r/India, Telegram channels, National Cybercrime Portal...",
  "[AGENT2] clustering threat vectors (Digital Arrest & financial fraud patterns)...",
  "[AGENT3] loading Whisper ASR model...",
  "[AGENT3] running keyword + semantic + Groq LLM analyzers...",
  "[FUSION] cross-agent correlation engine initializing...",
  "[FUSION] building criminal network graph (NetworkX)...",
  "[FUSION] computing 24h victimisation projection...",
  "[FUSION] generating SHA-256 evidence package...",
  "[SYSTEM] synthesizing unified verdict...",
];

function Processing() {
  const nav = useNavigate();
  const { activeCase, isLoading, loadingSessionId, selectSample } = useAnalysis();

  const [stage, setStage]           = useState(-1);
  const [logs, setLogs]             = useState<string[]>([]);
  const [liveScores, setLiveScores] = useState<Record<string, number>>({});
  const logRef     = useRef<HTMLDivElement>(null);
  const bootLogIdx = useRef(0);

  // Guard: if someone hits /processing directly (no active session, not loading),
  // redirect to /analysis so they start from the form instead of crashing.
  useEffect(() => {
    if (!isLoading && !loadingSessionId) {
      // Allow a short grace period in case the state just got set
      const t = setTimeout(() => {
        const s = useAnalysis.getState();
        if (!s.isLoading && !s.loadingSessionId) {
          nav({ to: "/analysis" });
        }
      }, 800);
      return () => clearTimeout(t);
    }
  }, []);

  useEffect(() => { if (activeCase?.caseId) selectSample(activeCase.caseId); }, []);

  useEffect(() => {
    let cancelled = false;
    let s = -1;
    const advance = () => {
      if (cancelled) return;
      s++;
      setStage(s);
      if (s < 4)      setTimeout(advance, 1800);
      else if (s === 4) setTimeout(advance, 2500);
      else if (s === 5) {
        const poll = setInterval(() => {
          if (cancelled) { clearInterval(poll); return; }
          if (!useAnalysis.getState().isLoading) {
            clearInterval(poll);
            setTimeout(() => !cancelled && nav({ to: "/dashboard" }), 600);
          }
        }, 200);
      }
    };
    const t = setTimeout(advance, 300);
    return () => { cancelled = true; clearTimeout(t); };
  }, [nav]);

  useEffect(() => {
    const int = setInterval(() => {
      if (bootLogIdx.current < BOOT_LOGS.length) {
        setLogs((prev) => [...prev, BOOT_LOGS[bootLogIdx.current++]]);
        if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
      } else { clearInterval(int); }
    }, 520);
    return () => clearInterval(int);
  }, []);

  useEffect(() => {
    const sid = useAnalysis.getState().loadingSessionId;
    if (!sid) return;
    const es = new EventSource(`/api/v1/analyze/stream/${sid}`);
    es.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data) as { agent: string; msg: string };
        if (d.msg === "__DONE__") { es.close(); return; }
        const line = `[${d.agent}] ${d.msg}`;
        setLogs((prev) => [...prev.slice(-60), line]);
        if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
      } catch { /* ignore */ }
    };
    es.onerror = () => es.close();
    return () => es.close();
  }, []);

  useEffect(() => {
    if (!isLoading) {
      const c = useAnalysis.getState().activeCase;
      setLiveScores({
        speech:  c.agents.speech.score,
        visual:  c.agents.visual.score,
        text:    c.agents.text.score,
        network: c.agents.network.score,
      });
    }
  }, [isLoading]);

  const doneAgents = useMemo(() => Math.max(0, Math.min(stage, 4)), [stage]);

  return (
    <AppShell>
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1fr_320px]">
        <div>
          <div className="mb-6">
            <div className="text-[10px] uppercase tracking-[0.25em] text-muted-foreground">Step 2 of 3</div>
            <h1 className="mt-1 text-3xl font-semibold" style={{ fontFamily: "var(--font-display)" }}>Multi-agent analysis in progress</h1>
            <p className="mt-2 text-sm text-muted-foreground">Four specialized AI agents run in parallel against live threat intelligence, then fuse their verdicts into a single actionable decision.</p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {STAGES.map((sg, i) => {
              const status = stage > i ? "complete" : stage === i ? "scanning" : "idle";
              const score  = liveScores[sg.key] ?? (status === "complete" ? activeCase.agents[sg.key].score : 0);
              const tier   = tierFromScore(score);
              const color  = tierColor(tier);
              return (
                <GlassCard key={sg.key} glow={status !== "idle" ? color : undefined} className="relative">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="grid h-11 w-11 place-items-center rounded-xl border transition"
                        style={{ borderColor: status === "idle" ? "rgba(255,255,255,0.1)" : color, color: status === "idle" ? "var(--muted-foreground)" : color, background: status !== "idle" ? `color-mix(in oklab, ${color} 12%, transparent)` : undefined }}>
                        <sg.icon size={20} />
                      </div>
                      <div>
                        <div className="text-sm font-semibold">{sg.label}</div>
                        <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{sg.agentLabel}</div>
                      </div>
                    </div>
                    <div className="text-xs">
                      {status === "idle"     && <span className="text-muted-foreground">Queued</span>}
                      {status === "scanning" && <span className="inline-flex items-center gap-1" style={{ color }}><Loader2 size={12} className="animate-spin" /> Scanning</span>}
                      {status === "complete" && <span className="inline-flex items-center gap-1" style={{ color }}><Check size={12} /> Complete</span>}
                    </div>
                  </div>
                  <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-white/5">
                    <motion.div key={status} initial={{ width: status === "complete" ? "100%" : 0 }}
                      animate={{ width: status === "scanning" ? "80%" : status === "complete" ? "100%" : "0%" }}
                      transition={{ duration: status === "scanning" ? 1.6 : 0.4 }}
                      className="h-full rounded-full" style={{ background: `linear-gradient(90deg, ${color}, var(--neon-blue))` }} />
                  </div>
                  <AnimatePresence>
                    {status === "complete" && score > 0 && (
                      <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="mt-3 flex items-baseline gap-2">
                        <div className="text-mono text-2xl font-semibold" style={{ color }}>{score}</div>
                        <div className="text-[10px] uppercase tracking-widest text-muted-foreground">risk score</div>
                        {!isLoading && <span className="ml-auto text-[10px] text-[color:var(--risk-safe)]">● live</span>}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </GlassCard>
              );
            })}
          </div>

          <div className="mt-6">
            <GlassCard glow={stage >= 4 ? "var(--neon-violet)" : undefined}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="grid h-11 w-11 place-items-center rounded-xl border" style={{ borderColor: "var(--neon-violet)", color: "var(--neon-violet)", background: "color-mix(in oklab, var(--neon-violet) 12%, transparent)" }}>
                    <Zap size={20} />
                  </div>
                  <div>
                    <div className="text-sm font-semibold">Agent 4 — Fusion & Prediction Engine</div>
                    <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
                      {stage < 4 ? "Waiting for agents" : stage === 4 ? "Correlating · mapping criminal network · projecting victims…" : "Verdict ready"}
                    </div>
                  </div>
                </div>
                {stage >= 5 && !isLoading && (
                  <button onClick={() => nav({ to: "/dashboard" })} className="inline-flex items-center gap-1 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs hover:bg-white/10">
                    View results <ArrowRight size={12} />
                  </button>
                )}
              </div>
              <div className="relative mt-6 h-40">
                <svg viewBox="0 0 400 160" className="h-full w-full">
                  <defs><linearGradient id="fx" x1="0" x2="1"><stop stopColor="var(--neon-cyan)" /><stop offset="1" stopColor="var(--neon-violet)" /></linearGradient></defs>
                  {[{ y: 20 }, { y: 60 }, { y: 100 }, { y: 140 }].map((p, i) => (
                    <g key={i}>
                      <line x1="40" y1={p.y} x2="200" y2="80" stroke="url(#fx)" strokeWidth={stage >= 4 ? 1.5 : 0.6} strokeOpacity={stage >= 4 ? 0.9 : 0.3} />
                      <circle cx="40" cy={p.y} r="6" fill={doneAgents > i ? "var(--neon-cyan)" : "rgba(255,255,255,0.2)"} />
                    </g>
                  ))}
                  <circle cx="200" cy="80" r={stage >= 4 ? 20 : 14} fill="url(#fx)" opacity={stage >= 4 ? 1 : 0.4}>
                    {stage >= 4 && <animate attributeName="r" values="18;24;18" dur="1.6s" repeatCount="indefinite" />}
                  </circle>
                  <line x1="220" y1="80" x2="380" y2="80" stroke="url(#fx)" strokeWidth={stage >= 5 ? 2 : 0.6} strokeOpacity={stage >= 5 ? 1 : 0.3} />
                  <rect x="330" y="60" width="60" height="40" rx="6" fill="none" stroke={stage >= 5 ? "var(--risk-critical)" : "rgba(255,255,255,0.2)"} strokeWidth="1.5" />
                  <text x="360" y="85" textAnchor="middle" fill={stage >= 5 ? "var(--risk-critical)" : "rgba(255,255,255,0.4)"} fontSize="10" fontFamily="var(--font-mono)">VERDICT</text>
                </svg>
              </div>
            </GlassCard>
          </div>
        </div>

        <GlassCard className="h-fit lg:sticky lg:top-20">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Live log</div>
            <span className="inline-flex items-center gap-1 text-[10px] text-muted-foreground">
              <span className="h-1.5 w-1.5 rounded-full pulse-dot" style={{ background: isLoading ? "var(--risk-safe)" : "var(--risk-medium)" }} />
              {isLoading ? "streaming" : "complete"}
            </span>
          </div>
          <div ref={logRef} className="text-mono h-96 overflow-y-auto rounded-lg border border-white/10 bg-black/40 p-3 text-[11px] leading-relaxed">
            {logs.map((l, i) => {
              const agentKey = l.match(/^\[([A-Z0-9]+)\]/)?.[1] ?? "SYSTEM";
              const color =
                agentKey === "AGENT3" ? "var(--neon-cyan)"
                : agentKey === "AGENT2" ? "var(--neon-blue)"
                : agentKey === "AGENT1" ? "var(--neon-violet)"
                : agentKey === "FUSION" ? "var(--risk-medium)"
                : "var(--muted-foreground)";
              return (
                <div key={i} className="whitespace-pre-wrap">
                  <span style={{ color }}>{l.split(" ")[0]}</span>{" "}
                  <span className="text-foreground/80">{l.split(" ").slice(1).join(" ")}</span>
                </div>
              );
            })}
          </div>
        </GlassCard>
      </div>
    </AppShell>
  );
}
