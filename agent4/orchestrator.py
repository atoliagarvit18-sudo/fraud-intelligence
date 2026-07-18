"""
agent4/orchestrator.py

Agent 4 — Fraud Campaign Intelligence Orchestrator.

The central engine of the multi-agent system. Coordinates all three sub-agents,
runs cross-agent correlation, criminal network analysis, predictive victimisation
modelling, and legal evidence packaging, then synthesises everything into a
single Unified Threat Intelligence Report.

Usage:
    from orchestrator import run

    report = run(OrchestratorInput(
        currency_image_path="path/to/note.jpg",
        currency_location="Jaipur Branch A",
        audio_path="path/to/call.mp3",
        agent2_source="mock",
    ))

The orchestrator degrades gracefully — it produces a report even if only one
agent fires. The more agents that contribute, the higher the composite score
and the richer the correlation analysis.
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
_AGENT4_DIR = os.path.dirname(os.path.abspath(__file__))
if _AGENT4_DIR not in sys.path:
    sys.path.insert(0, _AGENT4_DIR)

from schemas import OrchestratorInput, ThreatIntelligenceReport

from adapters import agent1_adapter, agent2_adapter, agent3_adapter
import correlator
import predictor
import network_graph
import evidence_package
import synthesizer


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(inputs: OrchestratorInput) -> Dict[str, Any]:
    """
    Run the full Agent 4 orchestration pipeline.

    Args:
        inputs: OrchestratorInput model with paths and mode settings.

    Returns:
        dict — a fully populated ThreatIntelligenceReport.
    """
    start_time = time.time()
    report_id  = f"FCIS-{datetime.now(tz=timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    timestamp  = datetime.now(tz=timezone.utc).isoformat()

    # -----------------------------------------------------------------------
    # Step 1 — Run all three sub-agents (or load precomputed)
    # -----------------------------------------------------------------------
    a1 = _get_agent1(inputs)
    a2 = _get_agent2(inputs)
    a3 = _get_agent3(inputs)

    # -----------------------------------------------------------------------
    # Step 2 — Cross-agent correlation
    # -----------------------------------------------------------------------
    corr = correlator.correlate(a1, a2, a3)

    # -----------------------------------------------------------------------
    # Step 3 — Criminal network hypothesis
    # -----------------------------------------------------------------------
    net = network_graph.build(a1, a2, a3, corr)

    # -----------------------------------------------------------------------
    # Step 4 — Predictive victimisation modelling
    # -----------------------------------------------------------------------
    pred = predictor.predict(a2, a3, corr.get("correlation_score", 0.0))

    # -----------------------------------------------------------------------
    # Step 5 — Synthesis (composite score, narrative, actions)
    # -----------------------------------------------------------------------
    synthesis = synthesizer.synthesize(a1, a2, a3, corr, net, pred, None)

    # -----------------------------------------------------------------------
    # Step 6 — Legal evidence package
    # -----------------------------------------------------------------------
    evp = evidence_package.generate(
        agent1=a1,
        agent2=a2,
        agent3=a3,
        correlation=corr,
        report_id=report_id,
        composite_score=synthesis["composite_risk_score"],
        severity=synthesis["severity"],
        scam_type=synthesis["unified_scam_type"],
    )

    processing_time = round(time.time() - start_time, 2)

    # -----------------------------------------------------------------------
    # Step 7 — Assemble final report
    # -----------------------------------------------------------------------
    report = {
        "agent":       "Agent4_FraudCampaignOrchestrator",
        "system_name": "Fraud Campaign Intelligence System",
        "report_id":   report_id,
        "timestamp":   timestamp,

        # Core verdict
        "composite_risk_score": synthesis["composite_risk_score"],
        "severity":             synthesis["severity"],
        "unified_scam_type":    synthesis["unified_scam_type"],
        "triggered_by":         synthesis["triggered_by"],
        "agents_active":        synthesis["agents_active"],

        # Raw agent outputs
        "agent1_currency":  a1,
        "agent2_campaign":  a2,
        "agent3_call":      a3,

        # Agent 4 unique capabilities
        "correlation":              corr,
        "criminal_network":         net,
        "victimisation_prediction": pred,
        "evidence_package":         evp,

        # Human-readable outputs
        "narrative":                    synthesis["narrative"],
        "recommended_actions":          synthesis["recommended_actions"],
        "threat_neutralisation_playbook": synthesis["threat_neutralisation_playbook"],

        # System metadata
        "system": {
            "version":                "1.0.0",
            "processing_time_seconds": processing_time,
            "agents_attempted":        3,
            "agents_active":          synthesis["agents_active"],
            "correlation_engine":     "4-signal cross-agent correlator",
            "prediction_engine":      "campaign-velocity victimisation projector",
            "network_engine":         "networkx criminal cell hypothesis builder",
            "evidence_engine":        "SHA-256 legal evidence packager",
            "models_used":            _models_used(a1, a2, a3),
        },
    }

    return report


def run_from_dict(input_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience wrapper: accepts a plain dict instead of OrchestratorInput."""
    return run(OrchestratorInput(**input_dict))


def save_report(report: Dict[str, Any], output_dir: str = "output") -> str:
    """Save the report JSON to the output directory. Returns the file path."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"threat_report_{ts}.json"
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    return path


# ---------------------------------------------------------------------------
# Sub-agent runners with graceful degradation
# ---------------------------------------------------------------------------

def _get_agent1(inputs: OrchestratorInput) -> Optional[Dict[str, Any]]:
    if inputs.agent1_precomputed:
        result = dict(inputs.agent1_precomputed)
        result.setdefault("available", result.get("verdict") == "fake" or result.get("status") == "ok")
        return result

    if inputs.currency_image_path:
        return agent1_adapter.run(
            image_path=inputs.currency_image_path,
            denom_hint=inputs.currency_denom_hint,
            location=inputs.currency_location,
        )

    return {"available": False, "error": "No currency image path provided"}


def _get_agent2(inputs: OrchestratorInput) -> Optional[Dict[str, Any]]:
    if inputs.agent2_precomputed:
        result = dict(inputs.agent2_precomputed)
        result.setdefault("available", True)
        return result

    return agent2_adapter.run(
        source=inputs.agent2_source,
        json_path=inputs.agent2_json_path,
    )


def _get_agent3(inputs: OrchestratorInput) -> Optional[Dict[str, Any]]:
    if inputs.agent3_precomputed:
        result = dict(inputs.agent3_precomputed)
        result.setdefault("available", True)
        return result

    if inputs.audio_path:
        return agent3_adapter.run(audio_path=inputs.audio_path)

    # Fall back to mock for demo mode
    return agent3_adapter.mock_result()


def _models_used(a1, a2, a3) -> list:
    models = []
    if a1 and a1.get("available"):
        models.extend(["opencv-cv-pipeline", "sklearn-random-forest", "imagehash-phash"])
    if a2 and a2.get("available"):
        models.extend(["sentence-transformers/all-MiniLM-L6-v2", "sklearn-dbscan", "groq/llama-3.3-70b-versatile"])
    if a3 and a3.get("available"):
        models.extend(["openai-whisper-base", "sentence-transformers/all-MiniLM-L6-v2", "groq/llama-3.1-8b-instant"])
    return list(dict.fromkeys(models))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent 4 — Fraud Campaign Intelligence Orchestrator")
    parser.add_argument("--image",    help="Path to currency image (Agent 1)")
    parser.add_argument("--denom",    help="Denomination hint (e.g. 500)")
    parser.add_argument("--location", help="Currency detection location")
    parser.add_argument("--audio",    help="Path to scam call audio (Agent 3)")
    parser.add_argument("--a2-source", default="mock", choices=["mongodb", "json", "mock"])
    parser.add_argument("--a2-json",  help="Path to Agent 2 events JSON (for json mode)")
    parser.add_argument("--output",   default="output", help="Output directory")
    args = parser.parse_args()

    inputs = OrchestratorInput(
        currency_image_path=args.image,
        currency_denom_hint=args.denom,
        currency_location=args.location,
        audio_path=args.audio,
        agent2_source=args.a2_source,
        agent2_json_path=args.a2_json,
    )

    print("\nRunning Agent 4 orchestrator...")
    report = run(inputs)
    path   = save_report(report, args.output)

    print(f"\nReport saved to: {path}")
    print(f"Composite Risk Score: {report['composite_risk_score']}/100  |  Severity: {report['severity']}")
    print(f"Unified Scam Type:    {report['unified_scam_type']}")
    print(f"Agents Active:        {report['agents_active']}/3")
    print(f"\nNarrative:\n{report['narrative']}")
