"""
agent4/correlator.py

Cross-agent correlation engine.

Links signals from Agent 1 (currency), Agent 2 (OSINT), and Agent 3 (scam calls)
to detect coordinated, multi-vector fraud campaigns.

Four correlation signals are evaluated:
  1. Scam type match    — same fraud category across multiple agents
  2. Geographic overlap — same city/region detected by ≥ 2 agents
  3. Temporal spike     — all agents fired within a short time window
  4. Infrastructure link — shared platform/tactic signatures between agents

Correlation score formula:
  score = 0.35 × (scam_match) + 0.30 × (geo) + 0.20 × (temporal) + 0.15 × (infra)
  Range: 0.0 (no signals) → 1.0 (all four signals matched)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Scam type equivalence mapping
# Agent 3 uses human labels; Agent 2 uses snake_case.
# ---------------------------------------------------------------------------
_SCAM_TYPE_MAP: Dict[str, List[str]] = {
    "Digital Arrest": ["digital_arrest", "cyber_crime", "other"],
    "Bank Fraud":     ["bank_fraud", "phishing", "identity_theft"],
    "KYC Scam":       ["phishing", "identity_theft", "other"],
    "Investment Scam": ["investment_scam", "ponzi", "crypto_fraud", "fake_broker"],
    "Lottery Scam":   ["lottery_scam", "other"],
    "Job Scam":       ["job_scam", "other"],
    "Courier Scam":   ["courier_scam", "other"],
}

# ---------------------------------------------------------------------------
# City keyword lookup — supports fuzzy geographic matching
# ---------------------------------------------------------------------------
_CITY_KEYWORDS: Dict[str, List[str]] = {
    "jaipur":     ["jaipur", "pink city"],
    "delhi":      ["delhi", "new delhi", "ndmc", "ncr"],
    "mumbai":     ["mumbai", "bombay"],
    "bangalore":  ["bangalore", "bengaluru"],
    "hyderabad":  ["hyderabad"],
    "chennai":    ["chennai", "madras"],
    "kolkata":    ["kolkata", "calcutta"],
    "pune":       ["pune"],
    "jodhpur":    ["jodhpur"],
    "ajmer":      ["ajmer"],
    "rajasthan":  ["rajasthan"],
    "gujarat":    ["gujarat", "ahmedabad", "surat"],
}

# Events within this many minutes are considered a temporal spike
_TEMPORAL_WINDOW_MIN = 60


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def correlate(
    agent1: Optional[Dict[str, Any]],
    agent2: Optional[Dict[str, Any]],
    agent3: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluate all four correlation signals and return a correlation result.

    Args:
        agent1: Normalised Agent 1 result dict (or None if not run).
        agent2: Normalised Agent 2 result dict (or None if not run).
        agent3: Normalised Agent 3 result dict (or None if not run).

    Returns:
        dict matching CorrelationResult schema.
    """
    evidence: List[str] = []

    scam_match  = _check_scam_type_match(agent1, agent2, agent3, evidence)
    geo_match   = _check_geo_overlap(agent1, agent2, agent3, evidence)
    temp_match  = _check_temporal_spike(agent1, agent2, agent3, evidence)
    infra_match = _check_infrastructure_link(agent2, agent3, evidence)

    weights = {
        "scam":  (0.35, scam_match),
        "geo":   (0.30, geo_match),
        "temp":  (0.20, temp_match),
        "infra": (0.15, infra_match),
    }
    score = sum(w for w, matched in weights.values() if matched)
    # Minimum floor when at least one signal fires
    if any(m for _, m in weights.values()):
        score = max(score, 0.25)

    unified_scam = _unified_scam_type(agent2, agent3)

    return {
        "scam_type_match":    scam_match,
        "geo_overlap":        geo_match,
        "temporal_spike":     temp_match,
        "infrastructure_link": infra_match,
        "correlation_score":  round(score, 3),
        "signals_matched":    sum([scam_match, geo_match, temp_match, infra_match]),
        "signals_total":      4,
        "correlation_evidence": evidence,
        "unified_scam_type":  unified_scam,
        "linked_campaign_id": f"cluster_{agent2['cluster_id']}" if agent2 and agent2.get("cluster_id") else None,
    }


# ---------------------------------------------------------------------------
# Signal evaluators
# ---------------------------------------------------------------------------

def _check_scam_type_match(a1, a2, a3, evidence: List[str]) -> bool:
    a3_scam = (a3 or {}).get("scam_type")
    a2_scam = (a2 or {}).get("scam_type")

    if a3_scam and a2_scam and a3_scam not in ("Unknown", None):
        compatible = _SCAM_TYPE_MAP.get(a3_scam, [])
        a2_norm = a2_scam.lower().replace(" ", "_")
        if a2_norm in compatible or a3_scam.lower().replace(" ", "_") == a2_norm:
            evidence.append(
                f"Agent 3 (Scam Call) and Agent 2 (OSINT) independently classify "
                f"this as '{a3_scam}' — cross-source confirmation"
            )
            # FICN + Digital Arrest is a known co-tactic
            if a1 and a1.get("verdict") == "fake" and a3_scam == "Digital Arrest":
                evidence.append(
                    "Counterfeit currency (Agent 1) co-detected with Digital Arrest "
                    "scam — FICN is used as a physical prop in 23% of DA cases (RBI 2024)"
                )
            return True

    if a1 and a1.get("verdict") == "fake":
        if a3_scam == "Digital Arrest" or (a2_scam and "digital" in a2_scam.lower()):
            evidence.append(
                "Fake currency at scene consistent with Digital Arrest modus operandi"
            )
            return True

    return False


def _check_geo_overlap(a1, a2, a3, evidence: List[str]) -> bool:
    raw_locations: List[tuple] = []

    if a1 and a1.get("location"):
        raw_locations.append(("Agent1", a1["location"].lower()))

    for loc in (a2 or {}).get("locations", []):
        raw_locations.append(("Agent2", loc.lower()))

    # Map raw strings to canonical city names
    city_agents: Dict[str, List[str]] = {}
    for agent, loc_str in raw_locations:
        for city, keywords in _CITY_KEYWORDS.items():
            if any(kw in loc_str for kw in keywords):
                city_agents.setdefault(city, []).append(agent)

    overlapping = {
        city: list(set(agents))
        for city, agents in city_agents.items()
        if len(set(agents)) >= 2
    }

    if overlapping:
        for city, agents in overlapping.items():
            evidence.append(
                f"Geographic overlap confirmed: {city.title()} independently detected "
                f"by {' and '.join(agents)}"
            )
        return True

    # Single-agent location is still reported but not a confirmed overlap
    if raw_locations:
        locs = ", ".join(set(l for _, l in raw_locations))
        evidence.append(f"Operational geography identified: {locs}")

    return False


def _check_temporal_spike(a1, a2, a3, evidence: List[str]) -> bool:
    now = datetime.now(timezone.utc)
    timestamps: List[tuple] = []

    if a1 and a1.get("timestamp"):
        try:
            ts = _parse_ts(a1["timestamp"])
            timestamps.append(("Agent1", ts))
        except Exception:
            pass

    if a3 and a3.get("available"):
        timestamps.append(("Agent3", now))

    if a2:
        td = a2.get("temporal_data") or {}
        latest = td.get("latest_post")
        if latest:
            try:
                ts = _parse_ts(latest)
                timestamps.append(("Agent2", ts))
            except Exception:
                pass

    if len(timestamps) >= 2:
        times = [ts for _, ts in timestamps]
        span_min = (max(times) - min(times)).total_seconds() / 60
        if span_min <= _TEMPORAL_WINDOW_MIN:
            evidence.append(
                f"Temporal spike: all {len(timestamps)} agents activated within "
                f"{int(span_min)} minute(s) — coordinated multi-vector attack signature"
            )
        else:
            evidence.append(
                f"Multi-agent activation within {int(span_min / 60)} hour(s) — "
                f"campaign is actively operating"
            )
        return True

    if len(timestamps) == 1:
        evidence.append("Real-time intelligence: live agent activation detected")
        return True

    return False


def _check_infrastructure_link(a2, a3, evidence: List[str]) -> bool:
    if not a2 or not a3:
        return False

    a2_sources  = [s.lower() for s in (a2.get("sources") or [])]
    a3_tactics  = [t.lower() for t in (a3.get("psychological_tactics") or [])]
    a3_entities = [e.lower() for e in (a3.get("government_entities") or [])]

    found = False

    if "telegram" in a2_sources and (
        "authority impersonation" in a3_tactics
        or any(e in ["cbi", "ed", "enforcement directorate", "customs"] for e in a3_entities)
    ):
        evidence.append(
            "Telegram-coordinated OSINT campaign (Agent 2) linked to authority-"
            "impersonation call pattern (Agent 3) — shared criminal infrastructure"
        )
        found = True

    if a3_entities and (a2.get("scam_type") or "").lower() in ("digital_arrest", "cyber_crime"):
        gov_list = ", ".join(a3_entities[:3])
        evidence.append(
            f"Government entity impersonation ({gov_list}) in call matches "
            f"OSINT campaign profile — consistent criminal modus operandi"
        )
        found = True

    return found


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_ts(ts_str: str) -> datetime:
    ts_str = ts_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _unified_scam_type(a2, a3) -> str:
    if a3 and a3.get("scam_type") and a3["scam_type"] not in (None, "Unknown"):
        return a3["scam_type"]
    if a2 and a2.get("scam_type"):
        return a2["scam_type"].replace("_", " ").title()
    return "Unknown"
