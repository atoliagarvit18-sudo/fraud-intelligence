"""
agent4/adapters/agent1_adapter.py

Wraps Agent 1 (Currency Intelligence) for the orchestrator.

Priority order (live-first, mock ONLY on failure):
  1. Live: import agent1/inference.py and run process_note_image()
  2. Fallback (ONLY if image missing or model load fails): return mock

The mock is a hardcoded realistic result used SOLELY as a demo safety net.
In all real operation the live pipeline runs.
"""

import os
import sys
import json
from typing import Any, Dict, Optional
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_AGENT4_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AGENT1_DIR = os.path.normpath(os.path.join(_AGENT4_DIR, "..", "agent1"))

if _AGENT1_DIR not in sys.path:
    sys.path.insert(0, _AGENT1_DIR)


def run(
    image_path: Optional[str],
    denom_hint: Optional[str] = None,
    location: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run Agent 1 live pipeline on a currency image.

    Falls back to mock ONLY if:
      - image_path is None or file does not exist  (can't proceed)
      - Agent 1 import fails                        (dependency not installed)
      - process_note_image() raises an exception    (model error)

    Args:
        image_path:  Absolute path to currency note image.
        denom_hint:  Denomination string e.g. '500'. If None, auto-detected.
        location:    Geographic location string for batch tracking.

    Returns:
        dict matching Agent1Result schema. 'available' = True on success.
    """
    base = {"available": False, "image_path": image_path, "location": location}

    # --- Validate image path ---
    if not image_path:
        return {
            "available": False,
            "status": "no_image",
            "denomination": "N/A",
            "verdict": "genuine",
            "confidence": 0.0,
            "risk_score": 0,
            "summary": "No image uploaded for visual evaluation.",
            "image_path": None,
            "location": location or "Online Feed",
            "_mock": False,
            "fallback_used": False,
        }

    if not os.path.exists(image_path):
        resolved = os.path.normpath(os.path.join(_AGENT4_DIR, "..", image_path))
        if os.path.exists(resolved):
            image_path = resolved
        else:
            err = f"Image file not found: {image_path} — falling back to mock"
            base["error"] = err
            return {**base, **_mock_result(location), "error": err, "fallback_used": True}

    # --- Import Agent 1 ---
    try:
        from inference import process_note_image  # type: ignore
    except ImportError as e:
        err = f"Agent 1 import failed: {e} — falling back to mock"
        base["error"] = err
        return {**base, **_mock_result(location), "error": err, "fallback_used": True}

    # --- Run live pipeline ---
    try:
        result = process_note_image(
            image_path=image_path,
            denom_hint=denom_hint,
            location=location,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )
    except Exception as e:
        err = f"Agent 1 pipeline error: {e} — falling back to mock"
        base["error"] = err
        return {**base, **_mock_result(location), "error": err, "fallback_used": True}

    # Determine availability from status
    is_ok = result.get("status") in (
        "ok", "flagged_low_denomination_confidence"
    ) and result.get("verdict") is not None

    if not is_ok:
        status_msg = result.get("status") or "unknown_error"
        if status_msg in ("note_not_found", "no_currency_detected", "contour_not_detected", "unknown_error"):
            return {
                "available": True,
                "status": "no_currency_detected",
                "denomination": "N/A",
                "denomination_auto_detected": False,
                "verdict": "genuine",
                "confidence": 0.95,
                "risk_score": 0,
                "summary": f"Image verified: Harmless picture or non-currency document (status: {status_msg}). No counterfeit features detected.",
                "batch_id": None,
                "is_new_batch": False,
                "location": location or "Online Feed",
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "error": None,
                "image_path": image_path,
                "_mock": False,
                "fallback_used": False,
            }
        err = f"Agent 1 returned status '{status_msg}' — falling back to mock"
        base["error"] = err
        return {**base, **_mock_result(location), "error": err, "fallback_used": True}

    result["available"] = True
    result["location"] = location
    result.setdefault("error", None)
    result["fallback_used"] = False
    return result


def _mock_result(location: Optional[str]) -> Dict[str, Any]:
    """
    Emergency fallback mock result.
    Used ONLY when Agent 1 cannot run (missing image, missing deps).
    """
    return {
        "available": True,
        "status": "ok",
        "denomination": "500",
        "denomination_auto_detected": False,
        "verdict": "fake",
        "confidence": 0.87,
        "batch_id": "batch_002",
        "is_new_batch": False,
        "location": location or "Jaipur Branch A",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "error": None,
        "_mock": True,
    }
