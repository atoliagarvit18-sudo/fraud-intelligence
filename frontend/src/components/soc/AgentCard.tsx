import { Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { AudioLines, FileText, ScanEye, Network, CheckCircle2, Loader2 } from "lucide-react";
import { tierColor, tierFromScore, type AgentKey, type AgentResult } from "@/mocks/cases";
import { GlassCard } from "./GlassCard";

const meta: Record<AgentKey, { title: string; agentName: string; icon: typeof AudioLines }> = {
  speech: { title: "Speech Intelligence", agentName: "Agent 3 — Call Analysis", icon: AudioLines },
  text: { title: "OSINT Campaign Intelligence", agentName: "Agent 2 — Reddit · Telegram · Complaints Scraper", icon: FileText },
  visual: { title: "Visual Intelligence", agentName: "Agent 1 — Currency & ID CV", icon: ScanEye },
  network: { title: "Network Intelligence", agentName: "Agent 4 — Correlation Engine", icon: Network },
};

export function AgentCard({ agentKey, data, linkTo = true }: { agentKey: AgentKey; data: AgentResult; linkTo?: boolean }) {
  const { title, agentName, icon: Icon } = meta[agentKey];
  const tier = tierFromScore(data.score);
  const color = tierColor(tier);
  const content = (
    <GlassCard interactive={linkTo} glow={color} className="h-full">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-xl border" style={{ borderColor: color, color, background: `color-mix(in oklab, ${color} 12%, transparent)` }}>
            <Icon size={20} />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold">{title}</div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{agentName}</div>
          </div>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
          {data.status === "complete" ? <CheckCircle2 size={12} /> : <Loader2 size={12} className="animate-spin" />}
          {data.status}
        </span>
      </div>
      <div className="mt-5 flex items-end gap-4">
        <div>
          <div className="text-mono text-4xl font-semibold" style={{ color }}>
            {data.score}
          </div>
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Risk score</div>
        </div>
        <div className="ml-auto text-right">
          <div className="text-mono text-lg text-foreground/90">{data.confidence}%</div>
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Confidence</div>
        </div>
      </div>
      <div className="mt-3 h-1 w-full rounded-full bg-white/5">
        <motion.div initial={{ width: 0 }} animate={{ width: `${data.score}%` }} transition={{ duration: 1 }} className="h-full rounded-full" style={{ background: `linear-gradient(90deg, ${color}, var(--neon-blue))` }} />
      </div>
      <p className="mt-4 line-clamp-2 text-xs leading-relaxed text-muted-foreground">{data.summary}</p>
    </GlassCard>
  );
  return linkTo ? (
    <Link to="/agent/$id" params={{ id: agentKey }} className="block h-full">
      {content}
    </Link>
  ) : content;
}
