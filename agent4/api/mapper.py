"""
agent4/api/mapper.py

Converts the raw Agent 4 orchestrator report dict into the CaseData shape
expected by the React frontend (src/mocks/cases.ts CaseData interface).

Key interface requirements:
  agents.*  : { score, confidence, status, summary }
  details.speech.transcript : { speaker, line }[]
  details.speech.keywords   : { term, severity }[]
  details.text.entities     : { label, value }[]
  details.text.keywords     : string[]
  details.visual.forgery    : { verdict, confidence }
  details.visual.fakeId     : { verdict, confidence, regions[] }
  details.network.flags     : Record<string, boolean>
  details.network.cluster   : { id, reports, description }
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List


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

    # ── Per-agent raw data ───────────────────────────────────────────────────
    a1  = agents_r.get("agent1", {})
    a2  = agents_r.get("agent2", {})
    a3  = agents_r.get("agent3", {})
    ag4 = agents_r.get("agent4_fusion", {})

    # ── Per-agent cards (must include status + summary) ──────────────────────
    agents = {
        "speech": _agent_card(
            score=int(a3.get("risk_score", 0)),
            confidence=int(a3.get("confidence", 0) * 100),
            summary=a3.get("verdict", a3.get("reasoning", "No audio provided"))[:120],
        ),
        "visual": _agent_card(
            score=int(a1.get("risk_score", 0)),
            confidence=int(a1.get("confidence", 0) * 100),
            summary=a1.get("verdict", a1.get("reasoning", "No image provided"))[:120],
        ),
        "text": _agent_card(
            score=int(a2.get("risk_score", 0)),
            confidence=int(a2.get("confidence", 0) * 100),
            summary=a2.get("verdict", a2.get("reasoning", "No text provided"))[:120],
        ),
        "network": _agent_card(
            score=int(ag4.get("risk_score", overall)),
            confidence=int(ag4.get("confidence", synthesis.get("confidence", 0)) * 100),
            summary=ag4.get("verdict", synthesis.get("verdict", "Pending"))[:120],
        ),
    }

    # ── Evidence sources ─────────────────────────────────────────────────────
    sources_list: List[str] = []
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
            recommendations.append({
                "action":  r.get("action", str(r)),
                "urgency": r.get("urgency", _infer_urgency(r.get("action", ""))),
            })
    if not recommendations:
        recommendations = [
            {"action": "Report to National Cyber Crime Portal (cybercrime.gov.in)", "urgency": "critical"},
            {"action": "Call 1930 — National Cyber Helpline",                        "urgency": "warning"},
            {"action": "Contact your bank immediately if any details were shared",   "urgency": "info"},
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
        signal_weights = {
            "call_analysis": 0.28,
            "osint_campaign": 0.24,
            "currency_cv": 0.22,
            "network_fusion": 0.26,
        }
    explainability = [
        {"signal": k.replace("_", " ").title(), "weight": v}
        for k, v in signal_weights.items()
    ]

    # ── details.speech ────────────────────────────────────────────────────────
    raw_transcript = a3.get("transcript", "")
    if isinstance(raw_transcript, list):
        # Already structured [{speaker, line}]
        transcript = [
            {"speaker": t.get("speaker", "Unknown"), "line": t.get("line", t.get("text", ""))}
            for t in raw_transcript
        ]
    elif isinstance(raw_transcript, str) and raw_transcript:
        # Plain string — split into caller/victim turns
        lines = raw_transcript.strip().split("\n")
        transcript = []
        for i, line in enumerate(lines):
            if ":" in line:
                sp, txt = line.split(":", 1)
                transcript.append({"speaker": sp.strip(), "line": txt.strip()})
            else:
                transcript.append({"speaker": "Caller" if i % 2 == 0 else "Victim", "line": line.strip()})
    else:
        transcript = []

    raw_kw_speech = a3.get("keywords", [])
    if isinstance(raw_kw_speech, list) and raw_kw_speech and isinstance(raw_kw_speech[0], dict):
        speech_keywords = [
            {"term": k.get("term", str(k)), "severity": k.get("severity", "medium")}
            for k in raw_kw_speech
        ]
    elif isinstance(raw_kw_speech, list):
        speech_keywords = [{"term": str(k), "severity": "high"} for k in raw_kw_speech]
    elif isinstance(raw_kw_speech, str):
        speech_keywords = [{"term": t.strip(), "severity": "high"} for t in raw_kw_speech.split(",") if t.strip()]
    else:
        speech_keywords = []

    details_speech = {
        "transcript":        transcript,
        "keywords":          speech_keywords,
        "similarity":        float(a3.get("pattern_similarity", 0)),
        "syntheticVoiceProb": float(a3.get("synthetic_voice_probability", 0)),
        "reasoning":         a3.get("reasoning", ""),
    }

    # ── details.text ──────────────────────────────────────────────────────────
    raw_entities = a2.get("entities", [])
    if isinstance(raw_entities, list) and raw_entities and isinstance(raw_entities[0], dict):
        text_entities = [
            {"label": e.get("label", "Entity"), "value": e.get("value", str(e))}
            for e in raw_entities
        ]
    elif isinstance(raw_entities, list):
        text_entities = [{"label": f"Entity {i+1}", "value": str(e)} for i, e in enumerate(raw_entities)]
    elif isinstance(raw_entities, str) and raw_entities:
        text_entities = [{"label": f"Term {i+1}", "value": t.strip()} for i, t in enumerate(raw_entities.split(",")) if t.strip()]
    else:
        text_entities = []

    raw_kw_text = a2.get("keywords", [])
    if isinstance(raw_kw_text, list):
        text_keywords = [str(k) for k in raw_kw_text]
    elif isinstance(raw_kw_text, str):
        text_keywords = [t.strip() for t in raw_kw_text.split(",") if t.strip()]
    else:
        text_keywords = []

    raw_threat_level = a2.get("threat_level", "low")
    if raw_threat_level not in ("critical", "high", "medium", "low", "safe"):
        raw_threat_level = "medium"

    details_text = {
        "entities":    text_entities,
        "threatLevel": raw_threat_level,
        "keywords":    text_keywords,
        "category":    a2.get("campaign_type", "Unknown"),
        "reasoning":   a2.get("reasoning", ""),
    }

    # ── details.visual ────────────────────────────────────────────────────────
    raw_forgery = a1.get("forgery_analysis", {})
    if isinstance(raw_forgery, dict):
        forgery = {
            "verdict":    raw_forgery.get("verdict", raw_forgery.get("result", "Unknown")),
            "confidence": float(raw_forgery.get("confidence", 0)),
        }
    else:
        forgery = {"verdict": str(raw_forgery) if raw_forgery else "No analysis", "confidence": 0.0}

    raw_fake_id = a1.get("fake_id_analysis", {})
    if isinstance(raw_fake_id, dict):
        raw_regions = raw_fake_id.get("regions", raw_fake_id.get("anomaly_regions", []))
        if isinstance(raw_regions, list):
            regions = [
                {
                    "x": float(r.get("x", r[0] if isinstance(r, (list, tuple)) else 10)),
                    "y": float(r.get("y", r[1] if isinstance(r, (list, tuple)) else 10)),
                    "w": float(r.get("w", r[2] if isinstance(r, (list, tuple)) else 30)),
                    "h": float(r.get("h", r[3] if isinstance(r, (list, tuple)) else 20)),
                }
                for r in raw_regions[:4]
            ]
        else:
            regions = []
        fake_id = {
            "verdict":    raw_fake_id.get("verdict", raw_fake_id.get("result", "Unknown")),
            "confidence": float(raw_fake_id.get("confidence", 0)),
            "regions":    regions,
        }
    else:
        fake_id = {
            "verdict":    str(raw_fake_id) if raw_fake_id else "No analysis",
            "confidence": 0.0,
            "regions":    [],
        }

    details_visual = {
        "ocr":     a1.get("ocr_text", ""),
        "forgery": forgery,
        "fakeId":  fake_id,
    }

    # ── details.network ───────────────────────────────────────────────────────
    raw_flags = a2.get("threat_flags", {})
    if isinstance(raw_flags, dict):
        flags = {k: bool(v) for k, v in raw_flags.items()}
        # Ensure the four keys the frontend uses always exist
        for key in ("phone", "bank", "email", "ip"):
            flags.setdefault(key, False)
    else:
        flags = {"phone": False, "bank": False, "email": False, "ip": False}

    raw_cluster = a2.get("campaign_cluster", {})
    if isinstance(raw_cluster, dict):
        cluster = {
            "id":          raw_cluster.get("id", raw_cluster.get("cluster_id", "UNKNOWN")),
            "reports":     int(raw_cluster.get("reports", raw_cluster.get("report_count", 0))),
            "description": raw_cluster.get("description", raw_cluster.get("campaign_type", "")),
        }
    else:
        cluster = {"id": "UNKNOWN", "reports": 0, "description": str(raw_cluster) if raw_cluster else ""}

    details_network = {
        "phone":   str(a2.get("phone_number", "")),
        "bank":    str(a2.get("bank_account", "")),
        "email":   str(a2.get("email", "")),
        "ip":      str(a2.get("ip_address", "")),
        "flags":   flags,
        "cluster": cluster,
    }

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
            "urgencyLevel":       pred_r.get("urgency_level", "MONITOR"),
            "campaignGrowthRate": pred_r.get("campaign_growth_rate", "STABLE").upper(),
            "postsPerHour":       pred_r.get("posts_per_hour"),
            "victims24hLow":      pred_r.get("estimated_victims_24h_low", 0),
            "victims24hHigh":     pred_r.get("estimated_victims_24h_high", 0),
            "victims48hLow":      pred_r.get("estimated_victims_48h_low", 0),
            "victims48hHigh":     pred_r.get("estimated_victims_48h_high", 0),
            "hoursToPeak":        pred_r.get("hours_to_peak_activity"),
            "predictionBasis":    pred_r.get("prediction_basis", "")[:120],
        }

    # ── Evidence Package ──────────────────────────────────────────────────────
    evidence_package_out = None
    if evp_r:
        evidence_package_out = {
            "packageId":     evp_r.get("package_id", "EVP-UNKNOWN"),
            "evidenceCount": evp_r.get("evidence_item_count", 0),
            "portalUrl":     "https://cybercrime.gov.in",
            "helpline":      "1930",
            "hasRbiAlert":   evp_r.get("rbi_ficn_alert_applicable", False),
        }

    # ── Source provenance ─────────────────────────────────────────────────────
    src_out = {
        "agent1":     sources_r.get("agent1", "unknown"),
        "agent2":     sources_r.get("agent2", "unknown"),
        "agent3":     sources_r.get("agent3", "unknown"),
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
            "speech":  details_speech,
            "text":    details_text,
            "visual":  details_visual,
            "network": details_network,
        },
    }

    if criminal_network:     result["criminalNetwork"]  = criminal_network
    if victim_prediction:    result["victimPrediction"] = victim_prediction
    if evidence_package_out: result["evidencePackage"]  = evidence_package_out
    result["_sources"] = src_out

    return result


# ── Helpers ──────────────────────────────────────────────────────────────────

def _score_to_tier(score: int) -> str:
    if score >= 85: return "critical"
    if score >= 65: return "high"
    if score >= 40: return "medium"
    if score >= 20: return "low"
    return "safe"


def _agent_card(score: int, confidence: int, summary: str) -> dict:
    return {
        "score":      score,
        "confidence": confidence,
        "status":     "complete",   # always complete when mapper is called
        "summary":    summary,
    }


def _infer_urgency(action: str) -> str:
    a = action.lower()
    if any(w in a for w in ("block", "report", "arrest", "freeze", "cyber crime", "rbi")): return "critical"
    if any(w in a for w in ("warn", "alert", "monitor", "bank", "notify")):               return "warning"
    return "info"
