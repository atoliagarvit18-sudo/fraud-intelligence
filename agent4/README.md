# Agent 4 — Fraud Campaign Intelligence Orchestrator

**ET AI Hackathon 2.0 | Problem Statement 6**
_AI for Digital Public Safety: Defeating Counterfeiting, Fraud & Digital Arrest Scams_

---

## What Agent 4 Does

Agent 4 is the **Predictive Threat Neutralisation Engine** — the orchestrating brain that unifies the three specialist agents into a single, actionable intelligence package.

It adds **four capabilities** that no individual agent has:

| Capability | What it Does | Why it Wins |
|---|---|---|
| **Cross-Agent Correlation** | Links scam type + geography + timing across agents | Proves coordinated, multi-vector attack |
| **Criminal Network Hypothesis** | Builds a NetworkX graph of inferred criminal infrastructure | Law-enforcement-grade cell profiling |
| **Predictive Victimisation Engine** | Projects 24h/48h victim count if campaign isn't disrupted | Evaluation criterion: "lead time before mass victimisation" |
| **Legal Evidence Package** | SHA-256 hashed bundle + NCRB complaint draft + RBI FICN alert | Evaluation criterion: "legal admissibility" |

---

## Quick Start

### Install dependencies

```bash
cd agent4
pip install -r requirements.txt
```

> **Note:** Agent 4 itself has minimal dependencies. For live agent runs, you also need the dependencies from `agent1/`, `agent2/`, and `agent3/`.

### Run the demo (recommended — works offline)

```bash
python demo/demo_runner.py
```

This runs the full pipeline in **mock mode** for Agent 2 and **mock mode** for Agent 3 (no Whisper needed). Agent 1 will attempt to run on the committed sample images.

### Run with live Agent 3 (Whisper + Groq)

```bash
python demo/demo_runner.py --audio ../agent3/audio/sample.mp3
```

### Run with live MongoDB (Agent 2)

```bash
python demo/demo_runner.py --agent2-mongodb
```

### Full custom run

```bash
python demo/demo_runner.py \
  --image  ../agent1/sample_data/500_fake_001.jpg \
  --denom  500 \
  --location "Jaipur Branch A" \
  --audio  ../agent3/audio/sample.mp3
```

### Use orchestrator programmatically

```python
from agent4.orchestrator import run
from agent4.schemas import OrchestratorInput

report = run(OrchestratorInput(
    currency_image_path="path/to/note.jpg",
    currency_location="Jaipur Branch A",
    audio_path="path/to/call.mp3",
    agent2_source="mock",   # or 'mongodb' or 'json'
))

print(report["composite_risk_score"])   # e.g. 92
print(report["severity"])               # CRITICAL
print(report["narrative"])              # Human-readable threat story
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   AGENT 4 ORCHESTRATOR                   │
│                                                          │
│  Agent 1       Agent 2        Agent 3                    │
│  (Currency)    (OSINT)        (Scam Call)                │
│     ↓              ↓               ↓                     │
│  ┌───────────────────────────────────────┐               │
│  │       Cross-Agent Correlator          │               │
│  │  • Scam type match                    │               │
│  │  • Geographic overlap                 │               │
│  │  • Temporal spike                     │               │
│  │  • Infrastructure link                │               │
│  └─────────────────┬─────────────────────┘               │
│                    │                                     │
│          ┌─────────┼─────────┐                          │
│          ↓         ↓         ↓                          │
│  Criminal Net  Victimisation  Evidence                   │
│  Hypothesis    Prediction     Package                    │
│          ↓         ↓         ↓                          │
│          └─────────┴─────────┘                          │
│                    ↓                                     │
│           Synthesizer (score + narrative)                │
│                    ↓                                     │
│       Unified Threat Intelligence Report                 │
└──────────────────────────────────────────────────────────┘
```

---

## Output Schema (key fields)

```json
{
  "agent": "Agent4_FraudCampaignOrchestrator",
  "report_id": "FCIS-20260718-094523-A3F21B",
  "composite_risk_score": 92,
  "severity": "CRITICAL",
  "unified_scam_type": "Digital Arrest",
  "agents_active": 3,

  "correlation": {
    "scam_type_match": true,
    "geo_overlap": true,
    "temporal_spike": true,
    "infrastructure_link": true,
    "correlation_score": 0.95,
    "signals_matched": 4,
    "correlation_evidence": ["..."]
  },

  "criminal_network": {
    "cell_id": "CELL-JAI-2026-DA1",
    "estimated_operators": "4–8",
    "operational_geography": ["Jaipur", "Jodhpur"],
    "modus_operandi": "Digital Arrest + counterfeit currency distribution",
    "confidence": 0.82,
    "evidence_strength": "strong"
  },

  "victimisation_prediction": {
    "estimated_victims_24h_low": 340,
    "estimated_victims_24h_high": 850,
    "urgency_level": "IMMEDIATE"
  },

  "evidence_package": {
    "package_id": "EVP-20260718-A3C9F1",
    "integrity_verified": true,
    "evidence_count": 4,
    "ncrb_complaint_draft": { "...": "..." }
  },

  "narrative": "A coordinated Digital Arrest fraud campaign is ACTIVELY operating in Jaipur, Rajasthan...",
  "recommended_actions": ["Hang up immediately...", "Call 1930...", "..."],
  "threat_neutralisation_playbook": ["Escalate to State Cyber Crime Unit...", "..."]
}
```

---

## File Guide

| File | Purpose |
|---|---|
| `orchestrator.py` | Main entry point — call `run(OrchestratorInput(...))` |
| `correlator.py` | 4-signal cross-agent correlation engine |
| `predictor.py` | Predictive victimisation modelling |
| `network_graph.py` | Criminal cell hypothesis builder (NetworkX) |
| `evidence_package.py` | SHA-256 evidence bundler + NCRB/RBI drafts |
| `synthesizer.py` | Composite scoring, narrative, actions |
| `schemas.py` | All Pydantic input/output models |
| `adapters/agent1_adapter.py` | Wraps Agent 1 currency pipeline |
| `adapters/agent2_adapter.py` | Agent 2: MongoDB / JSON / mock modes |
| `adapters/agent3_adapter.py` | Wraps Agent 3 call analysis pipeline |
| `demo/demo_runner.py` | **Hackathon demo — run this** |
| `demo/demo_scenario.json` | Pre-staged inputs for demo day |

---

## Evaluation Criteria Mapping

| Criterion (25%) | How Agent 4 Addresses It |
|---|---|
| **Innovation** | Criminal network hypothesis + predictive victimisation — not seen in any prior fraud detection system |
| **Business Impact** | Shifts law enforcement from reactive case investigation to pre-emptive campaign disruption |
| **Technical Excellence** | Multi-signal correlator, NetworkX graph, SHA-256 integrity, probabilistic victimisation model |
| **Scalability** | Stateless orchestrator — horizontally scalable; Agent 2 already has MongoDB + APScheduler |
| **User Experience** | One command → full colour intelligence report in <20 seconds |
