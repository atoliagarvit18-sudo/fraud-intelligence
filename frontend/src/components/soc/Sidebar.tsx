import { Link, useRouterState } from "@tanstack/react-router";
import { LayoutDashboard, Radar, ClipboardList, AudioLines, FileText, ScanEye, Network, Sparkles, Settings, Shield, ChevronLeft } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/analysis", label: "New Analysis", icon: Radar },
  { to: "/cases", label: "Case History", icon: ClipboardList },
  { to: "/agent/speech", label: "Speech Agent", icon: AudioLines },
  { to: "/agent/text", label: "Text Agent", icon: FileText },
  { to: "/agent/visual", label: "Visual Agent", icon: ScanEye },
  { to: "/agent/network", label: "Network Agent", icon: Network },
  { to: "/recommendations", label: "Recommendations", icon: Sparkles },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const path = useRouterState({ select: (s) => s.location.pathname });

  return (
    <aside
      className={cn(
        "sticky top-0 hidden h-screen shrink-0 flex-col border-r border-white/10 bg-black/30 backdrop-blur-xl md:flex",
        collapsed ? "w-[72px]" : "w-[248px]",
        "transition-[width] duration-300",
      )}
    >
      <Link to="/" className="flex items-center gap-3 px-4 py-5">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-white/10"
          style={{ background: "linear-gradient(135deg, var(--neon-blue), var(--neon-violet))" }}>
          <Shield size={18} className="text-white" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold" style={{ fontFamily: "var(--font-display)" }}>Fraud Intel</div>
            <div className="truncate text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Platform</div>
          </div>
        )}
      </Link>

      <nav className="mt-2 flex-1 space-y-1 px-2">
        {nav.map(({ to, label, icon: Icon }) => {
          const active = path === to || (to !== "/dashboard" && path.startsWith(to));
          return (
            <Link
              key={to}
              to={to}
              className={cn(
                "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition",
                active
                  ? "bg-white/10 text-foreground"
                  : "text-muted-foreground hover:bg-white/5 hover:text-foreground",
              )}
            >
              {active && (
                <span className="absolute inset-y-1 left-0 w-0.5 rounded-full" style={{ background: "var(--neon-cyan)", boxShadow: "0 0 12px var(--neon-cyan)" }} />
              )}
              <Icon size={18} className="shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
            </Link>
          );
        })}
      </nav>

      <button
        onClick={() => setCollapsed((c) => !c)}
        className="m-3 flex items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-muted-foreground hover:bg-white/10"
      >
        <ChevronLeft size={14} className={cn("transition", collapsed && "rotate-180")} />
        {!collapsed && <span>Collapse</span>}
      </button>
    </aside>
  );
}

export function MobileNav() {
  const path = useRouterState({ select: (s) => s.location.pathname });
  const items = [
    { to: "/dashboard", label: "Home", icon: LayoutDashboard },
    { to: "/analysis", label: "Scan", icon: Radar },
    { to: "/cases", label: "Cases", icon: ClipboardList },
    { to: "/recommendations", label: "Actions", icon: Sparkles },
    { to: "/settings", label: "More", icon: Settings },
  ] as const;
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 flex items-center justify-around border-t border-white/10 bg-black/60 backdrop-blur-xl md:hidden">
      {items.map(({ to, label, icon: Icon }) => {
        const active = path === to || (to !== "/dashboard" && path.startsWith(to));
        return (
          <Link key={to} to={to} className={cn("flex flex-1 flex-col items-center gap-1 py-2 text-[10px]", active ? "text-foreground" : "text-muted-foreground")}>
            <Icon size={18} />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
