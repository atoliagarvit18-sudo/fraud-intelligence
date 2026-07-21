"""
agent4/network_graph.py

Criminal Network Hypothesis Engine.

Builds a graph model of the inferred criminal infrastructure from
multi-agent intelligence signals. This is a HYPOTHESIS for investigative
guidance — not a legally proven assertion.

Nodes represent:
  - ScamOperation      (the central coordinating entity)
  - Platform_X         (Telegram channels, Reddit communities)
  - GeographicZone_X   (operational cities/states)
  - PhysicalVector_X   (counterfeit currency batches)
  - ImpersonatedAgency_X (CBI, ED, RBI etc.)
  - CriminalOperator   (estimated individual actors)

Edges represent:
  - Operational connections (uses, targets, coordinates_via)
  - Each edge has a confidence weight based on evidence quality

The graph yields:
  - Estimated operator count (from coordination complexity)
  - Key infrastructure node (most connected)
  - Operational geography list
  - Evidence strength rating
"""

from typing import Any, Dict, List, Optional

try:
    import networkx as nx
    _NX_AVAILABLE = True
except ImportError:
    nx = None
    _NX_AVAILABLE = False


# ---------------------------------------------------------------------------
# Operator count estimation heuristics
# ---------------------------------------------------------------------------
# Each factor adds to estimated operator count

_OP_BASE = 2                        # minimum: caller + handler
_OP_PER_PLATFORM = 1                # each additional platform = coordinator
_OP_PER_CURRENCY_BATCH = 1          # each batch = distributor
_OP_IF_MULTI_CITY = 2               # multi-city = additional field agents
_OP_IF_MULTI_SOURCE = 1             # cross-platform = social media manager
_OP_IF_VIDEO_CALL = 1               # DA video call = technical operator
_OP_IF_FINANCIAL_REQUEST = 1        # money mule coordinator


def build(
    agent1: Optional[Dict[str, Any]],
    agent2: Optional[Dict[str, Any]],
    agent3: Optional[Dict[str, Any]],
    correlation: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a criminal network hypothesis from multi-agent intelligence.

    Args:
        agent1:      Currency agent output (or None).
        agent2:      OSINT agent output (or None).
        agent3:      Call agent output (or None).
        correlation: Correlation result dict (or None).

    Returns:
        dict matching CriminalNetworkHypothesis schema.
    """
    # Gather all intelligence signals
    signals = _extract_signals(agent1, agent2, agent3, correlation)

    # Estimate operator count
    op_min, op_max = _estimate_operators(signals)

    # Build the graph
    G, key_node = _build_graph(signals, op_min, op_max)

    nodes = G.number_of_nodes() if _NX_AVAILABLE else len(signals.get("platforms", [])) + 4
    edges = G.number_of_edges() if _NX_AVAILABLE else nodes - 1

    # Determine evidence strength
    ev_strength = _evidence_strength(signals, correlation)

    # Build human-readable infrastructure dict
    infrastructure = {
        "communication": list(set(signals["platforms"])),
        "physical":      ["counterfeit_currency"] if signals["has_ficn"] else [],
        "digital":       _digital_infrastructure(signals),
        "impersonation": signals["gov_entities"],
    }
    infrastructure = {k: v for k, v in infrastructure.items() if v}

    # Monthly victim estimate (rough, for context)
    monthly_victims = _monthly_victim_estimate(signals)

    # Generate cell ID from geography and scam type
    geo_tag = (signals["locations"][0][:3].upper() if signals["locations"] else "UNK")
    scam_tag = (signals["scam_type"][:2].upper() if signals["scam_type"] else "FR")
    cell_id  = f"CELL-{geo_tag}-2026-{scam_tag}1"

    return {
        "cell_id":                cell_id,
        "estimated_operators":    f"{op_min}–{op_max}",
        "operational_geography":  [loc.title() for loc in signals["locations"]],
        "infrastructure":         infrastructure,
        "modus_operandi":         _modus_operandi(signals),
        "impersonation_targets":  signals["gov_entities"],
        "coordination_channels":  signals["platforms"],
        "estimated_monthly_victims": monthly_victims,
        "confidence":             _confidence_score(signals, correlation),
        "evidence_strength":      ev_strength,
        "graph_nodes":            nodes,
        "graph_edges":            edges,
        "key_infrastructure_node": key_node,
        "disclaimer": (
            "This is an AI-generated hypothesis for investigative guidance only. "
            "It must be verified by a qualified cybercrime investigator before any "
            "enforcement action."
        ),
    }


# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------

def _extract_signals(a1, a2, a3, corr) -> Dict[str, Any]:
    """Pull all relevant signals from agent outputs into a flat dict."""
    platforms: List[str] = []
    locations: List[str] = []
    gov_entities: List[str] = []
    tactics: List[str] = []

    has_ficn    = False
    ficn_batch  = None
    has_video   = False
    has_finance = False
    scam_type   = "Unknown"
    multi_city  = False
    multi_src   = False

    # --- Agent 1 ---
    if a1 and a1.get("verdict") == "fake":
        has_ficn   = True
        ficn_batch = a1.get("batch_id")
        if a1.get("location"):
            locations.append(a1["location"].lower())

    # --- Agent 2 ---
    if a2 and a2.get("available"):
        platforms.extend([s.lower() for s in (a2.get("sources") or [])])
        platforms.extend([p.lower() for p in (a2.get("platforms") or [])])
        locations.extend([l.lower() for l in (a2.get("locations") or [])])
        multi_src = bool(a2.get("is_multi_source"))
        if a2.get("scam_type"):
            scam_type = a2["scam_type"].replace("_", " ").title()

    # --- Agent 3 ---
    if a3 and a3.get("available"):
        gov_entities = [e for e in (a3.get("government_entities") or []) if e]
        tactics      = [t for t in (a3.get("psychological_tactics") or []) if t]
        has_finance  = bool(a3.get("financial_request"))
        has_video    = any("video" in t.lower() for t in tactics)
        if a3.get("scam_type") and a3["scam_type"] != "Unknown":
            scam_type = a3["scam_type"]

    # Deduplicate
    platforms  = list(dict.fromkeys(platforms))
    locations  = list(dict.fromkeys(locations))
    gov_entities = list(dict.fromkeys(gov_entities))
    multi_city = len(set(locations)) >= 2

    return {
        "platforms":   platforms,
        "locations":   locations,
        "gov_entities": gov_entities,
        "tactics":     tactics,
        "has_ficn":    has_ficn,
        "ficn_batch":  ficn_batch,
        "has_video":   has_video,
        "has_finance": has_finance,
        "scam_type":   scam_type,
        "multi_city":  multi_city,
        "multi_src":   multi_src,
    }


# ---------------------------------------------------------------------------
# Operator count estimation
# ---------------------------------------------------------------------------

def _estimate_operators(signals: Dict) -> tuple:
    count = _OP_BASE
    count += len(set(signals["platforms"])) * _OP_PER_PLATFORM
    if signals["has_ficn"]:
        count += _OP_PER_CURRENCY_BATCH
    if signals["multi_city"]:
        count += _OP_IF_MULTI_CITY
    if signals["multi_src"]:
        count += _OP_IF_MULTI_SOURCE
    if signals["has_video"]:
        count += _OP_IF_VIDEO_CALL
    if signals["has_finance"]:
        count += _OP_IF_FINANCIAL_REQUEST

    return max(count - 1, 2), count + 2   # low = min-1, high = estimate+2


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _build_graph(signals: Dict, op_min: int, op_max: int):
    """
    Build a NetworkX directed graph representing the criminal network.
    Returns (graph, key_node_name).
    """
    if not _NX_AVAILABLE or nx is None:
        return _DummyGraph(), "ScamOperation"

    G = nx.DiGraph()

    # Central node
    G.add_node("ScamOperation", type="operation", confidence=1.0)

    # Platform nodes
    for platform in signals["platforms"][:5]:  # cap at 5 for clarity
        pnode = f"Platform_{platform.replace(' ', '_')}"
        G.add_node(pnode, type="platform", confidence=0.9)
        G.add_edge("ScamOperation", pnode, relation="coordinates_via", weight=0.9)

    # Geographic nodes
    for loc in signals["locations"][:4]:
        gnode = f"Zone_{loc.replace(' ', '_').title()}"
        G.add_node(gnode, type="geography", confidence=0.85)
        G.add_edge("ScamOperation", gnode, relation="operates_in", weight=0.85)

    # FICN node
    if signals["has_ficn"]:
        batch_label = signals["ficn_batch"] or "ficn_batch_unknown"
        fnode = f"FICN_{batch_label}"
        G.add_node(fnode, type="physical_vector", confidence=0.88)
        G.add_edge("ScamOperation", fnode, relation="distributes", weight=0.88)

    # Government impersonation nodes
    for entity in signals["gov_entities"][:3]:
        enode = f"Impersonates_{entity.replace(' ', '_')}"
        G.add_node(enode, type="impersonation_target", confidence=0.92)
        G.add_edge("ScamOperation", enode, relation="impersonates", weight=0.92)

    # Estimated operator nodes (anonymous)
    for i in range(1, min(op_min + 1, 5)):
        onode = f"Operator_{i:02d}"
        G.add_node(onode, type="criminal_actor", confidence=0.60)
        G.add_edge(onode, "ScamOperation", relation="runs", weight=0.60)

    # Find key node (highest out-degree)
    key_node = "ScamOperation"
    if G.number_of_nodes() > 1:
        degrees = dict(G.degree())
        key_node = max(degrees, key=lambda k: degrees.get(k, 0))

    return G, key_node


class _DummyGraph:
    """Fallback when networkx is unavailable."""
    def number_of_nodes(self): return 0
    def number_of_edges(self): return 0


# ---------------------------------------------------------------------------
# Derived fields
# ---------------------------------------------------------------------------

def _modus_operandi(signals: Dict) -> str:
    parts = []
    if signals["scam_type"] != "Unknown":
        parts.append(signals["scam_type"])
    if signals["has_ficn"]:
        parts.append("counterfeit currency distribution")
    if signals["has_video"]:
        parts.append("video call intimidation")
    if signals["multi_src"]:
        parts.append("multi-platform social engineering")
    return " + ".join(parts) if parts else "Unknown"


def _digital_infrastructure(signals: Dict) -> List[str]:
    infra = []
    if signals["has_video"]:
        infra.append("video_call_spoofing")
    if any("telephone" in p or "ivr" in p for p in signals["platforms"]):
        infra.append("ivr_robocall")
    if signals["gov_entities"]:
        infra.append("spoofed_government_numbers")
    infra.append("voip_caller_id_spoofing")
    return list(set(infra))


def _monthly_victim_estimate(signals: Dict) -> str:
    base = 200
    if signals["multi_src"]:
        base *= 2
    if signals["has_ficn"]:
        base = int(base * 1.3)
    if signals["multi_city"]:
        base = int(base * 1.5)
    return f"{base}–{base * 3}"


def _confidence_score(signals: Dict, corr) -> float:
    score = 0.40  # base
    if signals["has_ficn"]:         score += 0.10
    if signals["gov_entities"]:     score += 0.12
    if signals["multi_src"]:        score += 0.10
    if corr and corr.get("scam_type_match"): score += 0.10
    if corr and corr.get("geo_overlap"):     score += 0.08
    if corr and corr.get("temporal_spike"):  score += 0.05
    return round(min(score, 0.95), 2)


def _evidence_strength(signals: Dict, corr) -> str:
    n_signals = sum([
        bool(signals["has_ficn"]),
        bool(signals["gov_entities"]),
        bool(signals["multi_src"]),
        bool(corr and corr.get("scam_type_match")),
        bool(corr and corr.get("geo_overlap")),
    ])
    if n_signals >= 4:
        return "strong"
    elif n_signals >= 2:
        return "medium"
    return "low"
