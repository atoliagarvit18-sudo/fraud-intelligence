import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";
import { Toaster } from "sonner";

import appCss from "../styles.css?url";
import { reportLovableError } from "../lib/lovable-error-reporting";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <div className="text-mono text-7xl font-semibold neon-text" style={{ color: "var(--neon-cyan)" }}>404</div>
        <h1 className="mt-4 text-xl font-semibold">Signal lost</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          The route you're looking for isn't in our threat graph.
        </p>
        <Link
          to="/"
          className="mt-6 inline-flex items-center justify-center rounded-lg border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium hover:bg-white/10"
        >
          Return to base
        </Link>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-xl text-center">
        <h1 className="text-xl font-semibold text-red-400">Something went sideways</h1>
        <p className="mt-2 text-sm text-muted-foreground">Retry, or head back to the dashboard.</p>
        <div className="mt-4 rounded-lg border border-red-500/20 bg-black/60 p-4 text-left font-mono text-xs text-red-300 max-h-48 overflow-y-auto">
          <div className="font-bold text-red-400">{error.message || String(error)}</div>
          {error.stack && <pre className="mt-2 text-[10px] text-muted-foreground whitespace-pre-wrap">{error.stack}</pre>}
        </div>
        <div className="mt-6 flex justify-center gap-2">
          <button
            onClick={() => { router.invalidate(); reset(); }}
            className="rounded-lg border border-white/15 bg-white/5 px-4 py-2 text-sm hover:bg-white/10"
          >Try again</button>
          <a href="/" className="rounded-lg border border-white/15 px-4 py-2 text-sm hover:bg-white/10">Home</a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Fraud Intelligence Platform — Multi-Agent AI Fraud Detection" },
      { name: "description", content: "AI-powered SOC dashboard for detecting Digital Arrest scams, phishing, financial fraud and counterfeit documents using multi-agent intelligence." },
      { name: "author", content: "Fraud Intelligence Platform" },
      { property: "og:title", content: "Fraud Intelligence Platform" },
      { property: "og:description", content: "Multi-Agent AI System for Digital Fraud Detection." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" },
      { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head><HeadContent /></head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  return (
    <QueryClientProvider client={queryClient}>
      <Outlet />
      <Toaster theme="dark" position="top-right" toastOptions={{ style: { background: "rgba(20,25,40,0.9)", border: "1px solid rgba(255,255,255,0.1)", color: "white", backdropFilter: "blur(12px)" } }} />
    </QueryClientProvider>
  );
}
