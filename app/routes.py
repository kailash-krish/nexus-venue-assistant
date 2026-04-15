"""
NEXUS · app/routes.py
=====================
All URL routes for the NEXUS platform.

Endpoints:
  GET /              — Renders the high-fidelity dashboard
  GET /api/recommend — Telemetry + recommendation JSON API
  GET /api/health    — Liveness probe for Cloud Run
"""

from __future__ import annotations

import html
import logging
import os
from typing import Any, Dict, Tuple

from flask import Blueprint, jsonify, render_template, request
from flask.wrappers import Response

from utils.telemetry import (
    arena_state,
    build_recommendation,
    crowd_score,
    sync_arena_telemetry,
)

logger = logging.getLogger("NEXUS-ROUTES")
bp = Blueprint("main", __name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _sanitize_str(value: Any, max_len: int = 64) -> str:
    """
    Sanitize and truncate an untrusted string value from query params.

    Args:
        value:   Input value (may be None or non-string).
        max_len: Maximum permitted length after sanitisation.

    Returns:
        Safe, HTML-escaped string, truncated to ``max_len``.
    """
    if value is None:
        return ""
    return html.escape(str(value)[:max_len])


def _parse_bool_param(param: str, default: bool = False) -> bool:
    """
    Parse a boolean-like query-string parameter.

    Args:
        param:   Raw query string value.
        default: Fallback if value is unrecognisable.

    Returns:
        Boolean interpretation.
    """
    return param.lower() in ("true", "1", "yes") if param else default


# ── Views ─────────────────────────────────────────────────────────────────────

@bp.route("/")
def index() -> str:
    """
    Render the NEXUS dashboard.

    Injects the Maps API key from the environment at template render time;
    the key is never exposed in source control.

    Returns:
        Rendered HTML string.
    """
    maps_key: str = os.getenv("MAPS_API_KEY", "")
    logger.info("Dashboard requested from %s", request.remote_addr)
    return render_template("index.html", maps_key=maps_key)


# ── API ───────────────────────────────────────────────────────────────────────

@bp.route("/api/recommend")
def api_recommend() -> Tuple[Response, int]:
    """
    Primary telemetry and recommendation endpoint.

    Query Parameters:
        vip     (bool):  Whether VIP gates should be included in routing.
        refresh (bool):  Force a full telemetry re-sync before responding.

    Returns:
        JSON payload with gates, restrooms, food, protip, crowd_score.
    """
    try:
        # ── Input validation ──────────────────────────────────────────────────
        raw_vip     = _sanitize_str(request.args.get("vip", "false"))
        raw_refresh = _sanitize_str(request.args.get("refresh", "false"))

        vip_enabled: bool = _parse_bool_param(raw_vip)
        force_refresh: bool = _parse_bool_param(raw_refresh)

        logger.info(
            "API /recommend — vip=%s force_refresh=%s addr=%s",
            vip_enabled, force_refresh, request.remote_addr,
        )

        if force_refresh:
            sync_arena_telemetry()

        protip: Dict[str, str] = build_recommendation(vip_enabled=vip_enabled)
        score: int = crowd_score()

        payload: Dict[str, Any] = {
            "gates":       arena_state["gates"],
            "restrooms":   arena_state["restrooms"],
            "food":        arena_state["food_services"],
            "protip":      protip,
            "crowd_score": score,
            "telemetry_id": arena_state["telemetry_id"],
        }

        return jsonify(payload), 200

    except Exception as exc:
        logger.critical("API failure: %s", exc, exc_info=True)
        return jsonify({"error": "Telemetry service temporarily unavailable"}), 500


@bp.route("/api/health")
def health() -> Tuple[Response, int]:
    """
    Liveness probe for Cloud Run health checks.

    Returns:
        JSON ``{"status": "ok"}`` with HTTP 200.
    """
    return jsonify({"status": "ok", "telemetry_id": arena_state["telemetry_id"]}), 200
