"""
agent4/api/main.py

FastAPI backend for the Fraud Intelligence Platform.
Run from the PROJECT ROOT (fraud-campaign-intelligence/):

    python -m uvicorn agent4.api.main:app --port 8000 --reload

Endpoints:
    GET  /api/v1/health              — liveness check
    POST /api/v1/analyze             — run full Agent 4 pipeline on uploaded files
    GET  /api/v1/cases/sample        — run pipeline with no inputs (live demo)
    GET  /api/v1/analyze/stream/{id} — SSE log stream for a running session
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# ── Python path: make sure agent4/ imports resolve ────────────────────────────
_API_DIR   = os.path.dirname(os.path.abspath(__file__))   # …/agent4/api
_AGENT4_DIR = os.path.dirname(_API_DIR)                   # …/agent4
_ROOT_DIR   = os.path.dirname(_AGENT4_DIR)                # project root

for _p in [_ROOT_DIR, _AGENT4_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Import orchestrator using its public API
from orchestrator import run_from_dict as _orch_run         # type: ignore
from api.mapper import report_to_case                       # type: ignore


def run_agent4(
    image_path: Optional[str] = None,
    audio_path: Optional[str] = None,
    location: Optional[str]   = None,
    agent2_source: str        = "mongodb",
    denom_hint: str           = "500",
) -> dict:
    """Thin wrapper that calls the orchestrator with correct field names."""
    return _orch_run({
        "currency_image_path": image_path,
        "currency_denom_hint": denom_hint,
        "currency_location":   location or "Unknown",
        "audio_path":          audio_path,
        "agent2_source":       agent2_source,
    })


# ── In-memory SSE log queues (session_id → list of log lines) ────────────────
_log_queues: Dict[str, asyncio.Queue] = {}


def _emit(session_id: str, agent: str, msg: str) -> None:
    """Push a log line into the queue for this session (fire-and-forget)."""
    q = _log_queues.get(session_id)
    if q:
        try:
            q.put_nowait({"agent": agent, "msg": msg})
        except asyncio.QueueFull:
            pass


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Fraud Intelligence Platform — Agent 4 API",
    version="1.0.0",
    description="Multi-agent fraud detection backend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(tz=timezone.utc).isoformat()}


@app.get("/api/v1/cases/sample")
def sample_case():
    """Run the full pipeline with no uploads — uses live MongoDB for Agent 2."""
    try:
        report = run_agent4(agent2_source="mongodb")
        case   = report_to_case(report)
        return {"success": True, "case": case}
    except Exception as exc:
        # Fallback: run in mock mode so the demo always works
        try:
            report = run_agent4(agent2_source="mock")
            case   = report_to_case(report)
            return {"success": True, "case": case, "fallback": True}
        except Exception as exc2:
            return JSONResponse(status_code=500, content={"success": False, "error": str(exc2)})


@app.post("/api/v1/analyze")
async def analyze(
    session_id: str        = Form(default=""),
    audio:      UploadFile = File(default=None),
    image:      UploadFile = File(default=None),
    text:       str        = Form(default=""),
    phone:      str        = Form(default=""),
    url:        str        = Form(default=""),
):
    """Accept uploaded evidence, run full Agent 4 pipeline, return CaseData."""
    sid = session_id or str(uuid.uuid4())
    _log_queues[sid] = asyncio.Queue(maxsize=200)

    tmp_audio = tmp_image = None
    try:
        # Save uploads to temp files
        if audio and audio.filename:
            suffix = os.path.splitext(audio.filename)[1] or ".mp3"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                f.write(await audio.read())
                tmp_audio = f.name
            _emit(sid, "AGENT3", f"Audio uploaded: {audio.filename}")

        if image and image.filename:
            suffix = os.path.splitext(image.filename)[1] or ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                f.write(await image.read())
                tmp_image = f.name
            _emit(sid, "AGENT1", f"Image uploaded: {image.filename}")

        if text:  _emit(sid, "AGENT2", f"Text evidence received ({len(text)} chars)")
        if phone: _emit(sid, "AGENT2", f"Phone number submitted: {phone}")
        if url:   _emit(sid, "AGENT2", f"URL submitted for domain analysis: {url}")

        _emit(sid, "SYSTEM", "Running orchestrator — all agents starting...")

        # Run the orchestrator (blocking — runs in thread pool via FastAPI)
        loop   = asyncio.get_event_loop()
        report = await loop.run_in_executor(
            None,
            lambda: run_agent4(
                image_path=tmp_image,
                audio_path=tmp_audio,
                agent2_source="mongodb",
            ),
        )

        _emit(sid, "FUSION", "Pipeline complete — building verdict...")
        case = report_to_case(report)
        _emit(sid, "SYSTEM", "__DONE__")

        return {"success": True, "case": case, "session_id": sid}

    except Exception as exc:
        _emit(sid, "SYSTEM", f"ERROR: {exc}")
        _emit(sid, "SYSTEM", "__DONE__")
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})

    finally:
        # Clean up temp files
        for p in [tmp_audio, tmp_image]:
            if p and os.path.exists(p):
                try: os.unlink(p)
                except: pass


@app.get("/api/v1/analyze/stream/{session_id}")
async def stream_logs(session_id: str):
    """Server-Sent Events stream: push log lines to the frontend in real-time."""
    q = _log_queues.get(session_id)

    async def _generator():
        if q is None:
            yield "data: {\"agent\":\"SYSTEM\",\"msg\":\"Session not found\"}\n\n"
            return
        while True:
            try:
                item = await asyncio.wait_for(q.get(), timeout=30.0)
                import json
                yield f"data: {json.dumps(item)}\n\n"
                if item.get("msg") == "__DONE__":
                    break
            except asyncio.TimeoutError:
                yield "data: {\"agent\":\"SYSTEM\",\"msg\":\"__DONE__\"}\n\n"
                break

    return StreamingResponse(_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
