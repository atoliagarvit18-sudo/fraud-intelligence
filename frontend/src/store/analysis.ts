import { create } from "zustand";
import { cases, type CaseData } from "@/mocks/cases";

interface AnalysisState {
  activeCase: CaseData;
  history: CaseData[];
  isLoading: boolean;
  loadingSessionId: string | null;
  error: string | null;
  setActiveCase: (c: CaseData) => void;
  selectSample: (id?: string) => void;
  /** Upload evidence files → call API → update activeCase */
  analyzeEvidence: (payload: {
    audio?: File | null;
    image?: File | null;
    text?: string;
    phone?: string;
    url?: string;
    onLog?: (agent: string, msg: string) => void;
  }) => Promise<CaseData | null>;
  /** Load the live sample case from /api/v1/cases/sample (Agent 2 MongoDB) */
  loadSampleCase: () => Promise<CaseData | null>;
}

export const useAnalysis = create<AnalysisState>((set, get) => ({
  activeCase: cases[0],
  history: cases,
  isLoading: false,
  loadingSessionId: null,
  error: null,

  setActiveCase: (c) => set({ activeCase: c }),

  selectSample: (id) =>
    set((s) => ({ activeCase: s.history.find((c) => c.caseId === id) ?? s.history[0] })),

  analyzeEvidence: async ({ audio, image, text, phone, url, onLog }) => {
    set({ isLoading: true, error: null });

    const sessionId = crypto.randomUUID();
    set({ loadingSessionId: sessionId });

    try {
      // Start SSE stream for live logs BEFORE posting the form
      let sseController: AbortController | null = null;
      if (onLog) {
        sseController = new AbortController();
        _streamLogs(sessionId, onLog, sseController.signal);
      }

      // POST evidence to /api/v1/analyze
      const form = new FormData();
      form.append("session_id", sessionId);
      if (audio) form.append("audio", audio);
      if (image) form.append("image", image);
      if (text)  form.append("text", text);
      if (phone) form.append("phone", phone);
      if (url)   form.append("url", url);

      const res = await fetch("/api/v1/analyze", { method: "POST", body: form });
      const data = await res.json();

      sseController?.abort();

      if (!data.success) throw new Error(data.error ?? "API returned failure");

      const newCase: CaseData = data.case as CaseData;
      set((s) => ({
        activeCase: newCase,
        history: [newCase, ...s.history.filter((c) => c.caseId !== newCase.caseId)],
        isLoading: false,
        loadingSessionId: null,
      }));
      return newCase;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ isLoading: false, error: msg, loadingSessionId: null });
      return null;
    }
  },

  loadSampleCase: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch("/api/v1/cases/sample");
      const data = await res.json();
      if (!data.success) throw new Error(data.error ?? "API returned failure");

      const sample: CaseData = data.case as CaseData;
      set((s) => ({
        activeCase: sample,
        history: [sample, ...s.history.filter((c) => c.caseId !== sample.caseId)],
        isLoading: false,
      }));
      return sample;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ isLoading: false, error: msg });
      return null;
    }
  },
}));

/** Subscribe to SSE /api/v1/analyze/stream/:sessionId and fire onLog for each line. */
function _streamLogs(
  sessionId: string,
  onLog: (agent: string, msg: string) => void,
  signal: AbortSignal,
) {
  const es = new EventSource(`/api/v1/analyze/stream/${sessionId}`);
  signal.addEventListener("abort", () => es.close());

  es.onmessage = (e) => {
    try {
      const d = JSON.parse(e.data) as { agent: string; msg: string };
      if (d.msg === "__DONE__") { es.close(); return; }
      onLog(d.agent, d.msg);
    } catch {
      /* ignore malformed */
    }
  };
  es.onerror = () => es.close();
}
