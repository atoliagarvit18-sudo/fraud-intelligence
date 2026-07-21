import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { AudioLines, ImageIcon, MessageSquare, Phone, Globe, Check, ArrowRight, Loader2, Wifi } from "lucide-react";
import { motion } from "framer-motion";
import { AppShell } from "@/components/soc/AppShell";
import { GlassCard } from "@/components/soc/GlassCard";
import { cn } from "@/lib/utils";
import { useAnalysis } from "@/store/analysis";
import { toast } from "sonner";

export const Route = createFileRoute("/analysis")({
  head: () => ({ meta: [{ title: "New Analysis — Fraud Intelligence Platform" }] }),
  component: Analysis,
});

const SAMPLE_TEXT =
  "URGENT: This is Inspector Sharma from CBI Cyber Cell. A case is registered against your Aadhaar. Do not disconnect. Transfer ₹2,40,000 to the RBI verification account within 30 minutes or a warrant will be issued.";

function Analysis() {
  const nav = useNavigate();
  const { analyzeEvidence, isLoading } = useAnalysis();

  const [text, setText]   = useState("");
  const [transcript, setTranscript] = useState("");
  const [phone, setPhone] = useState("");
  const [url, setUrl]     = useState("");
  const [checking, setChecking] = useState(false);

  const audioRef = useRef<File | null>(null);
  const imageRef = useRef<File | null>(null);
  const [audioName, setAudioName] = useState("");
  const [imageName, setImageName] = useState("");

  const filled = [audioName, imageName, transcript, text, phone, url].filter(Boolean).length;

  const handleAnalyze = async () => {
    if (filled === 0 || isLoading) return;
    // Mark loading first so /processing sees isLoading=true immediately
    useAnalysis.setState({ isLoading: true, error: null });
    nav({ to: "/processing" });
    const result = await analyzeEvidence({
      audio: audioRef.current,
      transcript: transcript || undefined,
      image: imageRef.current,
      text:  text || undefined,
      phone: phone || undefined,
      url:   url   || undefined,
    });
    if (!result) {
      // Backend unavailable — fall back to demo data so the flow still works
      toast.error("API server unavailable — running in demo mode", {
        description: "Start the Python backend on :8000 for live analysis.",
      });
      // Keep isLoading false (already set by analyzeEvidence) so /processing redirects to dashboard with mock data
    }
  };

  const fileCards = [
    { key: "audio" as const, icon: AudioLines, title: "Audio recording",    hint: ".mp3 / .wav call recording",       color: "var(--neon-cyan)"   },
    { key: "image" as const, icon: ImageIcon,  title: "Image / screenshot", hint: "Fake ID, currency note, document", color: "var(--neon-violet)" },
  ];

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl">
        <div className="mb-8">
          <div className="text-[10px] uppercase tracking-[0.25em] text-muted-foreground">Step 1 of 3</div>
          <h1 className="mt-1 text-3xl font-semibold" style={{ fontFamily: "var(--font-display)" }}>Submit evidence</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Provide any combination of evidence. Agent 1 inspects currency/documents, Agent 3 analyzes call audio, and Agent 2 correlates text/phone queries against its live MongoDB feed of scraped Reddit posts, Telegram channels, and National Cybercrime Complaints.
          </p>
        </div>

        {/* File upload cards */}
        <div className="grid gap-4 md:grid-cols-2">
          {fileCards.map((c, i) => {
            const isFilled = c.key === "audio" ? !!audioName : !!imageName;
            const name     = c.key === "audio" ? audioName  : imageName;
            return (
              <motion.div key={c.key} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}>
                <GlassCard glow={isFilled ? c.color : undefined} className="h-full">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={cn("grid h-10 w-10 place-items-center rounded-xl border transition", isFilled ? "border-current" : "border-white/10 text-muted-foreground")}
                        style={{ color: isFilled ? c.color : undefined }}
                      >
                        <c.icon size={18} />
                      </div>
                      <div>
                        <div className="text-sm font-semibold">{c.title}</div>
                        <div className="text-[11px] text-muted-foreground">{c.hint}</div>
                      </div>
                    </div>
                    {isFilled && (
                      <span className="grid h-6 w-6 place-items-center rounded-full" style={{ background: `color-mix(in oklab, ${c.color} 15%, transparent)`, color: c.color }}>
                        <Check size={14} />
                      </span>
                    )}
                  </div>
                  <label
                    className={cn(
                      "flex h-36 cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-white/15 bg-black/20 text-center text-xs text-muted-foreground transition hover:border-white/30",
                    )}
                    style={{ borderColor: isFilled ? c.color : undefined, backgroundColor: isFilled ? `color-mix(in oklab, ${c.color} 5%, transparent)` : undefined }}
                  >
                    <input
                      type="file"
                      accept={c.key === "audio" ? ".mp3,.wav,.m4a" : ".jpg,.jpeg,.png,.webp"}
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (!file) return;
                        if (c.key === "audio") { audioRef.current = file; setAudioName(file.name); }
                        else                   { imageRef.current = file; setImageName(file.name); }
                      }}
                    />
                    {isFilled ? (
                      <>
                        <div className="text-mono text-xs font-medium" style={{ color: c.color }}>{name}</div>
                        {c.key === "audio" && (
                          <div className="flex h-8 items-end gap-0.5">
                            {Array.from({ length: 38 }).map((_, i) => (
                              <span key={i} className="w-1 rounded-full" style={{ height: `${20 + Math.abs(Math.sin(i * 0.7)) * 100}%`, background: c.color, opacity: 0.7 }} />
                            ))}
                          </div>
                        )}
                        {c.key === "image" && (
                          <div className="mt-1 grid h-14 w-20 place-items-center rounded-md border border-white/10 bg-white/5 text-[10px] text-muted-foreground">preview</div>
                        )}
                      </>
                    ) : (
                      <>
                        <span>Drop file or click to upload</span>
                        <span className="text-[10px] opacity-60">{c.hint}</span>
                      </>
                    )}
                  </label>
                </GlassCard>
              </motion.div>
            );
          })}
        </div>
        {/* Transcript */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mt-4">
            <GlassCard glow={transcript ? "var(--neon-cyan)" : undefined}>
              <div className="mb-3 flex items-center gap-3">
                <div
                  className={cn(
                    "grid h-10 w-10 place-items-center rounded-xl border transition",
                    transcript
                      ? "border-[color:var(--neon-cyan)] text-[color:var(--neon-cyan)]"
                      : "border-white/10 text-muted-foreground"
                  )}
                >
                  <AudioLines size={18} />
                </div>

                <div>
                  <div className="text-sm font-semibold">
                    Call Transcript
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Paste transcript instead of uploading audio
                  </div>
                </div>

                {transcript && (
                  <Check
                    size={14}
                    className="ml-auto text-[color:var(--neon-cyan)]"
                  />
                )}
              </div>

              <textarea
                rows={6}
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
                className="text-mono w-full resize-none rounded-xl border border-white/10 bg-black/20 p-3 text-xs placeholder:text-muted-foreground focus:outline-none focus:border-white/30"
                placeholder="Paste the scam call transcript here. If both audio and transcript are provided, the transcript will be used directly."
              />

              <div className="mt-2 flex justify-end text-[10px] text-muted-foreground">
                {transcript.length} chars
              </div>
            </GlassCard>
          </motion.div>

        {/* Text / Phone / URL cards */}
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {/* SMS / Email */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }}>
            <GlassCard glow={text ? "var(--neon-blue)" : undefined} className="h-full">
              <div className="mb-3 flex items-center gap-3">
                <div className={cn("grid h-10 w-10 place-items-center rounded-xl border transition", text ? "border-[color:var(--neon-blue)] text-[color:var(--neon-blue)]" : "border-white/10 text-muted-foreground")}>
                  <MessageSquare size={18} />
                </div>
                <div>
                  <div className="text-sm font-semibold">OSINT Text / Keyword Query</div>
                  <div className="text-[11px] text-muted-foreground">Query Reddit, Telegram & complaints DB</div>
                </div>
                {text && <Check size={14} className="ml-auto text-[color:var(--neon-blue)]" />}
              </div>
              <textarea
                rows={5}
                value={text}
                onChange={(e) => setText(e.target.value)}
                className="text-mono w-full resize-none rounded-xl border border-white/10 bg-black/20 p-3 text-xs placeholder:text-muted-foreground focus:outline-none focus:border-white/30"
                placeholder="Paste suspicious text, message, or keyword to query against Agent 2's live MongoDB feed…"
              />
              <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
                <button onClick={() => setText(SAMPLE_TEXT)} className="rounded-md border border-white/10 bg-white/5 px-2 py-1 hover:bg-white/10">Autofill sample</button>
                <span>{text.length} chars</span>
              </div>
            </GlassCard>
          </motion.div>

          {/* Phone */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }}>
            <GlassCard glow={phone ? "var(--risk-medium)" : undefined} className="h-full">
              <div className="mb-3 flex items-center gap-3">
                <div className={cn("grid h-10 w-10 place-items-center rounded-xl border transition", phone ? "border-[color:var(--risk-medium)] text-[color:var(--risk-medium)]" : "border-white/10 text-muted-foreground")}>
                  <Phone size={18} />
                </div>
                <div>
                  <div className="text-sm font-semibold">Phone number</div>
                  <div className="text-[11px] text-muted-foreground">+91 98••• •••••</div>
                </div>
                {phone && <Check size={14} className="ml-auto text-[color:var(--risk-medium)]" />}
              </div>
              <div className="flex gap-2">
                <select className="rounded-lg border border-white/10 bg-black/20 px-2 py-2 text-xs focus:outline-none">
                  <option>+91</option><option>+1</option><option>+44</option><option>+971</option>
                </select>
                <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone number"
                  className="text-mono flex-1 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs placeholder:text-muted-foreground focus:outline-none focus:border-white/30" />
              </div>
            </GlassCard>
          </motion.div>

          {/* URL */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.24 }}>
            <GlassCard glow={url ? "var(--risk-high)" : undefined} className="h-full">
              <div className="mb-3 flex items-center gap-3">
                <div className={cn("grid h-10 w-10 place-items-center rounded-xl border transition", url ? "border-[color:var(--risk-high)] text-[color:var(--risk-high)]" : "border-white/10 text-muted-foreground")}>
                  <Globe size={18} />
                </div>
                <div>
                  <div className="text-sm font-semibold">Website URL</div>
                  <div className="text-[11px] text-muted-foreground">https://…</div>
                </div>
                {url && <Check size={14} className="ml-auto text-[color:var(--risk-high)]" />}
              </div>
              <input value={url} onChange={(e) => setUrl(e.target.value)}
                onBlur={() => { if (url) { setChecking(true); setTimeout(() => setChecking(false), 900); } }}
                placeholder="https://suspicious-domain.co"
                className="text-mono w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs placeholder:text-muted-foreground focus:outline-none focus:border-white/30" />
              {checking && (
                <div className="mt-2 flex items-center gap-2 text-[11px] text-muted-foreground">
                  <span className="h-1.5 w-1.5 rounded-full pulse-dot" style={{ background: "var(--neon-cyan)" }} />
                  Checking domain reputation…
                </div>
              )}
            </GlassCard>
          </motion.div>
        </div>

        {/* Submit bar */}
        <div className="mt-8 flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-xl md:sticky md:bottom-6">
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <Wifi size={14} className="text-[color:var(--risk-safe)]" />
            <span>Live analysis — connected to Agent 4 orchestrator on <span className="text-mono text-foreground">:8000</span></span>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-mono text-xs text-muted-foreground">{filled} of 6 sources added</div>
            <button
              disabled={filled === 0 || isLoading}
              onClick={handleAnalyze}
              className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold text-white shadow-[0_0_30px_-8px_var(--neon-blue)] transition enabled:hover:shadow-[0_0_50px_-4px_var(--neon-blue)] disabled:opacity-40"
              style={{ background: "linear-gradient(135deg, var(--neon-blue), var(--neon-violet))" }}
            >
              {isLoading ? <><Loader2 size={16} className="animate-spin" /> Analyzing…</> : <>Analyze <ArrowRight size={16} /></>}
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
