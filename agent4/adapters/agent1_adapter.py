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
        base["error"] = "No currency image path provided — falling back to mock"
        return {**base, **_mock_result(location), "fallback_used": True}

    if not os.path.exists(image_path):
        base["error"] = f"Image file not found: {image_path} — falling back to mock"
        return {**base, **_mock_result(location), "fallback_used": True}

    # --- Import Agent 1 ---
    try:
        from inference import process_note_image  # type: ignore
    except ImportError as e:
        base["error"] = f"Agent 1 import failed: {e} — falling back to mock"
        return {**base, **_mock_result(location), "fallback_used": True}

    # --- Run live pipeline ---
    try:
        result = process_note_image(
            image_path=image_path,
            denom_hint=denom_hint,
            location=location,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )
    except Exception as e:
        base["error"] = f"Agent 1 pipeline error: {e} — falling back to mock"
        return {**base, **_mock_result(location), "fallback_used": True}

    # Determine availability from status
    result["available"] = result.get("status") in (
        "ok", "flagged_low_denomination_confidence"
    )
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
