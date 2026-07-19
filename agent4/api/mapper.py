"""
agent4/api/mapper.py

Converts the raw Agent 4 orchestrator report dict into the CaseData shape
expected by the React frontend (src/mocks/cases.ts CaseData interface).
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict


def report_to_case(report: Dict[str, Any]) -> Dict[str, Any]:
    """Transform an orchestrator report dict → frontend CaseData JSON."""

    meta      = report.get("metadata", {})
    agents_r  = report.get("agents", {})
    synthesis = report.get("synthesis", {})
    net_r     = report.get("criminal_network_hypothesis", {})
    pred_r    = report.get("victimisation_prediction", {})
    evp_r     = report.get("evidence_package", {})
    sources_r = report.get("_sources", {})

    # ── Overall score & tier ─────────────────────────────────────────────────
    overall    = int(synthesis.get("composite_threat_score", 0))
    tier       = _score_to_tier(overall)
    confidence = int(synthesis.get("confidence_percent", synthesis.get("confidence", 0) * 100))

    # ── Per-agent cards ──────────────────────────────────────────────────────
    a1 = agents_r.get("agent1", {})
    a2 = agents_r.get("agent2", {})
    a3 = agents_r.get("agent3", {})
    ag4 = agents_r.get("agent4_fusion", {})

    agents = {
        "speech": _agent_card(
            score=int(a3.get("risk_score", 0)),
            confidence=int(a3.get("confidence", 0) * 100),
            verdict=a3.get("verdict", "No audio provided"),
            reasoning=a3.get("reasoning", ""),
            label="Call Analysis",
        ),
        "visual": _agent_card(
            score=int(a1.get("risk_score", 0)),
            confidence=int(a1.get("confidence", 0) * 100),
            verdict=a1.get("verdict", "No image provided"),
            reasoning=a1.get("reasoning", ""),
            label="Currency / Document CV",
        ),
        "text": _agent_card(
            score=int(a2.get("risk_score", 0)),
            confidence=int(a2.get("confidence", 0) * 100),
            verdict=a2.get("verdict", "No text provided"),
            reasoning=a2.get("reasoning", ""),
            label="OSINT / Campaign Intel",
        ),
        "network": _agent_card(
            score=int(ag4.get("risk_score", overall)),
            confidence=int(ag4.get("confidence", synthesis.get("confidence", 0)) * 100),
            verdict=ag4.get("verdict", synthesis.get("verdict", "Pending")),
            reasoning=ag4.get("reasoning", synthesis.get("key_evidence_summary", "")),
            label="Network Fusion",
        ),
    }

    # ── Evidence sources ─────────────────────────────────────────────────────
    sources_list: list[str] = []
    if a3.get("risk_score", 0) > 0: sources_list.append("audio")
    if a1.get("risk_score", 0) > 0: sources_list.append("image")
    if a2.get("risk_score", 0) > 0: sources_list.append("text")
    if not sources_list:            sources_list = ["text"]

    # ── Recommendations ──────────────────────────────────────────────────────
    recs_raw = synthesis.get("recommendations", [])
    recommendations = []
    for r in recs_raw[:6]:
        if isinstance(r, str):
            recommendations.append({"action": r, "urgency": _infer_urgency(r)})
        elif isinstance(r, dict):
            recommendations.append({"action": r.get("action", str(r)), "urgency": r.get("urgency", "info")})
    if not recommendations:
        recommendations = [
            {"action": "Report to National Cyber Crime Portal (cybercrime.gov.in)", "urgency": "critical"},
            {"action": "Call 1930 — National Cyber Helpline", "urgency": "warning"},
            {"action": "Contact your bank immediately if any financial details were shared", "urgency": "info"},
        ]

    # ── Timeline ─────────────────────────────────────────────────────────────
    now   = datetime.now(tz=timezone.utc)
    steps = [
        "Evidence Uploaded", "Currency Analysis (Agent 1)", "OSINT Analysis (Agent 2)",
        "Call Analysis (Agent 3)", "Cross-Agent Correlation",
        "Criminal Network Mapping", "Fusion Engine", "Final Verdict",
    ]
    timeline = [{"step": s, "timestamp": now.strftime("%H:%M:%S")} for s in steps]

    # ── Explainability ────────────────────────────────────────────────────────
    corr = report.get("cross_agent_correlation", {})
    signal_weights = corr.get("signal_weights", {})
    if not signal_weights:
        signal_weights = {"call_analysis": 0.28, "osint_campaign": 0.24, "currency_cv": 0.22, "network_fusion": 0.26}
    explainability = [{"signal": k.replace("_", " ").title(), "weight": v} for k, v in signal_weights.items()]

    # ── Criminal Network ──────────────────────────────────────────────────────
    criminal_network = None
    if net_r:
        infra = net_r.get("infrastructure", {})
        criminal_network = {
            "cellId":               net_r.get("cell_id", "CELL-UNKNOWN"),
            "estimatedOperators":   net_r.get("estimated_operators", "Unknown"),
            "geography":            ", ".join(net_r.get("operational_geography", [])),
            "modusOperandi":        net_r.get("modus_operandi", ""),
            "communication":        net_r.get("coordination_channels", []),
            "digitalInfra":         infra.get("spoofing", []) + infra.get("platforms", []),
            "impersonationTargets": net_r.get("impersonation_targets", []),
            "monthlyVictims":       net_r.get("estimated_monthly_victims", "Unknown"),
            "evidenceStrength":     net_r.get("evidence_strength", "MEDIUM").upper(),
            "confidence":           net_r.get("confidence", 0.5),
            "graphNodes":           net_r.get("graph_nodes", 0),
            "graphEdges":           net_r.get("graph_edges", 0),
        }

    # ── Victim Prediction ─────────────────────────────────────────────────────
    victim_prediction = None
    if pred_r:
        victim_prediction = {
            "urgencyLevel":        pred_r.get("urgency_level", "MONITOR"),
            "campaignGrowthRate":  pred_r.get("campaign_growth_rate", "STABLE").upper(),
            "postsPerHour":        pred_r.get("posts_per_hour"),
            "victims24hLow":       pred_r.get("estimated_victims_24h_low", 0),
            "victims24hHigh":      pred_r.get("estimated_victims_24h_high", 0),
            "victims48hLow":       pred_r.get("estimated_victims_48h_low", 0),
            "victims48hHigh":      pred_r.get("estimated_victims_48h_high", 0),
            "hoursToPeak":         pred_r.get("hours_to_peak_activity"),
            "predictionBasis":     pred_r.get("prediction_basis", "")[:120],
        }

    # ── Evidence Package ──────────────────────────────────────────────────────
    evidence_package_out = None
    if evp_r:
        evidence_package_out = {
            "packageId":    evp_r.get("package_id", "EVP-UNKNOWN"),
            "evidenceCount": evp_r.get("evidence_item_count", 0),
            "portalUrl":    "https://cybercrime.gov.in",
            "helpline":     "1930",
            "hasRbiAlert":  evp_r.get("rbi_ficn_alert_applicable", False),
        }

    # ── Source provenance ─────────────────────────────────────────────────────
    src_out = {
        "agent1": sources_r.get("agent1", "unknown"),
        "agent2": sources_r.get("agent2", "unknown"),
        "agent3": sources_r.get("agent3", "unknown"),
        "agent1Mock": sources_r.get("agent1_mock", True),
        "agent2Mock": sources_r.get("agent2_mock", False),
        "agent3Mock": sources_r.get("agent3_mock", True),
    }

    case_id = meta.get("case_id", f"FIP-{now.strftime('%Y%m%d-%H%M%S')}")

    result: Dict[str, Any] = {
        "caseId":      case_id,
        "timestamp":   now.isoformat(),
        "verdict":     synthesis.get("verdict", "Unknown"),
        "overallRisk": overall,
        "tier":        tier,
        "confidence":  confidence,
        "sources":     sources_list,
        "agents":      agents,
        "recommendations": recommendations,
        "timeline":    timeline,
        "explainability": explainability,
        "details": {
            "speech": {
                "transcript":        a3.get("transcript", ""),
                "keywords":          " ".join(a3.get("keywords", [])),
                "similarity":        a3.get("pattern_similarity", 0),
                "syntheticVoiceProb": a3.get("synthetic_voice_probability", 0),
                "reasoning":         a3.get("reasoning", ""),
            },
            "text": {
                "entities":    " ".join(a2.get("entities", [])),
                "threatLevel": a2.get("threat_level", "low"),
                "keywords":    " ".join(a2.get("keywords", [])),
                "category":    a2.get("campaign_type", "Unknown"),
                "reasoning":   a2.get("reasoning", ""),
            },
            "visual": {
                "ocr":     a1.get("ocr_text", ""),
                "forgery": str(a1.get("forgery_analysis", {})),
                "fakeId":  str(a1.get("fake_id_analysis", {})),
            },
            "network": {
                "phone":   a2.get("phone_number", ""),
                "bank":    a2.get("bank_account", ""),
                "email":   a2.get("email", ""),
                "ip":      a2.get("ip_address", ""),
                "flags":   str(a2.get("threat_flags", {})),
                "cluster": str(a2.get("campaign_cluster", {})),
            },
        },
    }

    if criminal_network:   result["criminalNetwork"]   = criminal_network
    if victim_prediction:  result["victimPrediction"]  = victim_prediction
    if evidence_package_out: result["evidencePackage"] = evidence_package_out
    result["_sources"] = src_out

    return result


# ── Helpers ──────────────────────────────────────────────────────────────────

def _score_to_tier(score: int) -> str:
    if score >= 85: return "critical"
    if score >= 65: return "high"
    if score >= 40: return "medium"
    if score >= 20: return "low"
    return "safe"


def _agent_card(score: int, confidence: int, verdict: str, reasoning: str, label: str) -> dict:
    return {
        "score":      score,
        "confidence": confidence,
        "verdict":    verdict,
        "reasoning":  reasoning,
        "label":      label,
    }


def _infer_urgency(action: str) -> str:
    a = action.lower()
    if any(w in a for w in ("block", "report", "arrest", "freeze", "cyber crime", "rbi")): return "critical"
    if any(w in a for w in ("warn", "alert", "monitor", "bank", "notify")): return "warning"
    return "info"
