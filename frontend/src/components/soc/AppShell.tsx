import type { ReactNode } from "react";
import { MobileNav, Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen w-full">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 px-4 pb-24 pt-6 md:px-8 md:pb-10">{children}</main>
        <MobileNav />
      </div>
    </div>
  );
}
