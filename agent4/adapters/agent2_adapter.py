"""
agent4/adapters/agent2_adapter.py

Pulls live campaign intelligence from Agent 2's MongoDB database.

Priority order (live-first, mock ONLY on failure):
  1. Live MongoDB: query Agent 2's own 'events' and 'clusters' collections
     directly using the same MONGO_URI Agent 2 writes to.
  2. JSON file: load from a pre-exported Agent 2 events file (if provided).
  3. Mock (FALLBACK ONLY): if MongoDB is unreachable and no JSON provided.

Agent 2 writes to MongoDB collections: raw_posts, processed_posts,
clusters, events. We read from 'events' (highest-severity first) and
'clusters' for the matching cluster detail.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# MongoDB live reader
# ---------------------------------------------------------------------------

def _from_mongodb(mongo_uri: str) -> Dict[str, Any]:
    """
    Connect to Agent 2's MongoDB and pull the most recent high-severity event.

    Reads:
      - 'events'   collection → sorted by occurred_at desc, severity filter
      - 'clusters' collection → matching cluster_id for full cluster detail
    """
    try:
        from pymongo import MongoClient  # type: ignore

        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=4000)
        client.admin.command("ping")  # verify connection
        db = client["fraud_intelligence"]

        events_col   = db["events"]
        clusters_col = db["clusters"]

        # Prefer critical → high → medium → any
        top_event = None
        for sev in ["critical", "high", "medium", "low"]:
            top_event = events_col.find_one(
                {"severity": sev},
                {"_id": 0},
                sort=[("occurred_at", -1)],
            )
            if top_event:
                break

        if not top_event:
            top_event = events_col.find_one({}, {"_id": 0}, sort=[("occurred_at", -1)])

        if not top_event:
            return {
                "available": False,
                "error": "No events found in Agent 2 MongoDB — has the scheduler run?",
                "_source": "mongodb_empty",
            }

        # Get the corresponding cluster document
        cluster = clusters_col.find_one(
            {"cluster_id": top_event.get("cluster_id")},
            {"_id": 0},
        )

        result = _normalise(top_event, cluster)
        result["_source"] = "mongodb_live"
        return result

    except Exception as e:
        return {
            "available": False,
            "error": f"MongoDB connection failed: {e}",
            "_source": "mongodb_error",
        }


# ---------------------------------------------------------------------------
# JSON file reader
# ---------------------------------------------------------------------------

def _from_json(json_path: str) -> Dict[str, Any]:
    """Load Agent 2 event(s) from a JSON export file."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        events = data if isinstance(data, list) else [data]

        # Pick highest severity
        for sev in ["critical", "high", "medium", "low"]:
            for ev in events:
                if str(ev.get("severity", "")).lower() == sev:
                    result = _normalise(ev, ev.get("cluster"))
                    result["_source"] = f"json_file:{json_path}"
                    return result

        if events:
            result = _normalise(events[0], None)
            result["_source"] = f"json_file:{json_path}"
            return result

        return {"available": False, "error": "JSON file empty", "_source": "json_empty"}

    except Exception as e:
        return {"available": False, "error": f"JSON load failed: {e}", "_source": "json_error"}


# ---------------------------------------------------------------------------
# Mock fallback (emergency only)
# ---------------------------------------------------------------------------

def _mock_event() -> Dict[str, Any]:
    """
    Emergency fallback. Used ONLY when MongoDB is unreachable and no JSON file.
    Represents a realistic CRITICAL digital arrest campaign.
    """
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    return {
        "available": True,
        "_source": "mock_fallback",
        "_mock": True,
        "active_events": [{"severity": "critical", "scam_type": "digital_arrest", "post_count": 34}],
        "top_cluster": {
            "cluster_id": 7,
            "scam_type": "digital_arrest",
            "severity": "critical",
            "post_count": 34,
            "avg_confidence": 0.82,
            "campaign_score": 0.83,
            "weighted_confidence": 0.79,
            "sources": ["telegram", "reddit"],
            "platforms": ["ScamsIndia", "IndiaFrauds", "cybercrime_alerts_jaipur"],
            "is_multi_source": True,
            "earliest_post": "2026-07-17T18:30:00+00:00",
            "latest_post": now_iso,
        },
        "severity": "critical",
        "scam_type": "digital_arrest",
        "campaign_score": 0.83,
        "weighted_confidence": 0.79,
        "post_count": 34,
        "sources": ["telegram", "reddit"],
        "platforms": ["ScamsIndia", "IndiaFrauds", "cybercrime_alerts_jaipur"],
        "locations": ["jaipur", "jodhpur", "rajasthan"],
        "is_multi_source": True,
        "cluster_id": 7,
        "temporal_data": {
            "earliest_post": "2026-07-17T18:30:00+00:00",
            "latest_post": now_iso,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def _normalise(event: Dict, cluster: Optional[Dict]) -> Dict[str, Any]:
    """Flatten raw Agent 2 event + cluster into Agent4 schema shape."""
    src = cluster or event

    # Safely convert datetimes to ISO strings
    def _iso(val):
        if val is None:
            return None
        if isinstance(val, datetime):
            return val.isoformat()
        return str(val)

    return {
        "available":           True,
        "active_events":       [event],
        "top_cluster":         cluster,
        "severity":            str(event.get("severity") or src.get("severity") or "unknown").lower(),
        "scam_type":           event.get("scam_type") or src.get("scam_type"),
        "campaign_score":      float(src.get("campaign_score") or 0),
        "weighted_confidence": float(src.get("weighted_confidence") or 0),
        "post_count":          int(src.get("post_count") or 0),
        "sources":             list(src.get("sources") or []),
        "platforms":           list(src.get("platforms") or []),
        "locations":           [],          # enriched from entity extraction if available
        "is_multi_source":     bool(src.get("is_multi_source", False)),
        "cluster_id":          event.get("cluster_id"),
        "temporal_data": {
            "earliest_post": _iso(src.get("earliest_post")),
            "latest_post":   _iso(src.get("latest_post")),
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(
    source: str = "mongodb",
    json_path: Optional[str] = None,
    mongo_uri: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve latest Agent 2 campaign intelligence.

    Priority:
      1. MongoDB (live) — default, requires MONGO_URI
      2. JSON file      — if json_path provided and source='json'
      3. Mock           — ONLY if both above fail

    Args:
        source:    'mongodb' (default) | 'json' | 'mock'
        json_path: Path to JSON file (json mode only)
        mongo_uri: MongoDB URI override (reads MONGO_URI env var otherwise)

    Returns:
        dict matching Agent2Result schema — never raises.
    """
    if source == "mock":
        # Caller explicitly requested mock — honour it
        return _mock_event()

    if source == "json":
        if not json_path:
            # Degrade to mongodb
            pass
        else:
            result = _from_json(json_path)
            if result.get("available"):
                return result
            # JSON failed — try MongoDB next
            print(f"  [!] JSON source failed ({result.get('error')}) — trying MongoDB")

    # Default / json-failed: try MongoDB
    uri = mongo_uri or os.getenv("MONGO_URI", "mongodb://localhost:27017")
    result = _from_mongodb(uri)
    if result.get("available"):
        return result

    # MongoDB failed — warn and use mock
    print(f"  [!] MongoDB unavailable ({result.get('error')}) — using mock fallback")
    fallback = _mock_event()
    fallback["_mongodb_error"] = result.get("error")
    return fallback
