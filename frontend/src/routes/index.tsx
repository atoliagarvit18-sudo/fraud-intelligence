import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { AudioLines, FileText, ScanEye, Network, ArrowRight, Shield, Zap, PlayCircle, Loader2 } from "lucide-react";
import { ParticleBackground } from "@/components/soc/ParticleBackground";
import { GlassCard } from "@/components/soc/GlassCard";
import { CountUp } from "@/components/soc/CountUp";
import { useAnalysis } from "@/store/analysis";
import { toast } from "sonner";

export const Route = createFileRoute("/")({
  component: Landing,
});

const features = [
  { icon: ScanEye,    title: "Agent 1 — Visual Intel", desc: "OpenCV currency verification, fake ID detection and document forgery analysis.", color: "var(--neon-violet)" },
  { icon: FileText,   title: "Agent 2 — OSINT Campaign Intel", desc: "Live scraping of Reddit, Telegram & cybercrime complaints into MongoDB to track campaigns.", color: "var(--neon-blue)" },
  { icon: AudioLines, title: "Agent 3 — Speech Intel", desc: "Detect coercive tone, scripted patterns and synthetic voice artifacts in call recordings.", color: "var(--neon-cyan)" },
  { icon: Network,    title: "Agent 4 — Network Fusion", desc: "Cross-references all agents, maps criminal operator networks and projects 24h/48h victim surge.", color: "var(--risk-medium)" },
];

const stats = [
  { label: "Cases analyzed",    value: 12400, suffix: "+" },
  { label: "Detection accuracy", value: 97,    suffix: "%" },
  { label: "AI agents",          value: 4 },
  { label: "Avg. analysis time", value: 6.2,   suffix: "s" },
];

function Landing() {
  const nav = useNavigate();
  const { loadSampleCase, isLoading } = useAnalysis();

  return (
    <div className="relative min-h-screen overflow-hidden">
      <ParticleBackground />
      <header className="relative z-10 flex items-center justify-between px-6 py-5 md:px-10">
        <Link to="/" className="flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-xl border border-white/10" style={{ background: "linear-gradient(135deg, var(--neon-blue), var(--neon-violet))" }}>
            <Shield size={18} className="text-white" />
          </div>
          <div>
            <div className="text-sm font-semibold" style={{ fontFamily: "var(--font-display)" }}>Fraud Intelligence</div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Platform</div>
          </div>
        </Link>
        <nav className="hidden gap-6 text-sm text-muted-foreground md:flex">
          <a className="hover:text-foreground" href="#agents">Agents</a>
          <a className="hover:text-foreground" href="#stats">Stats</a>
          <Link to="/cases" className="hover:text-foreground">Cases</Link>
        </nav>
        <Link to="/dashboard" className="rounded-lg border border-white/15 bg-white/5 px-4 py-2 text-xs font-medium hover:bg-white/10">Open console</Link>
      </header>

      <section className="relative z-10 mx-auto max-w-6xl px-6 pt-12 text-center md:pt-24">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full pulse-dot" style={{ background: "var(--neon-cyan)" }} />
          Multi-Agent AI · Real-time SOC
        </motion.div>
        <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.7 }}
          className="mx-auto mt-6 max-w-4xl text-4xl font-semibold leading-[1.05] tracking-tight md:text-6xl" style={{ fontFamily: "var(--font-display)" }}>
          Fraud Intelligence
          <br />
          <span style={{ background: "linear-gradient(90deg, var(--neon-cyan), var(--neon-blue), var(--neon-violet))", WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent" }}>
            for the deepfake era.
          </span>
        </motion.h1>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2, duration: 0.7 }}
          className="mx-auto mt-5 max-w-2xl text-sm text-muted-foreground md:text-base">
          A multi-agent AI system that detects Digital Arrest scams, phishing, financial fraud and counterfeit documents — fused into a single verdict analysts can trust.
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.7 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <button onClick={() => nav({ to: "/analysis" })}
            className="group inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold text-white shadow-[0_0_40px_-6px_var(--neon-blue)] transition hover:shadow-[0_0_60px_-2px_var(--neon-blue)]"
            style={{ background: "linear-gradient(135deg, var(--neon-blue), var(--neon-violet))" }}>
            <Zap size={16} /> Start Analysis <ArrowRight size={16} className="transition group-hover:translate-x-1" />
          </button>
          <button disabled={isLoading}
            onClick={async () => {
              const c = await loadSampleCase();
              if (c) nav({ to: "/dashboard" });
              else toast.error("Could not load live sample — API server may be offline", { description: "Start the API with: .\\start_api.ps1" });
            }}
            className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-5 py-3 text-sm font-medium hover:bg-white/10 disabled:opacity-50">
            {isLoading ? <Loader2 size={16} className="animate-spin" /> : <PlayCircle size={16} />} View Live Sample
          </button>
        </motion.div>

        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.4, duration: 0.9 }}
          className="relative mx-auto mt-16 h-72 max-w-3xl md:h-96">
          <div className="absolute inset-0 grid place-items-center">
            <div className="relative float-slow">
              <svg width="320" height="320" viewBox="0 0 320 320" className="drop-shadow-[0_0_60px_rgba(80,180,255,0.35)]">
                <defs>
                  <linearGradient id="sg" x1="0" x2="1" y1="0" y2="1">
                    <stop offset="0%" stopColor="var(--neon-cyan)" />
                    <stop offset="50%" stopColor="var(--neon-blue)" />
                    <stop offset="100%" stopColor="var(--neon-violet)" />
                  </linearGradient>
                </defs>
                {[...Array(4)].map((_, i) => (
                  <circle key={i} cx="160" cy="160" r={40 + i * 30} fill="none" stroke="url(#sg)" strokeOpacity={0.3 - i * 0.05} strokeWidth="1" />
                ))}
                <path d="M160 60 L240 100 L240 170 C240 220 200 250 160 260 C120 250 80 220 80 170 L80 100 Z" fill="none" stroke="url(#sg)" strokeWidth="2" />
                <path d="M130 165 L155 190 L200 140" fill="none" stroke="url(#sg)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
          </div>
        </motion.div>
      </section>

      <section id="agents" className="relative z-10 mx-auto mt-8 grid max-w-6xl gap-4 px-6 pb-16 md:grid-cols-2 lg:grid-cols-4">
        {features.map((f, i) => (
          <motion.div key={f.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08 }}>
            <GlassCard interactive glow={f.color} className="h-full">
              <div className="grid h-11 w-11 place-items-center rounded-xl border" style={{ borderColor: f.color, color: f.color, background: `color-mix(in oklab, ${f.color} 12%, transparent)` }}>
                <f.icon size={20} />
              </div>
              <div className="mt-4 text-sm font-semibold">{f.title}</div>
              <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{f.desc}</p>
            </GlassCard>
          </motion.div>
        ))}
      </section>

      <section id="stats" className="relative z-10 mx-auto max-w-6xl px-6 pb-24">
        <GlassCard className="grid grid-cols-2 gap-6 py-6 md:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <div className="text-mono text-3xl font-semibold" style={{ color: "var(--neon-cyan)" }}>
                <CountUp to={s.value} suffix={s.suffix ?? ""} />
              </div>
              <div className="mt-1 text-[10px] uppercase tracking-widest text-muted-foreground">{s.label}</div>
            </div>
          ))}
        </GlassCard>
      </section>
    </div>
  );
}
