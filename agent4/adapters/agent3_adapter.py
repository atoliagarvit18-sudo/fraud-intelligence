"""
agent4/adapters/agent3_adapter.py

Wraps Agent 3 (Scam Call Intelligence) for the orchestrator.

Priority order (live-first, mock ONLY on failure):
  1. Live: run full Whisper + NLP + LLM pipeline using agent3/src modules
           (transcriber → analyzer → semantic_analyzer → llm_analyzer →
            voice_analyzer → decision_engine)
  2. Precomputed JSON: load from agent3/src/output/transcript.json
     if it exists from a previous live run (fast re-use, still real output)
  3. Mock (FALLBACK ONLY): if Whisper import fails or no audio file exists

The GROQ_API_KEY must be in agent3/.env for the LLM step.
The Whisper model is loaded lazily on first call.
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import sys

print("=" * 60)
print("Python executable:", sys.executable)
print("Python version:", sys.version)
print("=" * 60)
# ---------------------------------------------------------------------------
# Path setup — agent3/src must be on sys.path for its module imports to work
# ---------------------------------------------------------------------------
_AGENT4_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AGENT3_SRC = os.path.normpath(os.path.join(_AGENT4_DIR, "..", "agent3", "src"))
_AGENT3_DIR = os.path.normpath(os.path.join(_AGENT4_DIR, "..", "agent3"))

for _p in [_AGENT3_SRC, _AGENT3_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Also load agent3's .env so GROQ_API_KEY is available
_AGENT3_ENV = os.path.join(_AGENT3_DIR, ".env")
if os.path.exists(_AGENT3_ENV):
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(dotenv_path=_AGENT3_ENV, override=False)
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(
    audio_path: Optional[str] = None,
    transcript: Optional[str] = None,
    precomputed_json: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run Agent 3 live pipeline on a scam call audio file.

    Priority:
      1. Live Whisper + NLP + LLM pipeline on audio_path
      2. Load precomputed JSON (real previous output — not mock)
      3. Mock ONLY if audio missing AND no precomputed output

    Args:
        audio_path:       Path to .mp3 / .wav audio file.
        precomputed_json: Optional path to agent3/src/output/transcript.json
                          (auto-discovered if not given).

    Returns:
        dict matching Agent3Result schema — never raises.
    """
    if transcript and transcript.strip():
        print("  [LIVE] Using provided transcript")
        result = _run_from_transcript(transcript)
        if result.get("available"):
            return result

    # --- Step 1: Try live pipeline if audio exists ---
    if audio_path:
        if not os.path.exists(audio_path):
            resolved = os.path.normpath(os.path.join(_AGENT4_DIR, "..", audio_path))
            if os.path.exists(resolved):
                audio_path = resolved
        if os.path.exists(audio_path):
            result = _run_live(audio_path, transcript)
            if result.get("available"):
                return result
            # Live failed — report why and try next option
            print(f"  [!] Agent 3 live pipeline failed: {result.get('error')}")
            print(f"  [!] Attempting precomputed fallback...")

    # --- Step 2: Try precomputed transcript.json ---
    precomputed_path = precomputed_json or _find_precomputed()
    if precomputed_path and os.path.exists(precomputed_path):
        result = _load_precomputed(precomputed_path)
        if result.get("available"):
            print(f"  [OK] Loaded precomputed Agent 3 output from: {precomputed_path}")
            return result

    # --- Step 3: Mock fallback (last resort) ---
    if not audio_path or not os.path.exists(audio_path):
        reason = "audio file not found"
    else:
        reason = "live pipeline dependencies/model unavailable & no precomputed JSON"
    print(f"  [!] Agent 3 using mock fallback ({reason})")
    return mock_result()

def _run_from_transcript(transcript):

    from analyzer import analyze_transcript
    from semantic_analyzer import semantic_analysis
    from llm_analyzer import analyze_with_llm
    from decision_engine import make_final_decision


    keyword_result = analyze_transcript(transcript)

    semantic_result = semantic_analysis(transcript)

    llm_result = analyze_with_llm(transcript)


    overall = make_final_decision(
        keyword_result,
        semantic_result,
        llm_result
    )


    return _normalise_live(
        "provided_transcript",
        transcript,
        "provided",
        keyword_result,
        semantic_result,
        llm_result,
        {},
        overall
    )

def _run_live(audio_path: str, transcript: Optional[str] = None) -> Dict[str, Any]:
    """Import Agent 3 modules and run the full analysis pipeline."""
    # Agent 3 transcriber.py loads Whisper at module import time
    # so we must handle that import carefully
    try:
        from transcriber import transcribe_audio          # type: ignore
    except ImportError as e:
        return {"available": False, "error": f"Whisper/transcriber import failed: {e}"}
    except Exception as e:
        return {"available": False, "error": f"Whisper model load failed: {e}"}

    try:
        from analyzer import analyze_transcript           # type: ignore
        from semantic_analyzer import semantic_analysis   # type: ignore
        from llm_analyzer import analyze_with_llm         # type: ignore
        from voice_analyzer import analyze_voice          # type: ignore
        from decision_engine import make_final_decision   # type: ignore
    except ImportError as e:
        return {"available": False, "error": f"Agent 3 module import failed: {e}"}

    try:
        # Step 1
        # If frontend already supplied transcript,
        # don't run Whisper again.

        if transcript and transcript.strip():
            language = "unknown"
        else:
            transcription = transcribe_audio(audio_path)
            transcript = transcription["text"]
            language = transcription.get("language", "unknown")
            
        # Step 2: Three-layer analysis
        keyword_result  = analyze_transcript(transcript)
        semantic_result = semantic_analysis(transcript)
        llm_result      = analyze_with_llm(transcript)

        # Step 3: Voice features
        voice_result    = analyze_voice(audio_path)

        # Step 4: Ensemble decision
        overall         = make_final_decision(keyword_result, semantic_result, llm_result)

    except Exception as e:
        return {"available": False, "error": f"Agent 3 pipeline error: {e}"}

    return _normalise_live(
        audio_path, transcript, language,
        keyword_result, semantic_result, llm_result,
        voice_result, overall,
    )


def _normalise_live(
    audio_path, transcript, language,
    keyword_result, semantic_result, llm_result,
    voice_result, overall,
) -> Dict[str, Any]:
    """Flatten Agent 3 pipeline outputs into Agent4 schema shape."""
    llm = llm_result or {}
    ov  = overall   or {}

    return {
        "available":            True,
        "audio_file":           os.path.basename(audio_path),
        "transcript":           transcript,
        "language":             language,
        "scam_type":            ov.get("final_prediction") or llm.get("scam_type", "Unknown"),
        "risk_score":           ov.get("final_risk_score") or llm.get("risk_score", 0),
        "confidence":           ov.get("confidence") or llm.get("confidence", 0.0),
        "psychological_tactics": llm.get("psychological_tactics", []),
        "government_entities":  llm.get("government_entities", []),
        "financial_request":    llm.get("financial_request", False),
        "summary":              llm.get("summary", ""),
        "voice_analysis":       voice_result,
        "keyword_analysis":     keyword_result,
        "semantic_analysis":    semantic_result,
        "llm_analysis":         llm_result,
        "overall_analysis":     overall,
        "error":                None,
        "_source":              "live_pipeline",
        "_mock":                False,
    }


def _load_precomputed(json_path: str) -> Dict[str, Any]:
    """Load a real Agent 3 output JSON (from a previous live run)."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        llm = data.get("llm_analysis")  or {}
        ov  = data.get("overall_analysis") or {}

        return {
            "available":            True,
            "audio_file":           data.get("audio_file", os.path.basename(json_path)),
            "transcript":           data.get("transcript", ""),
            "language":             data.get("language", "unknown"),
            "scam_type":            ov.get("final_prediction") or llm.get("scam_type", "Unknown"),
            "risk_score":           ov.get("final_risk_score") or llm.get("risk_score", 0),
            "confidence":           ov.get("confidence") or llm.get("confidence", 0.0),
            "psychological_tactics": llm.get("psychological_tactics", []),
            "government_entities":  llm.get("government_entities", []),
            "financial_request":    llm.get("financial_request", False),
            "summary":              llm.get("summary", ""),
            "voice_analysis":       data.get("voice_analysis"),
            "keyword_analysis":     data.get("keyword_analysis"),
            "semantic_analysis":    data.get("semantic_analysis"),
            "llm_analysis":         llm,
            "overall_analysis":     ov,
            "error":                None,
            "_source":              f"precomputed:{json_path}",
            "_mock":                False,
        }
    except Exception as e:
        return {"available": False, "error": f"Precomputed JSON load failed: {e}"}


def _find_precomputed() -> Optional[str]:
    """
    Auto-discover a previously saved Agent 3 transcript.json.
    Checks agent3/src/output/transcript.json (the path Agent 3 writes to).
    """
    candidate = os.path.join(_AGENT3_SRC, "output", "transcript.json")
    if os.path.exists(candidate):
        return candidate
    return None


def mock_result() -> Dict[str, Any]:
    """
    Emergency fallback result — used ONLY when:
      - No audio file exists, AND
      - No precomputed transcript.json exists, AND
      - Live pipeline cannot run (missing deps / API key)

    Contains a realistic Digital Arrest scam call analysis.
    """
    return {
        "available":   True,
        "audio_file":  "demo_scam_call.mp3",
        "transcript": (
            "Hello sir, I am calling from Cyber Crime Department of CBI. "
            "Your Aadhaar card has been linked to 47 illegal bank accounts used "
            "in money laundering. This is a serious criminal offence. You must "
            "stay on the call. Connect with the Enforcement Directorate officer "
            "immediately. Press one now. Do not disconnect or you will be "
            "arrested within 2 hours."
        ),
        "language":    "english",
        "scam_type":   "Digital Arrest",
        "risk_score":  87,
        "confidence":  0.91,
        "psychological_tactics": [
            "authority impersonation",
            "urgency and time pressure",
            "fear of arrest",
            "isolation",
        ],
        "government_entities":   ["CBI", "Enforcement Directorate", "Cyber Crime Department"],
        "financial_request":     False,
        "summary": (
            "Caller impersonates CBI and Enforcement Directorate, falsely claiming "
            "the target's Aadhaar is linked to money laundering. Uses fear of "
            "imminent arrest to keep victim on the call."
        ),
        "voice_analysis": {
            "duration_seconds": 38.4,
            "sample_rate":      16000,
            "average_energy":   0.062,
            "zero_crossing_rate": 0.089,
            "audio_quality":    "Good",
        },
        "overall_analysis": {
            "final_prediction": "Digital Arrest",
            "agreement":        "3/3",
            "final_risk_score": 87,
            "risk_level":       "High",
            "confidence":       0.91,
        },
        "error":   None,
        "_source": "mock_fallback",
        "_mock":   True,
    }
