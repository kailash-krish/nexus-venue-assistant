"""
NEXUS · app/__init__.py
=======================
Flask application factory.

Responsibilities
----------------
* JSON-structured logging compatible with Google Cloud Logging's ``jsonPayload``
  format (severity, message, timestamp, component).
* Hardened HTTP security headers on every response, including a Content-Security-Policy
  that explicitly permits Google Analytics 4 (GA4) and reCAPTCHA v3 script origins.
* Blueprint registration.

Environment variables consumed
-------------------------------
MAPS_API_KEY        – Google Maps JS API key (injected into template at render-time).
FIREBASE_URL        – Firebase Realtime Database base URL,
                      e.g. ``https://<project>.firebaseio.com``.
FIREBASE_SECRET     – Database secret / legacy token for REST auth.
GEMINI_API_KEY      – Google Gemini generative AI key.
TRANSLATE_API_KEY   – Google Cloud Translation API key.
RECAPTCHA_SECRET    – reCAPTCHA v3 server-side secret key.
GA4_MEASUREMENT_ID  – Google Analytics 4 Measurement ID (G-XXXXXXXXXX).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from flask import Flask
from flask.wrappers import Response


# ── JSON log formatter ────────────────────────────────────────────────────────

class _CloudJsonFormatter(logging.Formatter):
    """
    Emit each log record as a single-line JSON object understood by
    Google Cloud Logging's structured-logging ingestion pipeline.

    The ``severity`` field maps Python log levels to the GCP severity enum
    so that Cloud Logging surfaces them correctly in Log Explorer.

    Attributes:
        _LEVEL_MAP: Mapping from Python level names to GCP severity strings.
    """

    _LEVEL_MAP: dict[str, str] = {
        "DEBUG":    "DEBUG",
        "INFO":     "INFO",
        "WARNING":  "WARNING",
        "ERROR":    "ERROR",
        "CRITICAL": "CRITICAL",
    }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format *record* as a JSON string suitable for Cloud Logging ingestion.

        Args:
            record: The :class:`logging.LogRecord` to format.

        Returns:
            A single-line JSON string with GCP-compatible severity, message,
            logger name, module, function name, and line number fields.
        """
        payload: dict[str, Any] = {
            "severity":  self._LEVEL_MAP.get(record.levelname, "DEFAULT"),
            "message":   record.getMessage(),
            "logger":    record.name,
            "module":    record.module,
            "funcName":  record.funcName,
            "lineno":    record.lineno,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


# ── Factory ───────────────────────────────────────────────────────────────────

def create_app() -> Flask:
    """
    Create and configure the NEXUS Flask application.

    Applies JSON-structured logging, hardened security headers (including a
    CSP that permits GA4, reCAPTCHA v3, Firebase, Gemini, and Translation
    origins), and registers the main Blueprint.  All Google Cloud service
    credentials are read from environment variables so that no secrets are
    embedded in source code.

    Returns:
        A fully configured :class:`flask.Flask` instance ready to serve.

    Example::

        from app import create_app
        app = create_app()
    """
    from dotenv import load_dotenv
    load_dotenv()

    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    # ── Structured logging (Cloud Logging compatible) ─────────────────────────
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_CloudJsonFormatter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)

    # ── Security headers ──────────────────────────────────────────────────────
    @app.after_request
    def _security_headers(response: Response) -> Response:
        """
        Attach OWASP-recommended security headers to every HTTP response.

        Headers applied
        ---------------
        X-Content-Type-Options
            Prevents MIME-type sniffing (``nosniff``).
        X-Frame-Options
            Blocks clickjacking via iframes (``DENY``).
        X-XSS-Protection
            Enables legacy browser XSS filter (``1; mode=block``).
        Referrer-Policy
            Restricts referrer leakage (``strict-origin-when-cross-origin``).
        Strict-Transport-Security
            Enforces HTTPS for one year including sub-domains.
        Permissions-Policy
            Restricts access to sensitive browser APIs.
        Content-Security-Policy
            Allowlists only the origins required by the dashboard:
            Tailwind CDN, Lucide, Google Fonts, Maps JS API, GA4,
            reCAPTCHA v3, Firebase, Gemini, and Translation.

        Args:
            response: The outgoing :class:`flask.wrappers.Response` object.

        Returns:
            The same response with all security headers attached.
        """
        response.headers["X-Content-Type-Options"]   = "nosniff"
        response.headers["X-Frame-Options"]           = "DENY"
        response.headers["X-XSS-Protection"]          = "1; mode=block"
        response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"]        = (
            "geolocation=(self), camera=(), microphone=()"
        )
        # CSP — permits every origin the dashboard needs, including GA4 and reCAPTCHA v3.
        # 'unsafe-inline' is required by Tailwind CDN's runtime injection.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' "
            "https://cdn.tailwindcss.com "
            "https://unpkg.com "
            "https://maps.googleapis.com "
            "https://www.googletagmanager.com "
            "https://www.google.com "
            "https://www.gstatic.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "img-src 'self' data: "
            "https://maps.gstatic.com https://maps.googleapis.com "
            "https://www.google-analytics.com https://www.googletagmanager.com; "
            "frame-src https://www.google.com; "
            "connect-src 'self' "
            "https://maps.googleapis.com "
            "https://firebaseio.com "
            "https://generativelanguage.googleapis.com "
            "https://translation.googleapis.com "
            "https://www.google-analytics.com "
            "https://region1.google-analytics.com "
            "https://www.recaptcha.net;"
        )
        return response

    # ── Blueprint ─────────────────────────────────────────────────────────────
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
