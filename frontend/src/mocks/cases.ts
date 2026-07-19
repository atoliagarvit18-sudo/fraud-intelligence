export type RiskTier = "critical" | "high" | "medium" | "low" | "safe";

export type AgentKey = "speech" | "text" | "visual" | "network";

export interface AgentResult {
  score: number;
  confidence: number;
  status: "idle" | "scanning" | "complete";
  summary: string;
}

export interface CaseData {
  caseId: string;
  timestamp: string;
  overallRisk: number;
  confidence: number;
  verdict: string;
  tier: RiskTier;
  sources: ("audio" | "image" | "text" | "phone" | "url")[];
  agents: Record<AgentKey, AgentResult>;
  explainability: { signal: string; weight: number; icon?: string }[];
  recommendations: { action: string; urgency: "critical" | "warning" | "info" }[];
  timeline: { step: string; timestamp: string }[];
  details: {
    speech: {
      transcript: { speaker: string; line: string }[];
      keywords: { term: string; severity: RiskTier }[];
      similarity: number;
      syntheticVoiceProb: number;
      reasoning: string;
    };
    text: {
      entities: { label: string; value: string }[];
      threatLevel: RiskTier;
      keywords: string[];
      category: string;
      reasoning: string;
    };
    visual: {
      ocr: string;
      forgery: { verdict: string; confidence: number };
      fakeId: { verdict: string; confidence: number; regions: { x: number; y: number; w: number; h: number }[] };
    };
    network: {
      phone: string;
      bank: string;
      email: string;
      ip: string;
      flags: Record<string, boolean>;
      cluster: { id: string; reports: number; description: string };
    };
  };
}

export const cases: CaseData[] = [
  {
    caseId: "FIP-2026-00842",
    timestamp: "2026-07-17T10:32:00Z",
    overallRisk: 94,
    confidence: 97,
    verdict: "Digital Arrest Scam",
    tier: "critical",
    sources: ["audio", "image", "text", "phone", "url"],
    agents: {
      speech: { score: 96, confidence: 95, status: "complete", summary: "Impersonation of law enforcement with coercive tone and synthetic voice markers." },
      text: { score: 89, confidence: 92, status: "complete", summary: "Threat-based persuasion referencing arrest warrants and time-bound payments." },
      visual: { score: 74, confidence: 81, status: "complete", summary: "Forged government ID with inconsistent MRZ checksum and misaligned photo region." },
      network: { score: 91, confidence: 94, status: "complete", summary: "Phone and bank account linked to known scam cluster SC-1187." },
    },
    explainability: [
      { signal: "Authority language detected", weight: 0.22 },
      { signal: "Threat-based persuasion", weight: 0.19 },
      { signal: "Forged identity document", weight: 0.17 },
      { signal: "Known scam phone network", weight: 0.16 },
      { signal: "High semantic similarity to prior scams", weight: 0.14 },
      { signal: "Urgent financial request", weight: 0.12 },
    ],
    recommendations: [
      { action: "Do not transfer money under any circumstances", urgency: "critical" },
      { action: "Block the caller's phone number immediately", urgency: "critical" },
      { action: "Report the incident to the National Cyber Crime Portal", urgency: "warning" },
      { action: "Preserve all messages, screenshots and call logs as evidence", urgency: "warning" },
      { action: "Ignore any future contact from associated numbers", urgency: "info" },
    ],
    timeline: [
      { step: "Evidence Uploaded", timestamp: "10:32:00" },
      { step: "Speech Analysis", timestamp: "10:32:03" },
      { step: "Text Analysis", timestamp: "10:32:05" },
      { step: "Visual Analysis", timestamp: "10:32:07" },
      { step: "Network Analysis", timestamp: "10:32:09" },
      { step: "Fusion Engine", timestamp: "10:32:11" },
      { step: "Final Verdict", timestamp: "10:32:12" },
    ],
    details: {
      speech: {
        transcript: [
          { speaker: "Caller", line: "This is Inspector Sharma from CBI Cyber Cell. A case has been registered against your Aadhaar." },
          { speaker: "Victim", line: "What? I haven't done anything." },
          { speaker: "Caller", line: "Do not disconnect. You are under digital arrest. Transfer the verification amount now." },
        ],
        keywords: [
          { term: "digital arrest", severity: "critical" },
          { term: "CBI", severity: "high" },
          { term: "Aadhaar", severity: "medium" },
          { term: "transfer", severity: "high" },
          { term: "verification amount", severity: "critical" },
        ],
        similarity: 0.93,
        syntheticVoiceProb: 0.71,
        reasoning: "Prosodic flatness and phoneme boundary artifacts indicate partial TTS synthesis. Script closely matches 214 prior 'Digital Arrest' recordings.",
      },
      text: {
        entities: [
          { label: "Authority", value: "CBI Cyber Cell" },
          { label: "ID", value: "Aadhaar" },
          { label: "Amount", value: "₹ 2,40,000" },
          { label: "Channel", value: "IMPS Transfer" },
        ],
        threatLevel: "critical",
        keywords: ["arrest warrant", "verification", "immediate", "do not disconnect", "RBI account"],
        category: "Digital Arrest Scam",
        reasoning: "Coercive authority framing combined with urgent financial ask and forbidding disconnection — signature pattern of Digital Arrest scams.",
      },
      visual: {
        ocr: "GOVERNMENT OF INDIA\nCENTRAL BUREAU OF INVESTIGATION\nOFFICER ID: CBI/2024/00871\nNAME: R. SHARMA",
        forgery: { verdict: "Likely forged", confidence: 0.82 },
        fakeId: {
          verdict: "Fake ID detected",
          confidence: 0.87,
          regions: [
            { x: 8, y: 12, w: 28, h: 34 },
            { x: 55, y: 60, w: 38, h: 14 },
          ],
        },
      },
      network: {
        phone: "+91 98••• ••432",
        bank: "HDFC •••• 8821",
        email: "cbi.cyber.verify@proton.me",
        ip: "185.216.71.44",
        flags: { phone: true, bank: true, email: true, ip: true },
        cluster: { id: "SC-1187", reports: 342, description: "Digital Arrest scam cluster active across North India since Q1 2026." },
      },
    },
  },
  {
    caseId: "FIP-2026-00701",
    timestamp: "2026-07-15T14:11:00Z",
    overallRisk: 62,
    confidence: 88,
    verdict: "Phishing Attempt",
    tier: "medium",
    sources: ["text", "url"],
    agents: {
      speech: { score: 0, confidence: 0, status: "complete", summary: "No audio evidence submitted." },
      text: { score: 71, confidence: 90, status: "complete", summary: "Credential-harvesting language with spoofed bank branding." },
      visual: { score: 44, confidence: 76, status: "complete", summary: "No document submitted; screenshot shows lookalike bank UI." },
      network: { score: 68, confidence: 89, status: "complete", summary: "Domain registered 6 days ago on suspicious registrar." },
    },
    explainability: [
      { signal: "Lookalike domain detected", weight: 0.28 },
      { signal: "Credential harvesting language", weight: 0.24 },
      { signal: "Newly registered domain", weight: 0.20 },
      { signal: "Spoofed brand imagery", weight: 0.16 },
      { signal: "Suspicious redirect chain", weight: 0.12 },
    ],
    recommendations: [
      { action: "Do not click the link or enter credentials", urgency: "critical" },
      { action: "Report the URL to your bank's fraud desk", urgency: "warning" },
      { action: "Enable two-factor authentication on your bank account", urgency: "info" },
    ],
    timeline: [
      { step: "Evidence Uploaded", timestamp: "14:11:00" },
      { step: "Text Analysis", timestamp: "14:11:02" },
      { step: "Network Analysis", timestamp: "14:11:05" },
      { step: "Fusion Engine", timestamp: "14:11:07" },
      { step: "Final Verdict", timestamp: "14:11:08" },
    ],
    details: {
      speech: { transcript: [], keywords: [], similarity: 0, syntheticVoiceProb: 0, reasoning: "No audio submitted." },
      text: {
        entities: [{ label: "Brand", value: "HDFC Bank" }, { label: "Domain", value: "hdfc-secure-login.co" }],
        threatLevel: "high",
        keywords: ["verify account", "suspended", "click here", "urgent"],
        category: "Phishing",
        reasoning: "Urgency + credential capture form on a lookalike domain.",
      },
      visual: {
        ocr: "HDFC BANK — Account Suspended\nVerify identity to restore access.",
        forgery: { verdict: "Suspected clone UI", confidence: 0.66 },
        fakeId: { verdict: "N/A", confidence: 0, regions: [] },
      },
      network: {
        phone: "—",
        bank: "—",
        email: "no-reply@hdfc-secure-login.co",
        ip: "104.21.72.9",
        flags: { email: true, ip: true, phone: false, bank: false },
        cluster: { id: "SC-0942", reports: 87, description: "Phishing cluster targeting Indian retail banking users." },
      },
    },
  },
  {
    caseId: "FIP-2026-00655",
    timestamp: "2026-07-12T09:04:00Z",
    overallRisk: 12,
    confidence: 91,
    verdict: "Legitimate Communication",
    tier: "safe",
    sources: ["text", "phone"],
    agents: {
      speech: { score: 8, confidence: 88, status: "complete", summary: "Natural speech, no coercion markers." },
      text: { score: 14, confidence: 92, status: "complete", summary: "Transactional message consistent with routine service notification." },
      visual: { score: 0, confidence: 0, status: "complete", summary: "No image submitted." },
      network: { score: 6, confidence: 95, status: "complete", summary: "Number belongs to verified enterprise sender." },
    },
    explainability: [
      { signal: "Verified sender ID", weight: 0.34 },
      { signal: "Consistent transactional tone", weight: 0.26 },
      { signal: "No urgency markers", weight: 0.22 },
      { signal: "Historical safe sender", weight: 0.18 },
    ],
    recommendations: [
      { action: "No action required — message appears legitimate", urgency: "info" },
      { action: "Continue to verify unknown senders before acting", urgency: "info" },
    ],
    timeline: [
      { step: "Evidence Uploaded", timestamp: "09:04:00" },
      { step: "Text Analysis", timestamp: "09:04:02" },
      { step: "Network Analysis", timestamp: "09:04:04" },
      { step: "Fusion Engine", timestamp: "09:04:05" },
      { step: "Final Verdict", timestamp: "09:04:06" },
    ],
    details: {
      speech: { transcript: [], keywords: [], similarity: 0, syntheticVoiceProb: 0, reasoning: "No audio submitted." },
      text: {
        entities: [{ label: "Sender", value: "AX-HDFCBK" }, { label: "Type", value: "Transactional" }],
        threatLevel: "safe",
        keywords: ["credited", "balance", "reference"],
        category: "Legitimate",
        reasoning: "Standard transactional SMS format from verified DLT-registered sender.",
      },
      visual: {
        ocr: "",
        forgery: { verdict: "N/A", confidence: 0 },
        fakeId: { verdict: "N/A", confidence: 0, regions: [] },
      },
      network: {
        phone: "AX-HDFCBK",
        bank: "—",
        email: "—",
        ip: "—",
        flags: {},
        cluster: { id: "—", reports: 0, description: "No known malicious associations." },
      },
    },
  },
];

export const notifications = [
  { id: 1, title: "New high-risk case detected", detail: "FIP-2026-00842 — Digital Arrest Scam", time: "2m ago", tier: "critical" as RiskTier },
  { id: 2, title: "Scam cluster SC-1187 expanded", detail: "12 new reports in the last hour", time: "18m ago", tier: "high" as RiskTier },
  { id: 3, title: "Weekly threat report ready", detail: "Download Q3 W2 intelligence brief", time: "3h ago", tier: "low" as RiskTier },
  { id: 4, title: "Model updated: speech-v4.2", detail: "Synthetic voice detection +6% recall", time: "1d ago", tier: "safe" as RiskTier },
];

export function tierFromScore(score: number): RiskTier {
  if (score >= 85) return "critical";
  if (score >= 65) return "high";
  if (score >= 40) return "medium";
  if (score >= 20) return "low";
  return "safe";
}

export function tierColor(tier: RiskTier) {
  return {
    critical: "var(--risk-critical)",
    high: "var(--risk-high)",
    medium: "var(--risk-medium)",
    low: "var(--risk-low)",
    safe: "var(--risk-safe)",
  }[tier];
}

export function tierLabel(tier: RiskTier) {
  return { critical: "CRITICAL", high: "HIGH RISK", medium: "MEDIUM", low: "LOW", safe: "SAFE" }[tier];
}
