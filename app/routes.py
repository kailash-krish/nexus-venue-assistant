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
    Supports ``vip``, ``refresh``, and optional ``g-recaptcha-response``
    query parameters.
POST /api/translate
    Translates gate names and protip text via Google Cloud Translation.
    Accepts ``{"texts": [...], "target": "es", "token": "<reCAPTCHA>"}``
    JSON body.
GET /api/health
    Lightweight liveness probe for Cloud Run health checks.

Security
--------
* All query-string values are sanitised (HTML-escaped, length-capped) before use.
* ``vip`` and ``refresh`` are strictly coerced to ``bool`` — no truthy shortcut.
* reCAPTCHA v3 tokens are verified server-side via the Google ``siteverify``
  REST endpoint.  Verification is **advisory** when ``RECAPTCHA_SECRET`` is
  absent so the dashboard works without the env-var during development.
* No user-supplied data is interpolated into SQL, shell commands, or HTML.
"""

from __future__ import annotations

import html
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import requests
from flask import Blueprint, jsonify, render_template, request
from flask.wrappers import Response

from utils.telemetry import (
    arena_state,
    build_recommendation,
    crowd_score,
    sync_arena_telemetry,
)

logger: logging.Logger = logging.getLogger("NEXUS-ROUTES")
bp: Blueprint = Blueprint("main", __name__)

# ── External endpoints ────────────────────────────────────────────────────────

_TRANSLATE_URL:   str = "https://translation.googleapis.com/language/translate/v2"
_RECAPTCHA_URL:   str = "https://www.google.com/recaptcha/api/siteverify"
_RECAPTCHA_MIN_SCORE: float = 0.5


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
    Strictly coerce a sanitised query-string fragment to a Python ``bool``.

    Only the explicit strings ``"true"``, ``"1"``, and ``"yes"``
    (case-insensitive) are treated as truthy.  Everything else — including
    empty string and arbitrary garbage — resolves to *default*, preventing
    accidental privilege escalation through non-standard truthy values.

    Args:
        param:   Sanitised string fragment from a query parameter.
        default: Value returned when *param* is empty or unrecognised.

    Returns:
        Boolean interpretation of *param*.

    Examples:
        >>> _parse_bool_param("true")
        True
        >>> _parse_bool_param("1")
        True
        >>> _parse_bool_param("banana")
        False
        >>> _parse_bool_param("")
        False
    """
    return param.lower() in ("true", "1", "yes") if param else default


# ─────────────────────────────────────────────────────────────────────────────
#  reCAPTCHA v3 verification
# ─────────────────────────────────────────────────────────────────────────────

def _verify_recaptcha(token: str) -> bool:
    """
    Verify a reCAPTCHA v3 client token via the Google ``siteverify`` endpoint.

    The check is **advisory-only** when ``RECAPTCHA_SECRET`` is not configured
    (returns ``True`` immediately).  In production, requests with a score below
    :data:`_RECAPTCHA_MIN_SCORE` are rejected.

    Score thresholds (Google guidance):
        * 0.9 — very likely human.
        * 0.5 — borderline (default threshold used here).
        * 0.1 — very likely bot.

    Args:
        token: The ``g-recaptcha-response`` token provided by the frontend
               ``grecaptcha.execute()`` call.

    Returns:
        ``True`` if the token is valid and the score meets the threshold,
        or if reCAPTCHA is not configured.
        ``False`` if the token is invalid, expired, or scores below threshold.
    """
    secret: str = os.getenv("RECAPTCHA_SECRET", "")
    if not secret:
        return True          # dev / CI — no secret configured, pass through

    if not token:
        return False

    try:
        resp = requests.post(
            _RECAPTCHA_URL,
            data={"secret": secret, "response": token},
            timeout=3,
        )
        resp.raise_for_status()
        body: Dict[str, Any] = resp.json()
        success: bool = bool(body.get("success", False))
        score: float  = float(body.get("score", 0.0))
        if not success or score < _RECAPTCHA_MIN_SCORE:
            logger.warning(
                "reCAPTCHA rejected — success=%s score=%.2f", success, score
            )
            return False
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("reCAPTCHA verification error: %s", exc)
        return True          # fail-open: network error should not block users


# ─────────────────────────────────────────────────────────────────────────────
#  Translation helper
# ─────────────────────────────────────────────────────────────────────────────

def _translate_texts(texts: List[str], target: str) -> List[str]:
    """
    Translate a list of strings to *target* language via Google Cloud
    Translation API v2 (REST).

    Uses a single batched POST for efficiency — one API call regardless of how
    many strings are in *texts*.  Falls back to the original strings unchanged
    whenever the API key is absent, the call times out, or the response is
    malformed, so the dashboard never breaks due to a translation failure.

    Args:
        texts:  List of UTF-8 source strings to translate.
        target: BCP-47 language code for the output language, e.g. ``"es"``.

    Returns:
        List of translated strings in the same order as *texts*.
        Returns the original *texts* list on any error.

    Raises:
        Never raises; all exceptions are caught and logged internally.
    """
    api_key: str = os.getenv("TRANSLATE_API_KEY", "")
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
        translations: List[Dict[str, str]] = (
            resp.json().get("data", {}).get("translations", [])
        )
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

    The Google Maps API key, GA4 Measurement ID, and reCAPTCHA Site Key are
    read from environment variables and injected into the Jinja2 template at
    render time.  They are never stored in source control.

    Returns:
        Rendered HTML string for the complete single-page dashboard.
    """
    maps_key:       str = os.getenv("MAPS_API_KEY",         "")
    ga4_id:         str = os.getenv("GA4_MEASUREMENT_ID",   "")
    recaptcha_site: str = os.getenv("RECAPTCHA_SITE_KEY",   "")
    logger.info("Dashboard requested from %s", request.remote_addr)
    return render_template(
        "index.html",
        maps_key=maps_key,
        ga4_id=ga4_id,
        recaptcha_site=recaptcha_site,
    )


@bp.route("/api/recommend")
def api_recommend() -> Tuple[Response, int]:
    """
    Primary telemetry and AI-routing recommendation endpoint.

    Performs optional reCAPTCHA v3 verification when a token is provided via
    the ``token`` query parameter.  Forces a full telemetry re-sync (hitting
    Firebase) when ``refresh=true`` is passed.  All query parameters are
    sanitised and strictly type-cast before use.

    Query Parameters:
        vip (str):     ``"true"`` / ``"false"`` — include VIP gates in routing.
        refresh (str): ``"true"`` / ``"false"`` — force sensor re-sync.
        token (str):   Optional reCAPTCHA v3 response token.

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

        HTTP 400 with ``{"error": "reCAPTCHA verification failed"}`` when a
        token is supplied but rejected by Google.
        HTTP 500 with ``{"error": "..."}`` on unhandled exceptions.
    """
    try:
        # ── reCAPTCHA (advisory when RECAPTCHA_SECRET absent) ─────────────────
        raw_token: str = _sanitize_str(request.args.get("token", ""), max_len=2048)
        if raw_token and not _verify_recaptcha(raw_token):
            return jsonify({"error": "reCAPTCHA verification failed"}), 400

        # ── Input sanitisation + strict bool coercion ─────────────────────────
        raw_vip:     str = _sanitize_str(request.args.get("vip",     "false"))
        raw_refresh: str = _sanitize_str(request.args.get("refresh", "false"))

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

    Optionally verifies a reCAPTCHA v3 token supplied in the request body
    under the ``"token"`` key.  Returns translated strings in the same order
    as the input ``"texts"`` array.

    Request body (``application/json``)::

        {
          "texts":  ["Gate A · North Concourse", "Navigate to Gate B"],
          "target": "es",
          "token":  "<optional reCAPTCHA v3 token>"
        }

    Returns:
        HTTP 200 with JSON body::

            {"translated": ["Puerta A · Concurso Norte", "Navegar a la Puerta B"]}

        HTTP 400 if ``texts`` is not a list, or if a supplied reCAPTCHA token
        is rejected.
        HTTP 500 on unexpected server errors.
    """
    try:
        body: Dict[str, Any] = request.get_json(silent=True) or {}

        # ── reCAPTCHA (advisory when RECAPTCHA_SECRET absent) ─────────────────
        raw_token: str = str(body.get("token", ""))[:2048]
        if raw_token and not _verify_recaptcha(raw_token):
            return jsonify({"error": "reCAPTCHA verification failed"}), 400

        raw_texts:  Any = body.get("texts", [])
        raw_target: str = str(body.get("target", "es"))[:5]

        if not isinstance(raw_texts, list):
            return jsonify({"error": "texts must be an array"}), 400
        if not raw_texts:
            return jsonify({"translated": []}), 200

        safe_texts: List[str] = [
            html.escape(str(t)[:500]) for t in raw_texts if t is not None
        ]
        target: str = html.escape(raw_target)

        logger.info(
            "API /translate — target=%s items=%d addr=%s",
            target, len(safe_texts), request.remote_addr,
        )

        translated: List[str] = _translate_texts(safe_texts, target)
        return jsonify({"translated": translated}), 200

    except Exception as exc:
        logger.critical("API /translate failure: %s", exc, exc_info=True)
        return jsonify({"error": "Translation service temporarily unavailable"}), 500


@bp.route("/api/health")
def health() -> Tuple[Response, int]:
    """
    Liveness probe endpoint for Google Cloud Run health checks.

    Returns a minimal JSON payload confirming the application is alive,
    along with the current telemetry generation ID for quick diagnostics.

    Returns:
        HTTP 200 with ``{"status": "ok", "telemetry_id": int}``.
    """
    return jsonify({"status": "ok", "telemetry_id": arena_state["telemetry_id"]}), 200
