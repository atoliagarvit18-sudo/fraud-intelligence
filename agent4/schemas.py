"""
agent4/schemas.py

Pydantic data models for all Agent 4 inputs and outputs.
Defines strict contracts between adapters, engines, and the orchestrator.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Agent input schemas (normalised outputs from agents 1-3)
# ---------------------------------------------------------------------------

class Agent1Result(BaseModel):
    """Normalised output from Agent 1 — Currency Intelligence."""
    available: bool = False
    image_path: Optional[str] = None
    status: Optional[str] = None
    denomination: Optional[str] = None
    verdict: Optional[str] = None          # 'genuine' | 'fake' | None
    confidence: Optional[float] = None
    batch_id: Optional[str] = None
    is_new_batch: Optional[bool] = None
    location: Optional[str] = None
    timestamp: Optional[str] = None
    denomination_auto_detected: Optional[bool] = None
    error: Optional[str] = None


class Agent2Result(BaseModel):
    """Normalised output from Agent 2 — OSINT Campaign Intelligence."""
    available: bool = False
    active_events: List[Dict[str, Any]] = []
    top_cluster: Optional[Dict[str, Any]] = None
    severity: Optional[str] = None         # low/medium/high/critical
    scam_type: Optional[str] = None
    campaign_score: Optional[float] = None
    weighted_confidence: Optional[float] = None
    post_count: Optional[int] = None
    sources: List[str] = []
    platforms: List[str] = []
    locations: List[str] = []              # entity-extracted locations from posts
    is_multi_source: Optional[bool] = None
    temporal_data: Optional[Dict[str, Any]] = None
    cluster_id: Optional[int] = None
    error: Optional[str] = None


class Agent3Result(BaseModel):
    """Normalised output from Agent 3 — Scam Call Intelligence."""
    available: bool = False
    audio_file: Optional[str] = None
    transcript: Optional[str] = None
    language: Optional[str] = None
    scam_type: Optional[str] = None
    risk_score: Optional[int] = None       # 0-100
    confidence: Optional[float] = None     # 0-1
    psychological_tactics: List[str] = []
    government_entities: List[str] = []
    financial_request: Optional[bool] = None
    summary: Optional[str] = None
    voice_analysis: Optional[Dict[str, Any]] = None
    keyword_analysis: Optional[Dict[str, Any]] = None
    semantic_analysis: Optional[Dict[str, Any]] = None
    llm_analysis: Optional[Dict[str, Any]] = None
    overall_analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Agent 4 intermediate results
# ---------------------------------------------------------------------------

class CorrelationResult(BaseModel):
    """Output of the cross-agent correlation engine."""
    scam_type_match: bool = False
    geo_overlap: bool = False
    temporal_spike: bool = False
    infrastructure_link: bool = False
    correlation_score: float = 0.0
    signals_matched: int = 0
    signals_total: int = 4
    correlation_evidence: List[str] = []
    unified_scam_type: str = "Unknown"
    linked_campaign_id: Optional[str] = None


class CriminalNetworkHypothesis(BaseModel):
    """
    Inferred criminal network structure from multi-agent intelligence.
    This is a HYPOTHESIS for law enforcement guidance, not a legal assertion.
    """
    cell_id: str
    estimated_operators: str               # e.g., '3-7'
    operational_geography: List[str]
    infrastructure: Dict[str, List[str]]   # category → list of items
    modus_operandi: str
    impersonation_targets: List[str]
    coordination_channels: List[str]
    estimated_monthly_victims: str         # range as string
    confidence: float
    evidence_strength: str                 # 'low' | 'medium' | 'strong'
    graph_nodes: int
    graph_edges: int
    key_infrastructure_node: Optional[str] = None
    disclaimer: str = (
        "This is an AI-generated hypothesis for investigative guidance only. "
        "It must be verified by a qualified cybercrime investigator before any enforcement action."
    )


class VictimisationPrediction(BaseModel):
    """
    Predictive estimate of future victims if campaign is not disrupted.
    Addresses the evaluation criterion: 'fraud network detection lead time before mass victimisation'.
    """
    prediction_window_hours: int = 24
    estimated_victims_24h_low: int
    estimated_victims_24h_high: int
    estimated_victims_48h_low: int
    estimated_victims_48h_high: int
    campaign_growth_rate: str              # 'accelerating' | 'stable' | 'declining' | 'unknown'
    posts_per_hour: Optional[float] = None
    hours_to_peak_activity: Optional[int] = None
    urgency_level: str                     # 'IMMEDIATE' | 'URGENT' | 'MONITOR' | 'LOW'
    prediction_basis: str
    methodology_note: str = (
        "Projection based on campaign velocity from Agent 2 OSINT, "
        "scaled by RBI/NCRB 2023-24 per-campaign victimisation rate estimates. "
        "This is a probabilistic estimate, not a deterministic forecast."
    )


class EvidenceItem(BaseModel):
    """A single piece of evidence in the legal package."""
    evidence_id: str
    evidence_type: str                     # 'audio_transcript' | 'currency_scan' | 'osint_campaign'
    source_agent: str
    collection_timestamp: str
    content_hash_sha256: str
    content_summary: str
    source_urls: List[str] = []
    admissibility_status: str = "AI-generated — requires human verification"


class LegalEvidencePackage(BaseModel):
    """
    Court-ready evidence bundle with chain-of-custody metadata.
    Addresses the evaluation criterion: 'auditability of intelligence packages for legal admissibility'.
    """
    package_id: str
    created_at: str
    system_version: str = "Fraud Campaign Intelligence System v1.0"
    integrity_verified: bool = True
    evidence_items: List[Dict[str, Any]] = []
    chain_of_custody: Dict[str, Any] = {}
    ncrb_complaint_draft: Dict[str, Any] = {}
    rbi_alert_draft: Optional[Dict[str, Any]] = None
    cybercrime_helpline: str = "1930"
    submission_portal: str = "cybercrime.gov.in"
    legal_disclaimer: str = (
        "This evidence package was generated by an automated AI system. "
        "All items should be reviewed by a qualified cybercrime investigator or "
        "forensic analyst before submission to any court or regulatory authority. "
        "The SHA-256 hashes provide integrity verification of the AI-generated data "
        "from the point of package creation."
    )


# ---------------------------------------------------------------------------
# Orchestrator input
# ---------------------------------------------------------------------------

class OrchestratorInput(BaseModel):
    """Input parameters for the Agent 4 orchestrator."""
    # Agent 1 inputs
    currency_image_path: Optional[str] = Field(
        default=None,
        description="Path to currency note image for Agent 1 analysis"
    )
    currency_denom_hint: Optional[str] = Field(
        default=None,
        description="Denomination hint (e.g. '500'). If None, auto-detected."
    )
    currency_location: Optional[str] = Field(
        default=None,
        description="Geographic location where the note was detected"
    )

    # Agent 3 inputs
    audio_path: Optional[str] = Field(
        default=None,
        description="Path to scam call audio file for Agent 3 analysis"
    )

    # Agent 2 source mode & manual query inputs
    agent2_source: str = Field(
        default="mongodb",
        description="'mongodb' (default/live) | 'json' | 'mock'"
    )
    agent2_json_path: Optional[str] = Field(
        default=None,
        description="Path to Agent 2 events JSON file (for 'json' mode)"
    )
    text: Optional[str] = Field(
        default=None,
        description="Raw text evidence or OSINT query message"
    )
    phone: Optional[str] = Field(
        default=None,
        description="Phone number evidence"
    )
    url: Optional[str] = Field(
        default=None,
        description="Website URL evidence"
    )

    # Pre-computed agent outputs (for offline/demo mode)
    agent1_precomputed: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Pre-computed Agent 1 result dict (skips live Agent 1 run)"
    )
    agent2_precomputed: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Pre-computed Agent 2 result dict"
    )
    agent3_precomputed: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Pre-computed Agent 3 result dict"
    )


# ---------------------------------------------------------------------------
# Final unified output
# ---------------------------------------------------------------------------

class ThreatIntelligenceReport(BaseModel):
    """
    The complete Agent 4 output — a unified threat intelligence package
    covering detection, correlation, prediction, network analysis, and
    legal evidence bundling.
    """
    agent: str = "Agent4_FraudCampaignOrchestrator"
    system_name: str = "Fraud Campaign Intelligence System"
    report_id: str
    timestamp: str

    # Agents that contributed to this report
    triggered_by: List[str]
    agents_active: int

    # --- Core verdict ---
    composite_risk_score: int              # 0-100
    severity: str                          # LOW/MEDIUM/HIGH/CRITICAL
    unified_scam_type: str

    # --- Raw agent outputs ---
    agent1_currency: Optional[Dict[str, Any]] = None
    agent2_campaign: Optional[Dict[str, Any]] = None
    agent3_call: Optional[Dict[str, Any]] = None

    # --- Agent 4 unique capabilities ---
    correlation: Dict[str, Any]
    criminal_network: Optional[Dict[str, Any]] = None
    victimisation_prediction: Optional[Dict[str, Any]] = None
    evidence_package: Optional[Dict[str, Any]] = None

    # --- Human-readable outputs ---
    narrative: str
    recommended_actions: List[str]
    threat_neutralisation_playbook: List[str]

    # --- System metadata ---
    system: Dict[str, Any]
