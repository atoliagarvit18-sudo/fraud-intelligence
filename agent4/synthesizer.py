"""
agent4/synthesizer.py

Composite scoring, severity determination, narrative generation,
and recommended action / playbook builder.

This module turns the raw outputs of all four engines into the
human-readable, judge-ready unified threat intelligence report.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Composite score weights
# ---------------------------------------------------------------------------

_W_AGENT1 = 0.20   # Currency confidence
_W_AGENT2 = 0.35   # Campaign score
_W_AGENT3 = 0.45   # Scam call risk score (most direct victim evidence)

# Correlation signal bonuses (added on top of weighted average × 100)
_BONUS_SCAM_MATCH  = 15
_BONUS_GEO_OVERLAP = 10
_BONUS_TEMPORAL    = 8
_BONUS_INFRA       = 7
_BONUS_3_AGENTS    = 10
_BONUS_2_AGENTS    = 5

# Severity ladder
_SEVERITY_THRESHOLDS = [
    (85, "CRITICAL"),
    (65, "HIGH"),
    (40, "MEDIUM"),
    (0,  "LOW"),
]

# Action templates keyed by scam type
_ACTIONS = {
    "Digital Arrest": [
        "Hang up immediately — no legitimate government agency will call and threaten arrest",
        "Call 1930 (National Cybercrime Helpline) to report the incident",
        "File a complaint at cybercrime.gov.in with evidence package",
        "Alert family members — do NOT transfer any money or share OTPs",
        "Contact your bank immediately if any financial details were shared",
    ],
    "Bank Fraud": [
        "Call your bank's fraud helpline immediately and freeze the account",
        "Change all digital banking passwords and UPI PINs",
        "File a complaint at cybercrime.gov.in (helpline: 1930)",
        "Do NOT click any links sent via SMS or WhatsApp",
        "File an FIR at the local police station with transaction details",
    ],
    "KYC Scam": [
        "Never share OTP, CVV, or PIN with anyone claiming to update KYC",
        "Visit your bank branch in person for any KYC updates",
        "Uninstall any APK or app installed during the call",
        "Call 1930 (Cybercrime Helpline) and your bank's fraud line",
        "Report the incident at cybercrime.gov.in",
    ],
    "Investment Scam": [
        "Stop all payments immediately and contact your bank",
        "Do NOT make any further 'tax' or 'withdrawal fee' payments",
        "File a complaint at cybercrime.gov.in (helpline: 1930)",
        "Report to SEBI if stock market / investment fraud: sebi.gov.in",
        "Preserve all chat screenshots, transaction receipts as evidence",
    ],
    "_default": [
        "Call 1930 (National Cybercrime Helpline) immediately",
        "File a complaint at cybercrime.gov.in",
        "Do NOT transfer money or share any personal/financial information",
        "Preserve all evidence: call recordings, screenshots, messages",
        "File an FIR at the nearest police station",
    ],
}

# Playbook templates (law-enforcement / institutional actions)
_PLAYBOOK = {
    "Digital Arrest": [
        "Immediately escalate to State Cyber Crime Unit — campaign is active",
        "Request CDR (Call Detail Records) from telecom provider for spoofed numbers",
        "Alert Telegram India (@spambot) to identified scam channels for takedown",
        "Coordinate with FICN detection if counterfeit currency co-detected",
        "Issue advisory to regional banks: watch for unusual large cash withdrawals by elderly customers",
        "Share intelligence with adjacent state cyber units — campaign may expand geographically",
        "Initiate Section 66C/66D IT Act proceedings if suspects are identified",
    ],
    "Bank Fraud": [
        "Alert nodal officer at victim's bank to freeze mule accounts",
        "File a complaint with RBI Ombudsman if bank is non-cooperative",
        "Request NPCI to flag suspicious UPI VPAs identified in investigation",
        "Share suspect device fingerprints with CERT-In",
    ],
    "_default": [
        "Escalate to State Cyber Crime Unit immediately",
        "Preserve all digital evidence per POCSO/IT Act guidelines",
        "File FIR under relevant sections of BNS (Bharatiya Nyaya Sanhita)",
        "Submit evidence package to designated cybercrime court",
    ],
}

_FICN_PLAYBOOK = [
    "Alert RBI Currency Management Division with FICN batch ID and location",
    "Instruct local bank branches in the area to use UV scanners for ₹{denom} notes",
    "Notify Currency Crime Cell at nearest police station with batch fingerprint data",
    "Cross-reference batch ID across all Agent 1 detections for circulation map",
    "File FIR under Section 489A/489B IPC (Counterfeit Currency)",
]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def synthesize(
    agent1: Optional[Dict[str, Any]],
    agent2: Optional[Dict[str, Any]],
    agent3: Optional[Dict[str, Any]],
    correlation: Dict[str, Any],
    criminal_network: Optional[Dict[str, Any]],
    victimisation: Optional[Dict[str, Any]],
    evidence_package: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute composite score, severity, narrative, and action items.

    Returns a dict ready to populate ThreatIntelligenceReport.
    """
    scam_type = correlation.get("unified_scam_type", "Unknown")

    # --- Composite scoring ---
    score = _compute_composite_score(agent1, agent2, agent3, correlation)
    severity = _severity(score)

    # --- Narrative ---
    narrative = _build_narrative(
        agent1, agent2, agent3, correlation, criminal_network,
        victimisation, score, severity, scam_type
    )

    # --- Actions ---
    actions    = _actions_for(scam_type)
    playbook   = _playbook_for(scam_type, agent1)
    triggered  = _triggered_agents(agent1, agent2, agent3)

    return {
        "composite_risk_score": score,
        "severity":             severity,
        "unified_scam_type":    scam_type,
        "triggered_by":         triggered,
        "agents_active":        len(triggered),
        "narrative":            narrative,
        "recommended_actions":  actions,
        "threat_neutralisation_playbook": playbook,
    }


# ---------------------------------------------------------------------------
# Composite score
# ---------------------------------------------------------------------------

def _compute_composite_score(a1, a2, a3, corr) -> int:
    scores, weights = [], []

    # Agent 1: confidence 0-1 when verdict is fake
    if a1 and a1.get("verdict") == "fake" and a1.get("confidence") is not None:
        scores.append(float(a1["confidence"]))
        weights.append(_W_AGENT1)

    # Agent 2: campaign score 0-1
    if a2 and a2.get("available") and a2.get("campaign_score") is not None:
        scores.append(float(a2["campaign_score"]))
        weights.append(_W_AGENT2)

    # Agent 3: risk score 0-100 → normalise to 0-1
    if a3 and a3.get("available") and a3.get("risk_score") is not None:
        scores.append(float(a3["risk_score"]) / 100.0)
        weights.append(_W_AGENT3)

    if not scores:
        return 0

    # Normalise weights to sum to 1.0
    total_w = sum(weights)
    base = sum(s * w for s, w in zip(scores, weights)) / total_w

    # Correlation bonuses
    bonus = 0
    if corr.get("scam_type_match"):    bonus += _BONUS_SCAM_MATCH
    if corr.get("geo_overlap"):        bonus += _BONUS_GEO_OVERLAP
    if corr.get("temporal_spike"):     bonus += _BONUS_TEMPORAL
    if corr.get("infrastructure_link"): bonus += _BONUS_INFRA
    n = len(scores)
    if n >= 3:   bonus += _BONUS_3_AGENTS
    elif n >= 2: bonus += _BONUS_2_AGENTS

    return min(round(base * 100) + bonus, 100)


def _severity(score: int) -> str:
    for threshold, label in _SEVERITY_THRESHOLDS:
        if score >= threshold:
            return label
    return "LOW"


# ---------------------------------------------------------------------------
# Narrative
# ---------------------------------------------------------------------------

def _build_narrative(a1, a2, a3, corr, net, pred, score, severity, scam_type) -> str:
    parts = []

    # Opening: what is happening
    if severity == "CRITICAL":
        opener = f"🚨 A coordinated '{scam_type}' fraud campaign is ACTIVELY operating"
    elif severity == "HIGH":
        opener = f"⚠️  A high-risk '{scam_type}' fraud operation has been detected"
    else:
        opener = f"A '{scam_type}' fraud incident has been identified"

    locations = corr.get("geo_locations") or []
    # Pull from network hypothesis if available
    if net and net.get("operational_geography"):
        locations = net["operational_geography"]
    elif a1 and a1.get("location"):
        locations = [a1["location"]]
    elif a2 and a2.get("locations"):
        locations = [l.title() for l in a2["locations"][:2]]

    if locations:
        parts.append(f"{opener} in {', '.join(locations[:2])}.")
    else:
        parts.append(f"{opener}.")

    # Three-source corroboration
    sources_active = []
    if a3 and a3.get("available"):
        risk = a3.get("risk_score", 0)
        conf = a3.get("confidence", 0)
        tactics_str = ", ".join((a3.get("psychological_tactics") or [])[:2])
        entities_str = ", ".join((a3.get("government_entities") or [])[:2])
        call_part = (
            f"A scam phone call with risk score {risk}/100 and confidence {conf:.0%} "
            f"was intercepted — all three AI analyzers are in agreement"
        )
        if entities_str:
            call_part += f", identifying impersonation of {entities_str}"
        if tactics_str:
            call_part += f" and psychological tactics including {tactics_str}"
        sources_active.append(call_part + ".")

    if a2 and a2.get("available"):
        post_count = a2.get("post_count", 0)
        source_list = ", ".join((a2.get("sources") or [])[:2])
        sev = (a2.get("severity") or "").upper()
        campaign_part = (
            f"An OSINT sweep across {source_list} has tracked {post_count} posts "
            f"forming a {sev}-severity campaign cluster — the campaign is multi-platform "
            f"and actively growing."
        )
        sources_active.append(campaign_part)

    if a1 and a1.get("verdict") == "fake":
        denom = a1.get("denomination", "?")
        batch = a1.get("batch_id", "unknown batch")
        loc   = a1.get("location", "detected location")
        ficn_part = (
            f"Counterfeit ₹{denom} notes from print batch {batch} are simultaneously "
            f"circulating at {loc} — FICN is a known prop used in {scam_type} cases "
            f"to create false legitimacy."
        )
        sources_active.append(ficn_part)

    if sources_active:
        parts.append("Real-time intelligence from three independent sources converges on a single criminal operation: "
                     + " ".join(f"({i+1}) {s}" for i, s in enumerate(sources_active)))

    # Criminal network
    if net and net.get("estimated_operators"):
        ops   = net["estimated_operators"]
        coord = ", ".join((net.get("coordination_channels") or [])[:2]) or "unknown channels"
        parts.append(
            f"The criminal cell is estimated to comprise {ops} operators "
            f"coordinating via {coord}, with evidence of both digital and physical "
            f"fraud vectors operating simultaneously."
        )

    # Prediction
    if pred and pred.get("urgency_level") in ("IMMEDIATE", "URGENT"):
        low  = pred.get("estimated_victims_24h_low", 0)
        high = pred.get("estimated_victims_24h_high", 0)
        urg  = pred.get("urgency_level")
        parts.append(
            f"Without immediate intervention, this campaign is projected to "
            f"victimise an estimated {low:,} to {high:,} additional citizens within the next 24 hours "
            f"(urgency: {urg})."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Actions and playbook
# ---------------------------------------------------------------------------

def _actions_for(scam_type: str) -> List[str]:
    return _ACTIONS.get(scam_type, _ACTIONS["_default"])


def _playbook_for(scam_type: str, agent1) -> List[str]:
    base = _PLAYBOOK.get(scam_type, _PLAYBOOK["_default"])
    if agent1 and agent1.get("verdict") == "fake":
        denom = agent1.get("denomination", "?")
        ficn  = [s.format(denom=denom) for s in _FICN_PLAYBOOK]
        return base + ficn
    return base


def _triggered_agents(a1, a2, a3) -> List[str]:
    out = []
    if a1 and a1.get("available"):      out.append("agent1_currency")
    if a2 and a2.get("available"):      out.append("agent2_osint_campaign")
    if a3 and a3.get("available"):      out.append("agent3_scam_call")
    return out
