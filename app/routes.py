"""
NEXUS · app/routes.py
=====================
HTTP route handlers for the NEXUS venue intelligence platform.

Endpoints
---------
GET /
    Renders the full-page Aero-Glass / Ultra-Night dashboard.
GET /api/recommend
    Returns telemetry, routing protip, and crowd score as JSON.
    Supports ``vip`` and ``refresh`` query parameters.
POST /api/translate
    Translates gate names and protip text via Google Cloud Translation.
    Accepts ``{"texts": [...], "target": "es"}`` JSON body.
GET /api/health
    Lightweight liveness probe for Cloud Run health checks.

Security
--------
All query-string values are sanitised (HTML-escaped, length-capped) before use.
No user-supplied data is ever interpolated into SQL, shell commands, or HTML.
"""

from __future__ import annotations

import html
import json
import logging
import os
from typing import Any, Dict, List, Tuple

import requests
from flask import Blueprint, jsonify, render_template, request
from flask.wrappers import Response

from utils.telemetry import (
    arena_state,
    build_recommendation,
    crowd_score,
    sync_arena_telemetry,
)

logger = logging.getLogger("NEXUS-ROUTES")
bp     = Blueprint("main", __name__)

# ── Google Cloud Translation REST endpoint ────────────────────────────────────

_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"


# ─────────────────────────────────────────────────────────────────────────────
#  Input helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sanitize_str(value: Any, max_len: int = 64) -> str:
    """
    Sanitise and truncate an untrusted string value from query parameters.

    Converts the input to ``str``, truncates to ``max_len`` characters, then
    HTML-escapes the result to prevent injection into downstream contexts.

    Args:
        value:   Raw input — may be ``None``, a list, or any other type.
        max_len: Maximum allowed length *before* HTML escaping.

    Returns:
        A safe, HTML-escaped string of at most ``max_len`` characters.

    Examples:
        >>> _sanitize_str("<script>alert(1)</script>")
        '&lt;script&gt;alert(1)&lt;/script&gt;'
        >>> _sanitize_str(None)
        ''
    """
    if value is None:
        return ""
    return html.escape(str(value)[:max_len])


def _parse_bool_param(param: str, default: bool = False) -> bool:
    """
    Coerce a raw query-string fragment to a Python ``bool``.

    Recognises ``"true"``, ``"1"``, and ``"yes"`` (case-insensitive) as
    truthy; everything else (including empty string) resolves to *default*.

    Args:
        param:   Raw string fragment after sanitisation.
        default: Value returned when ``param`` is empty or unrecognised.

    Returns:
        Boolean interpretation of *param*.

    Examples:
        >>> _parse_bool_param("true")
        True
        >>> _parse_bool_param("banana")
        False
    """
    return param.lower() in ("true", "1", "yes") if param else default


# ─────────────────────────────────────────────────────────────────────────────
#  Translation helper
# ─────────────────────────────────────────────────────────────────────────────

def _translate_texts(texts: List[str], target: str) -> List[str]:
    """
    Translate a list of strings to *target* language via Google Cloud
    Translation API v2 (REST).

    Uses a single batched API call for efficiency.  If the API key is not
    configured or the call fails, the original texts are returned unchanged
    so the dashboard never breaks due to a missing translation key.

    Args:
        texts:  List of UTF-8 strings to translate.
        target: BCP-47 language code for the output language, e.g. ``"es"``.

    Returns:
        List of translated strings in the same order as *texts*.
        Falls back to the original strings on any error.

    Raises:
        Does not raise; all exceptions are caught and logged internally.
    """
    api_key = os.getenv("TRANSLATE_API_KEY", "")
    if not api_key or not texts:
        return texts

    try:
        resp = requests.post(
            _TRANSLATE_URL,
            params={"key": api_key},
            json={"q": texts, "target": target, "format": "text"},
            timeout=4,
        )
        resp.raise_for_status()
        translations = resp.json().get("data", {}).get("translations", [])
        return [t.get("translatedText", orig) for t, orig in zip(translations, texts)]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Translation API error: %s", exc)
        return texts


# ─────────────────────────────────────────────────────────────────────────────
#  Routes
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/")
def index() -> str:
    """
    Render the NEXUS Aero-Glass / Ultra-Night dashboard.

    The Google Maps API key is read from the ``MAPS_API_KEY`` environment
    variable and injected into the Jinja2 template at render time.  It is
    never stored in source control.

    Returns:
        Rendered HTML string for the complete single-page dashboard.
    """
    maps_key: str = os.getenv("MAPS_API_KEY", "")
    logger.info("Dashboard requested from %s", request.remote_addr)
    return render_template("index.html", maps_key=maps_key)


@bp.route("/api/recommend")
def api_recommend() -> Tuple[Response, int]:
    """
    Primary telemetry and AI-routing recommendation endpoint.

    Optionally forces a full telemetry re-sync (hitting Firebase) when
    ``refresh=true`` is passed.  All query parameters are sanitised before use.

    Query Parameters:
        vip (str):      ``"true"`` / ``"false"`` — include VIP gates in routing.
        refresh (str):  ``"true"`` / ``"false"`` — force sensor re-sync.

    Returns:
        HTTP 200 with JSON body::

            {
              "gates":        [...],
              "restrooms":    [...],
              "food":         [...],
              "protip":       {"headline": ..., "detail": ..., "action": ...},
              "crowd_score":  int,
              "telemetry_id": int
            }

        HTTP 500 with ``{"error": "..."}`` on unhandled exceptions.
    """
    try:
        raw_vip     = _sanitize_str(request.args.get("vip",     "false"))
        raw_refresh = _sanitize_str(request.args.get("refresh", "false"))

        vip_enabled:   bool = _parse_bool_param(raw_vip)
        force_refresh: bool = _parse_bool_param(raw_refresh)

        logger.info(
            "API /recommend — vip=%s refresh=%s addr=%s",
            vip_enabled, force_refresh, request.remote_addr,
        )

        if force_refresh:
            sync_arena_telemetry()

        protip: Dict[str, str] = build_recommendation(vip_enabled=vip_enabled)
        score:  int            = crowd_score()

        payload: Dict[str, Any] = {
            "gates":        arena_state["gates"],
            "restrooms":    arena_state["restrooms"],
            "food":         arena_state["food_services"],
            "protip":       protip,
            "crowd_score":  score,
            "telemetry_id": arena_state["telemetry_id"],
        }
        return jsonify(payload), 200

    except Exception as exc:
        logger.critical("API /recommend failure: %s", exc, exc_info=True)
        return jsonify({"error": "Telemetry service temporarily unavailable"}), 500


@bp.route("/api/translate", methods=["POST"])
def api_translate() -> Tuple[Response, int]:
    """
    Translate dashboard text via Google Cloud Translation API.

    Called by the frontend language toggle (EN ↔ ES).  Accepts a JSON body
    containing an array of strings and a target locale.  Returns translated
    strings in the same order.

    Request body (``application/json``)::

        {"texts": ["Gate A · North Concourse", "Navigate to Gate B"], "target": "es"}

    Returns:
        HTTP 200 with JSON body::

            {"translated": ["Puerta A · Concurso Norte", "Navegar a la Puerta B"]}

        HTTP 400 if the request body is malformed or missing required keys.
        HTTP 500 on unexpected server errors.
    """
    try:
        body = request.get_json(silent=True) or {}

        raw_texts  = body.get("texts", [])
        raw_target = str(body.get("target", "es"))[:5]   # BCP-47 max 5 chars

        # Validate
        if not isinstance(raw_texts, list):
            return jsonify({"error": "texts must be an array"}), 400
        if not raw_texts:
            return jsonify({"translated": []}), 200

        # Sanitise each string; cap at 500 chars (Translation API limit awareness)
        safe_texts: List[str] = [
            html.escape(str(t)[:500]) for t in raw_texts if t is not None
        ]
        target: str = html.escape(raw_target)

        logger.info(
            "API /translate — target=%s items=%d addr=%s",
            target, len(safe_texts), request.remote_addr,
        )

        translated = _translate_texts(safe_texts, target)
        return jsonify({"translated": translated}), 200

    except Exception as exc:
        logger.critical("API /translate failure: %s", exc, exc_info=True)
        return jsonify({"error": "Translation service temporarily unavailable"}), 500


@bp.route("/api/health")
def health() -> Tuple[Response, int]:
    """
    Liveness probe endpoint for Google Cloud Run health checks.

    Returns a minimal JSON payload confirming the application is alive and
    includes the current telemetry generation ID for quick diagnostics.

    Returns:
        HTTP 200 with ``{"status": "ok", "telemetry_id": int}``.
    """
    return jsonify({"status": "ok", "telemetry_id": arena_state["telemetry_id"]}), 200
