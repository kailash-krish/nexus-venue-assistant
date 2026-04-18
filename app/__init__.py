"""
NEXUS · app/__init__.py
=======================
Flask application factory.

Responsibilities
----------------
* JSON-structured logging compatible with Google Cloud Logging's ``jsonPayload``
  format (severity, message, timestamp, component).
* Hardened HTTP security headers on every response.
* Blueprint registration.

Environment variables consumed
-------------------------------
MAPS_API_KEY        – Google Maps JS API key (injected into template at render-time).
FIREBASE_URL        – Firebase Realtime Database base URL, e.g.
                      ``https://<project>.firebaseio.com``.
FIREBASE_SECRET     – Database secret / legacy token for REST auth.
GEMINI_API_KEY      – Google Gemini generative AI key.
TRANSLATE_API_KEY   – Google Cloud Translation API key.
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

    def format(self, record: logging.LogRecord) -> str:  # noqa: D102
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

    Applies JSON-structured logging, security headers, and registers the
    main Blueprint.  All Google Cloud service credentials are read from
    environment variables so that no secrets are embedded in source code.

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
    # Remove default handlers to avoid duplicate / plain-text output
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
            Prevents MIME-type sniffing.
        X-Frame-Options
            Blocks clickjacking via iframes.
        X-XSS-Protection
            Enables legacy browser XSS filters.
        Referrer-Policy
            Limits referrer information leakage.
        Strict-Transport-Security
            Enforces HTTPS for one year, including sub-domains.
        Content-Security-Policy
            Allowlists only the CDN origins used by the dashboard.

        Args:
            response: The outgoing Flask :class:`~flask.wrappers.Response`.

        Returns:
            The same response object with security headers added.
        """
        response.headers["X-Content-Type-Options"]  = "nosniff"
        response.headers["X-Frame-Options"]          = "DENY"
        response.headers["X-XSS-Protection"]         = "1; mode=block"
        response.headers["Referrer-Policy"]          = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        # CSP — permits CDN assets (Tailwind, Lucide, Google Fonts, Maps)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com "
            "https://unpkg.com https://maps.googleapis.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "img-src 'self' data: https://maps.gstatic.com https://maps.googleapis.com; "
            "connect-src 'self' https://maps.googleapis.com https://unpkg.com https://firebaseio.com https://generativelanguage.googleapis.com https://translation.googleapis.com;"
        )
        return response

    # ── Blueprint ─────────────────────────────────────────────────────────────
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
