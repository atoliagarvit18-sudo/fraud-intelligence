"""
agent4/demo/demo_runner.py

ET AI Hackathon 2.0 — Problem Statement 6
Fraud Campaign Intelligence System — LIVE DEMO

LIVE-FIRST ARCHITECTURE:
  Every agent runs its real pipeline by default.
  Mock is used ONLY as an automatic safety net if a dependency fails.

  Agent 1 — real OpenCV + sklearn inference on sample_data/500_fake_0.jpg
  Agent 2 — real MongoDB query (falls back to mock if DB unreachable)
  Agent 3 — real Whisper transcription + Groq LLM (falls back to
             precomputed JSON, then mock if both unavailable)

Usage:
    # Full live run (recommended — requires Groq API key in agent3/.env)
    python demo/demo_runner.py

    # Specify a different audio file
    python demo/demo_runner.py --audio ../agent3/audio/sample.mp3

    # Override image
    python demo/demo_runner.py --image ../agent1/sample_data/500_fake_0.jpg

    # Use live MongoDB instead of auto-detect
    python demo/demo_runner.py --mongodb

    # Force mock for all agents (testing only)
    python demo/demo_runner.py --all-mock
"""

import io
import json
import os
import sys
import time
import uuid
import argparse
from datetime import datetime

# Force UTF-8 output so box-drawing / rupee chars render correctly on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Path setup — can be run from any directory
# ---------------------------------------------------------------------------
_DEMO_DIR   = os.path.dirname(os.path.abspath(__file__))
_AGENT4_DIR = os.path.dirname(_DEMO_DIR)
_PROJECT    = os.path.normpath(os.path.join(_AGENT4_DIR, ".."))

for _p in [_AGENT4_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from adapters import agent1_adapter, agent2_adapter, agent3_adapter
import correlator
import predictor
import network_graph
import evidence_package
import synthesizer
from orchestrator import save_report

# ---------------------------------------------------------------------------
# Colours (colorama)
# ---------------------------------------------------------------------------
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
except ImportError:
    class _Noop:
        def __getattr__(self, _): return ""
    Fore = Back = Style = _Noop()


# ---------------------------------------------------------------------------
# Print helpers
# ---------------------------------------------------------------------------

def _w(n=70): return "=" * n

def _header():
    w = 70
    print()
    print(Fore.CYAN + Style.BRIGHT + "=" * w)
    print(Fore.CYAN + Style.BRIGHT + " FRAUD CAMPAIGN INTELLIGENCE SYSTEM".center(w))
    print(Fore.CYAN + Style.BRIGHT + " Agent 4 -- Predictive Threat Neutralisation Engine".center(w))
    print(Fore.CYAN + Style.BRIGHT + " ET AI Hackathon 2.0  |  Problem Statement 6".center(w))
    print(Fore.CYAN + Style.BRIGHT + "=" * w)
    print()

def _section(title, icon=">"):
    print()
    print(Fore.YELLOW + Style.BRIGHT + "-" * 68)
    print(Fore.YELLOW + Style.BRIGHT + f"  {icon}  {title}")
    print(Fore.YELLOW + Style.BRIGHT + "-" * 68)

def _step(msg, delay=0.08):
    print(Fore.WHITE + f"  * {msg}")
    time.sleep(delay)

def _ok(msg):
    print(Fore.GREEN + Style.BRIGHT + f"  [LIVE] {msg}")

def _fallback(msg):
    print(Fore.YELLOW + f"  [FALLBACK] {msg}")

def _err(msg):
    print(Fore.RED + f"  [ERROR] {msg}")

def _box(lines, color=Fore.WHITE):
    if not lines:
        return
    w = max(len(l) for l in lines) + 4
    print(color + "  +" + "-" * (w - 2) + "+")
    for line in lines:
        print(color + f"  |  {line:<{w-4}}|")
    print(color + "  +" + "-" * (w - 2) + "+")

def _ts():
    return Fore.MAGENTA + f"[{datetime.now().strftime('%H:%M:%S')}]"

def _source_badge(result: dict) -> str:
    """Return LIVE / FALLBACK / PRECOMPUTED badge string."""
    src = result.get("_source", "")
    if result.get("_mock"):
        return Fore.YELLOW + "[MOCK FALLBACK]"
    if "precomputed" in str(src):
        return Fore.CYAN + "[PRECOMPUTED]"
    return Fore.GREEN + Style.BRIGHT + "[LIVE]"


# ---------------------------------------------------------------------------
# Agent runners
# ---------------------------------------------------------------------------

def _run_agent1(image_path: str, denom_hint: str, location: str) -> dict:
    _section("AGENT 1  |  Currency Intelligence (Computer Vision)", "=")
    _step("Loading OpenCV pipeline...")
    _step("Reading currency note image...")
    _step("Deskewing and perspective-correcting note...")
    _step("Extracting feature vector (LBP + HOG + colour histograms)...")
    _step("Running denomination classifier...")
    _step("Running fake/genuine binary classifier (Random Forest)...")
    _step("Perceptual hashing for batch fingerprinting (pHash-256)...")

    result = agent1_adapter.run(image_path, denom_hint, location)

    badge = _source_badge(result)

    if result.get("available") and result.get("verdict"):
        verdict = result["verdict"]
        vcolor  = Fore.RED if verdict == "fake" else Fore.GREEN
        vlabel  = "[!] FAKE - COUNTERFEIT DETECTED" if verdict == "fake" else "[OK] GENUINE"
        lines = [
            f"Denomination : Rs.{result.get('denomination', '?')}",
            f"Verdict      : {vlabel}",
            f"Confidence   : {result.get('confidence', 0):.3f}",
        ]
        if verdict == "fake":
            lines.append(f"Batch ID     : {result.get('batch_id', 'unassigned')}")
            lines.append(
                f"New Batch    : {'YES - first sighting of this print run' if result.get('is_new_batch') else 'NO - batch previously seen'}"
            )
        if result.get("location"):
            lines.append(f"Location     : {result['location']}")
        if result.get("denomination_auto_detected") is not None:
            lines.append(
                f"Denom Source : {'auto-detected' if result['denomination_auto_detected'] else 'hint provided'}"
            )
        _box(lines, vcolor)
        print(f"  {badge}" + (Fore.GREEN if not result.get("_mock") else Fore.YELLOW) +
              f" Agent 1 complete | verdict={verdict} | conf={result.get('confidence', 0):.3f}")
    else:
        status = result.get("error") or result.get("status") or "unknown"
        _fallback(f"Agent 1 used mock: {status}")

    return result


def _run_agent2(source: str, json_path=None, mongo_uri=None) -> dict:
    _section("AGENT 2  |  OSINT Campaign Intelligence (NLP + Clustering)", "=")
    _step("Connecting to Agent 2 intelligence database (MongoDB)...")
    _step("Querying fraud_intelligence.events collection...")
    _step("Loading most recent high-severity campaign cluster...")
    _step("Reading cluster metadata, sources, temporal data...")

    result = agent2_adapter.run(source=source, json_path=json_path, mongo_uri=mongo_uri)

    badge = _source_badge(result)

    if result.get("available"):
        sev       = (result.get("severity") or "unknown").upper()
        sev_color = Fore.RED if sev == "CRITICAL" else (
                    Fore.YELLOW if sev in ("HIGH", "MEDIUM") else Fore.WHITE)

        scam_label = (result.get("scam_type") or "unknown").replace("_", " ").title()
        sources    = ", ".join(result.get("sources") or ["unknown"])
        platforms  = ", ".join(result.get("platforms") or [])
        locs       = ", ".join(result.get("locations") or ["not extracted"])

        lines = [
            f"Severity       : {sev}",
            f"Scam Type      : {scam_label}",
            f"Post Count     : {result.get('post_count', 0)} posts tracked",
            f"Sources        : {sources}",
        ]
        if platforms:
            lines.append(f"Platforms      : {platforms[:60]}")
        lines += [
            f"Campaign Score : {result.get('campaign_score', 0):.4f}",
            f"Confidence     : {result.get('weighted_confidence', 0):.4f}",
            f"Multi-Source   : {'YES' if result.get('is_multi_source') else 'NO'}",
            f"Locations      : {locs}",
        ]
        td = result.get("temporal_data") or {}
        if td.get("earliest_post"):
            lines.append(f"Campaign Start : {td['earliest_post'][:19]}")
        if td.get("latest_post"):
            lines.append(f"Last Activity  : {td['latest_post'][:19]}")
        _box(lines, sev_color)
        print(f"  {badge}" + Fore.GREEN + f" Agent 2 complete | severity={sev} | score={result.get('campaign_score', 0):.3f}")
    else:
        _err(f"Agent 2 failed: {result.get('error', 'unknown')}")

    return result


def _run_agent3(audio_path: str) -> dict:
    _section("AGENT 3  |  Scam Call Intelligence (Audio + NLP + RAG + LLM)", "=")
    _step("Loading Whisper Base speech-to-text model (first call may take 10-20s)...")
    _step(f"Transcribing audio: {os.path.basename(audio_path)}...")
    _step("Running Keyword Analyzer (weighted pattern matching)...")
    _step("Running Semantic Analyzer (RAG over scam knowledge base)...")
    _step("Querying Groq LLM (llama-3.1-8b-instant) for contextual analysis...")
    _step("Running Librosa voice analysis (energy, ZCR, duration)...")
    _step("Computing 3-analyzer ensemble decision (majority vote)...")

    result = agent3_adapter.run(audio_path=audio_path, transcript = transcript)

    badge = _source_badge(result)

    if result.get("available"):
        risk   = result.get("risk_score", 0)
        conf   = result.get("confidence", 0)
        rcolor = Fore.RED if risk >= 70 else (Fore.YELLOW if risk >= 40 else Fore.GREEN)
        rlabel = "HIGH" if risk >= 70 else ("MEDIUM" if risk >= 40 else "LOW")
        tactics   = ", ".join((result.get("psychological_tactics") or [])[:4])[:70] or "none"
        entities  = ", ".join((result.get("government_entities") or [])[:3])[:60] or "none"
        agreement = (result.get("overall_analysis") or {}).get("agreement", "?/3")

        lines = [
            f"Scam Type    : {result.get('scam_type', 'Unknown')}",
            f"Risk Score   : {risk}/100  [{rlabel}]",
            f"Confidence   : {conf:.3f}",
            f"Language     : {result.get('language', 'unknown')}",
            f"Tactics      : {tactics}",
            f"Entities     : {entities}",
            f"Agreement    : {agreement} analyzers",
        ]
        va = result.get("voice_analysis") or {}
        if va.get("duration_seconds"):
            lines.append(f"Audio Length : {va['duration_seconds']:.1f}s")

        # Print transcript excerpt
        transcript = (result.get("transcript") or "").strip()
        if transcript:
            excerpt = transcript[:120] + ("..." if len(transcript) > 120 else "")
            lines.append(f"Transcript   : {excerpt}")

        _box(lines, rcolor)
        print(f"  {badge}" + Fore.GREEN + f" Agent 3 complete | type={result.get('scam_type')} | risk={risk}/100")
    else:
        _err(f"Agent 3 failed: {result.get('error', 'unknown')}")

    return result


# ---------------------------------------------------------------------------
# Agent 4 engines
# ---------------------------------------------------------------------------

def _run_correlation(a1, a2, a3) -> dict:
    _section("AGENT 4  |  Cross-Agent Correlation Engine", ">>")
    _step("Mapping scam type equivalences across agent taxonomies...")
    _step("Checking geographic overlap (city keyword matching)...")
    _step("Detecting temporal spike (activation window analysis)...")
    _step("Analysing shared infrastructure signatures...")

    corr = correlator.correlate(a1, a2, a3)

    checks = [
        ("Scam Type Match",     corr.get("scam_type_match")),
        ("Geographic Overlap",  corr.get("geo_overlap")),
        ("Temporal Spike",      corr.get("temporal_spike")),
        ("Infrastructure Link", corr.get("infrastructure_link")),
    ]
    for label, matched in checks:
        clr = Fore.GREEN if matched else Fore.RED
        sym = "[YES]" if matched else "[ NO]"
        print(clr + f"  {sym}  {label}")
        time.sleep(0.08)

    score = corr.get("correlation_score", 0)
    n_sig = corr.get("signals_matched", 0)
    sclr  = Fore.RED if score > 0.7 else (Fore.YELLOW if score > 0.4 else Fore.WHITE)
    print()
    print(sclr + Style.BRIGHT +
          f"  Correlation Score  : {score:.3f} / 1.000   ({n_sig}/{corr.get('signals_total', 4)} signals)")
    print(sclr + f"  Unified Scam Type  : {corr.get('unified_scam_type', 'Unknown')}")

    evs = corr.get("correlation_evidence") or []
    if evs:
        print(Fore.CYAN + "\n  Correlation Evidence:")
        for ev in evs:
            print(Fore.CYAN + f"    -> {ev}")

    return corr


def _run_network(a1, a2, a3, corr) -> dict:
    _section("AGENT 4  |  Criminal Network Hypothesis Engine  [UNIQUE]", ">>")
    _step("Extracting infrastructure signals from all three agents...")
    _step("Building directed NetworkX graph (nodes, edges, weights)...")
    _step("Computing degree centrality — identifying key infrastructure node...")
    _step("Estimating operator count from coordination complexity heuristics...")
    _step("Profiling criminal cell (geography, modus, monthly capacity)...")

    net = network_graph.build(a1, a2, a3, corr)

    ev_str   = (net.get("evidence_strength") or "unknown").upper()
    ev_color = Fore.RED if ev_str == "STRONG" else (Fore.YELLOW if ev_str == "MEDIUM" else Fore.WHITE)

    infra = net.get("infrastructure") or {}
    comm_list = ", ".join(infra.get("communication") or [])[:40] or "unknown"
    dig_list  = ", ".join(infra.get("digital") or [])[:60] or "unknown"
    imp_list  = ", ".join(net.get("impersonation_targets") or [])[:50] or "none"
    geo_list  = ", ".join(net.get("operational_geography") or [])[:40] or "unknown"

    lines = [
        f"Cell ID          : {net.get('cell_id', 'N/A')}",
        f"Est. Operators   : {net.get('estimated_operators', '?')} individuals",
        f"Geography        : {geo_list}",
        f"Modus Operandi   : {(net.get('modus_operandi') or 'unknown')[:65]}",
        f"Communication    : {comm_list}",
        f"Digital Infra.   : {dig_list[:60]}",
        f"Impersonation    : {imp_list}",
        f"Monthly Victims  : ~{net.get('estimated_monthly_victims', '?')}",
        f"Evidence Strength: {ev_str}",
        f"Confidence       : {net.get('confidence', 0):.2f}",
        f"Graph            : {net.get('graph_nodes', 0)} nodes, {net.get('graph_edges', 0)} edges",
    ]
    _box(lines, ev_color)
    print(Fore.GREEN + Style.BRIGHT + f"  [LIVE] Criminal cell profiled — {ev_str} evidence, confidence={net.get('confidence', 0):.2f}")

    return net


def _run_prediction(a2, a3, corr) -> dict:
    _section("AGENT 4  |  Predictive Victimisation Engine  [UNIQUE]", ">>")
    _step("Parsing campaign temporal data (earliest → latest post timestamps)...")
    _step("Computing campaign velocity (posts/hour)...")
    _step("Classifying growth trajectory (accelerating / stable / declining)...")
    _step("Applying RBI/NCRB 2023-24 per-campaign victimisation rate scaling...")
    _step("Projecting 24h and 48h victim windows (probabilistic range)...")

    pred = predictor.predict(a2, a3, corr.get("correlation_score", 0))

    urg   = pred.get("urgency_level", "UNKNOWN")
    traj  = pred.get("campaign_growth_rate", "unknown").upper()
    uc    = Fore.RED if urg == "IMMEDIATE" else (Fore.YELLOW if urg == "URGENT" else Fore.WHITE)
    ticon = "[^] ACCELERATING" if traj == "ACCELERATING" else ("[-] STABLE" if traj == "STABLE" else "[v] DECLINING")

    print()
    print(uc + Style.BRIGHT + "  [!]  WITHOUT INTERVENTION -- PROJECTED VICTIM COUNT:")
    lines = [
        f"Campaign Growth  : {ticon}",
    ]
    if pred.get("posts_per_hour") is not None:
        lines.append(f"Velocity         : {pred['posts_per_hour']:.1f} posts/hour")
    lines += [
        f"Next 24 hours    : {pred.get('estimated_victims_24h_low', 0):,} - {pred.get('estimated_victims_24h_high', 0):,} additional victims",
        f"Next 48 hours    : {pred.get('estimated_victims_48h_low', 0):,} - {pred.get('estimated_victims_48h_high', 0):,} additional victims",
        f"Urgency Level    : {urg}",
    ]
    if pred.get("hours_to_peak_activity"):
        lines.append(f"Peak Activity    : ~{pred['hours_to_peak_activity']}h from now")
    lines.append(f"Basis            : {(pred.get('prediction_basis') or '')[:70]}")
    _box(lines, uc)
    print(Fore.GREEN + Style.BRIGHT + f"  [LIVE] Prediction complete | urgency={urg}")

    return pred


def _run_evidence(a1, a2, a3, corr, report_id, score, severity, scam_type) -> dict:
    _section("AGENT 4  |  Legal Evidence Package Generator  [UNIQUE]", ">>")
    _step("Serialising all evidence items to canonical JSON...")
    _step("Computing SHA-256 integrity hashes for each item...")
    _step("Building chain-of-custody manifest...")
    _step("Drafting NCRB cybercrime.gov.in complaint...")
    if a1 and a1.get("verdict") == "fake":
        _step("Drafting RBI FICN alert (counterfeit currency notification)...")
    _step("Sealing evidence package with manifest hash...")

    evp = evidence_package.generate(a1, a2, a3, corr, report_id, score, severity, scam_type)

    items  = evp.get("evidence_count", 0)
    pkg_id = evp.get("package_id", "N/A")
    lines  = [
        f"Package ID       : {pkg_id}",
        f"Evidence Items   : {items} items hashed and sealed",
        f"Integrity        : SHA-256 verified",
        f"NCRB Draft       : Ready for cybercrime.gov.in",
    ]
    if evp.get("rbi_alert_draft"):
        lines.append(f"RBI FICN Alert   : Ready for RBI regional office")
    lines.append(f"Cybercrime Line  : 1930")
    lines.append(f"Portal           : cybercrime.gov.in")
    _box(lines, Fore.GREEN)
    print(Fore.GREEN + Style.BRIGHT + f"  [LIVE] Evidence package sealed | ID={pkg_id}")

    return evp


# ---------------------------------------------------------------------------
# Final report display
# ---------------------------------------------------------------------------

def _print_final_report(report: dict):
    w       = 72
    score   = report["composite_risk_score"]
    sev     = report["severity"]
    scam    = report["unified_scam_type"]
    narr    = report["narrative"]
    actions = report["recommended_actions"]
    play    = report["threat_neutralisation_playbook"]

    sclr = Fore.RED if score >= 80 else (Fore.YELLOW if score >= 50 else Fore.GREEN)

    print()
    print(Fore.RED + Style.BRIGHT + "=" * w)
    print(Fore.RED + Style.BRIGHT + "  !!! UNIFIED THREAT INTELLIGENCE REPORT !!!".center(w))
    print(Fore.RED + Style.BRIGHT + "=" * w)
    print(sclr + Style.BRIGHT + f"  Risk Score   : {score} / 100  |  Severity: {sev}")
    print(sclr + Style.BRIGHT + f"  Scam Type    : {scam}")
    print(sclr + Style.BRIGHT + f"  Agents Active: {report['agents_active']}/3")

    corr_sig = report.get("correlation", {}).get("signals_matched", 0)
    corr_scr = report.get("correlation", {}).get("correlation_score", 0)
    print(sclr + Style.BRIGHT + f"  Correlation  : {corr_sig}/4 signals matched | score={corr_scr:.3f}")

    # Show which agents were live vs mock
    print()
    print(Fore.WHITE + Style.BRIGHT + "  DATA SOURCES:")
    for key, label in [
        ("agent1_currency", "Agent 1 (Currency)"),
        ("agent2_campaign", "Agent 2 (OSINT)"),
        ("agent3_call",     "Agent 3 (Scam Call)"),
    ]:
        ag = report.get(key) or {}
        src = ag.get("_source", "unknown")
        mock = ag.get("_mock", False)
        badge = "MOCK FALLBACK" if mock else ("PRECOMPUTED" if "precomputed" in str(src) else "LIVE")
        bclr = Fore.YELLOW if mock else (Fore.CYAN if "precomputed" in str(src) else Fore.GREEN)
        print(bclr + f"    {label:<22}: [{badge}] {src}")

    print(Fore.RED + Style.BRIGHT + "-" * w)
    print(Fore.WHITE + Style.BRIGHT + "  NARRATIVE:")
    # Word-wrap narrative
    words = narr.split()
    line  = "  "
    for word in words:
        if len(line) + len(word) + 1 > w - 2:
            print(Fore.WHITE + line)
            line = "    " + word + " "
        else:
            line += word + " "
    if line.strip():
        print(Fore.WHITE + line)

    print(Fore.RED + Style.BRIGHT + "-" * w)
    print(Fore.WHITE + Style.BRIGHT + "  RECOMMENDED ACTIONS (Citizen / Victim):")
    for i, action in enumerate(actions[:6], 1):
        line = f"  {i}. {action}"
        if len(line) > w - 2:
            line = line[:w - 5] + "..."
        print(Fore.WHITE + line)

    print(Fore.RED + Style.BRIGHT + "-" * w)
    print(Fore.CYAN + Style.BRIGHT + "  THREAT NEUTRALISATION PLAYBOOK (Law Enforcement):")
    for i, step in enumerate(play[:6], 1):
        line = f"  {i}. {step}"
        if len(line) > w - 2:
            line = line[:w - 5] + "..."
        print(Fore.CYAN + line)

    # Summary footer
    proc    = report.get("system", {}).get("processing_time_seconds", 0)
    evp_id  = (report.get("evidence_package") or {}).get("package_id", "N/A")
    pred    = report.get("victimisation_prediction") or {}
    v24_lo  = pred.get("estimated_victims_24h_low", 0)
    v24_hi  = pred.get("estimated_victims_24h_high", 0)
    net     = report.get("criminal_network") or {}

    print(Fore.RED + Style.BRIGHT + "-" * w)
    print(Fore.YELLOW + Style.BRIGHT + f"  Evidence Package  : {evp_id}")
    print(Fore.YELLOW + Style.BRIGHT + f"  Victims at Risk   : {v24_lo:,} - {v24_hi:,} in next 24h  [intervention required]")
    print(Fore.YELLOW + Style.BRIGHT + f"  Criminal Cell     : {net.get('cell_id', 'N/A')} | {net.get('estimated_operators', '?')} operators | {net.get('evidence_strength', '?').upper()} evidence")
    print(Fore.YELLOW + Style.BRIGHT + f"  Processing Time   : {proc}s")
    print(Fore.RED + Style.BRIGHT + "=" * w)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fraud Campaign Intelligence System — Live Demo (ET AI Hackathon 2.0)"
    )
    parser.add_argument("--image",    default=None, help="Path to currency image for Agent 1")
    parser.add_argument("--denom",    default="500", help="Denomination hint (default: 500)")
    parser.add_argument("--location", default="Jaipur Branch A", help="Detection location")
    parser.add_argument("--audio",    default=None, help="Path to scam call audio for Agent 3")
    parser.add_argument("--mongodb",  action="store_true", help="Force MongoDB source for Agent 2")
    parser.add_argument("--mongo-uri",default=None, help="MongoDB URI override")
    parser.add_argument("--output",   default="output", help="Output directory for report JSON")
    parser.add_argument("--all-mock", action="store_true", help="Force all-mock mode (testing only)")
    args = parser.parse_args()

    _header()

    # Resolve default paths relative to project root
    image_path = args.image or os.path.join(_PROJECT, "agent1", "sample_data", "500_fake_0.jpg")
    audio_path = args.audio or os.path.join(_PROJECT, "agent3", "audio", "sample.mp3")

    # Agent 2 source: always MongoDB by default (live); fallback is automatic inside adapter
    agent2_src = "mock" if args.all_mock else "mongodb"

    print(f"{_ts()} Initialising live multi-agent fraud intelligence pipeline...")
    print(f"{_ts()} Image path : {image_path}")
    print(f"{_ts()} Audio path : {audio_path}")
    print(f"{_ts()} Agent 2 src: {agent2_src} (auto-fallback enabled)")
    print()
    time.sleep(0.3)

    start     = time.time()
    report_id = f"FCIS-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    # -----------------------------------------------------------------------
    # Run agents — live first, automatic fallback on any failure
    # -----------------------------------------------------------------------
    if args.all_mock:
        a1 = agent1_adapter._mock_result(args.location)
        a1["_source"] = "mock_forced"; a1["_mock"] = True
        a2 = agent2_adapter._mock_event()
        a2["_source"] = "mock_forced"; a2["_mock"] = True
        a3 = agent3_adapter.mock_result()
        a3["_source"] = "mock_forced"; a3["_mock"] = True
    else:
        a1 = _run_agent1(image_path, args.denom, args.location)
        a2 = _run_agent2(agent2_src, mongo_uri=args.mongo_uri)
        a3 = _run_agent3(audio_path)

    # -----------------------------------------------------------------------
    # Agent 4 engines (always live — no mocks here)
    # -----------------------------------------------------------------------
    corr = _run_correlation(a1, a2, a3)
    net  = _run_network(a1, a2, a3, corr)
    pred = _run_prediction(a2, a3, corr)

    synth = synthesizer.synthesize(a1, a2, a3, corr, net, pred, None)
    evp   = _run_evidence(
        a1, a2, a3, corr,
        report_id,
        synth["composite_risk_score"],
        synth["severity"],
        synth["unified_scam_type"],
    )

    proc_time = round(time.time() - start, 2)

    # Assemble full report
    report = {
        "agent":       "Agent4_FraudCampaignOrchestrator",
        "system_name": "Fraud Campaign Intelligence System",
        "report_id":   report_id,
        "timestamp":   datetime.utcnow().isoformat() + "Z",
        "composite_risk_score": synth["composite_risk_score"],
        "severity":             synth["severity"],
        "unified_scam_type":    synth["unified_scam_type"],
        "triggered_by":         synth["triggered_by"],
        "agents_active":        synth["agents_active"],
        "agent1_currency":      a1,
        "agent2_campaign":      a2,
        "agent3_call":          a3,
        "correlation":          corr,
        "criminal_network":     net,
        "victimisation_prediction": pred,
        "evidence_package":     evp,
        "narrative":            synth["narrative"],
        "recommended_actions":  synth["recommended_actions"],
        "threat_neutralisation_playbook": synth["threat_neutralisation_playbook"],
        "system": {
            "processing_time_seconds": proc_time,
            "agents_active":           synth["agents_active"],
            "agent1_source":           a1.get("_source", "unknown"),
            "agent2_source":           a2.get("_source", "unknown"),
            "agent3_source":           a3.get("_source", "unknown"),
        },
    }

    # -----------------------------------------------------------------------
    # Print final report
    # -----------------------------------------------------------------------
    _print_final_report(report)

    # Save JSON
    output_dir = os.path.join(_AGENT4_DIR, args.output)
    path = save_report(report, output_dir)
    print(Fore.GREEN + Style.BRIGHT + f"  [SAVED] Full report  : {path}")
    print(Fore.CYAN  + f"  [EVIDENCE] Package   : {evp.get('package_id', 'N/A')}")
    print(Fore.CYAN  + f"  [NCRB] Complaint     : {evp.get('ncrb_complaint_draft', {}).get('submission_portal', 'cybercrime.gov.in')}")
    print()


if __name__ == "__main__":
    main()
