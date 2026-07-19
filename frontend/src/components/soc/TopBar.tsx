import { Bell, Search } from "lucide-react";
import { useState } from "react";
import { notifications, tierColor } from "@/mocks/cases";
import { motion, AnimatePresence } from "framer-motion";

export function TopBar() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-white/10 bg-black/30 px-4 backdrop-blur-xl md:px-6">
      <div className="flex flex-1 items-center gap-2">
        <div className="relative hidden max-w-sm flex-1 md:block">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            placeholder="Search cases, phone numbers, hashes…"
            className="text-mono w-full rounded-lg border border-white/10 bg-white/5 py-2 pl-9 pr-3 text-xs text-foreground placeholder:text-muted-foreground focus:border-transparent"
          />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-widest text-muted-foreground md:inline-flex">
          <span className="h-1.5 w-1.5 rounded-full pulse-dot" style={{ background: "var(--risk-safe)" }} />
          Systems Online
        </span>
        <div className="relative">
          <button
            onClick={() => setOpen((v) => !v)}
            className="relative grid h-9 w-9 place-items-center rounded-lg border border-white/10 bg-white/5 hover:bg-white/10"
          >
            <Bell size={16} />
            <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full pulse-dot" style={{ background: "var(--risk-critical)" }} />
          </button>
          <AnimatePresence>
            {open && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 6 }}
                className="glass absolute right-0 top-12 z-50 w-80 p-2"
              >
                <div className="px-3 py-2 text-[10px] uppercase tracking-widest text-muted-foreground">Alerts</div>
                <ul className="space-y-1">
                  {notifications.map((n) => (
                    <li key={n.id} className="flex gap-3 rounded-lg p-3 hover:bg-white/5">
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full" style={{ background: tierColor(n.tier), boxShadow: `0 0 12px ${tierColor(n.tier)}` }} />
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-xs font-medium">{n.title}</div>
                        <div className="truncate text-[11px] text-muted-foreground">{n.detail}</div>
                      </div>
                      <div className="shrink-0 text-[10px] text-muted-foreground">{n.time}</div>
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <div className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5">
          <div className="grid h-7 w-7 place-items-center rounded-full text-xs font-semibold"
            style={{ background: "linear-gradient(135deg, var(--neon-blue), var(--neon-violet))" }}>
            AS
          </div>
          <div className="hidden text-left leading-tight md:block">
            <div className="text-xs font-medium">Ananya S.</div>
            <div className="text-[10px] text-muted-foreground">Senior Analyst</div>
          </div>
        </div>
      </div>
    </header>
  );
}
