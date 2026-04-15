"""
NEXUS · app/__init__.py
=======================
Flask application factory. Registers blueprints, security headers,
and boots the persistent telemetry engine.
"""

from __future__ import annotations

import os
import logging
from flask import Flask


def create_app() -> Flask:
    """
    Application factory.

    Returns:
        Configured Flask application instance.
    """
    from dotenv import load_dotenv
    load_dotenv()

    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    # ── Logging ──────────────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # ── Security: response headers ────────────────────────────────────────────
    @app.after_request
    def apply_security_headers(response):  # type: ignore[return-value]
        """Attach hardened HTTP security headers to every response."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # HSTS — enforced in production via Cloud Run HTTPS termination
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
            "connect-src 'self' https://maps.googleapis.com;"
        )
        return response

    # ── Register blueprints ───────────────────────────────────────────────────
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
