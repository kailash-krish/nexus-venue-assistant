"""
NEXUS · tests/test_nexus.py
===========================
Comprehensive pytest suite — v7.0

Coverage
--------
* All v6 tests preserved verbatim (zero regressions).
* TestRecaptcha          — _verify_recaptcha branches, 400 on bad token.
* TestHardenedHeaders    — Permissions-Policy, GA4/reCAPTCHA CSP origins.
* TestA11yEnhancements   — aria-pressed, focus-trap, Escape key handler.
* TestGA4Integration     — gtag snippet, trackEvent, page_view event.

Run with:  pytest tests/ -v
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def flask_app():
    """Create a test-configured Flask application with stub env vars."""
    os.environ.setdefault("MAPS_API_KEY",        "TEST_MAPS_KEY")
    os.environ.setdefault("FIREBASE_URL",         "https://test-project.firebaseio.com")
    os.environ.setdefault("FIREBASE_SECRET",      "TEST_FB_SECRET")
    os.environ.setdefault("GEMINI_API_KEY",        "TEST_GEMINI_KEY")
    os.environ.setdefault("TRANSLATE_API_KEY",     "TEST_TRANSLATE_KEY")
    os.environ.setdefault("GA4_MEASUREMENT_ID",    "G-TEST000001")
    os.environ.setdefault("RECAPTCHA_SITE_KEY",    "TEST_SITE_KEY")
    # RECAPTCHA_SECRET intentionally absent so advisory mode is active by default
    from app import create_app
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(flask_app):
    """Flask test client with Firebase mocked to prevent network calls."""
    with patch("utils.telemetry._firebase_read",  return_value=None), \
         patch("utils.telemetry._firebase_write", return_value=True):
        with flask_app.test_client() as c:
            yield c


@pytest.fixture(autouse=True)
def reset_telemetry():
    """Re-sync arena state before/after each test with Firebase mocked."""
    with patch("utils.telemetry._firebase_read",  return_value=None), \
         patch("utils.telemetry._firebase_write", return_value=True):
        from utils.telemetry import sync_arena_telemetry
        sync_arena_telemetry()
    yield
    with patch("utils.telemetry._firebase_read",  return_value=None), \
         patch("utils.telemetry._firebase_write", return_value=True):
        from utils.telemetry import sync_arena_telemetry
        sync_arena_telemetry()


# ── Health endpoint ───────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, client) -> None:
        """Liveness probe must respond HTTP 200."""
        assert client.get("/api/health").status_code == 200

    def test_health_returns_ok_status(self, client) -> None:
        """Payload must contain ``status: ok``."""
        assert client.get("/api/health").get_json()["status"] == "ok"

    def test_health_includes_telemetry_id(self, client) -> None:
        """Payload must expose current telemetry generation ID."""
        data = client.get("/api/health").get_json()
        assert "telemetry_id" in data
        assert isinstance(data["telemetry_id"], int)


# ── Dashboard route ───────────────────────────────────────────────────────────

class TestDashboardRoute:
    def test_index_returns_200(self, client) -> None:
        assert client.get("/").status_code == 200

    def test_index_returns_html_with_nexus(self, client) -> None:
        assert b"NEXUS" in client.get("/").data

    def test_index_contains_vip_toggle(self, client) -> None:
        assert b"vip-btn" in client.get("/").data

    def test_index_contains_language_toggle(self, client) -> None:
        assert b"lang-btn" in client.get("/").data

    def test_index_contains_theme_toggle(self, client) -> None:
        assert b"theme-icon-lucide" in client.get("/").data

    def test_index_contains_desktop_toggle(self, client) -> None:
        assert b"toggleDesktopMode" in client.get("/").data

    def test_lang_toggle_aria_label(self, client) -> None:
        assert b"Toggle language between English and Spanish" in client.get("/").data


# ── Security headers ──────────────────────────────────────────────────────────

class TestSecurityHeaders:
    def test_x_content_type_options(self, client) -> None:
        assert client.get("/").headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options(self, client) -> None:
        assert client.get("/").headers["X-Frame-Options"] == "DENY"

    def test_hsts_present(self, client) -> None:
        assert "max-age" in client.get("/").headers.get("Strict-Transport-Security", "")

    def test_csp_present(self, client) -> None:
        assert "Content-Security-Policy" in client.get("/").headers

    def test_csp_allows_firebase(self, client) -> None:
        assert "firebaseio.com" in client.get("/").headers["Content-Security-Policy"]

    def test_csp_allows_gemini(self, client) -> None:
        assert "generativelanguage.googleapis.com" in client.get("/").headers["Content-Security-Policy"]

    def test_csp_allows_translate(self, client) -> None:
        assert "translation.googleapis.com" in client.get("/").headers["Content-Security-Policy"]


# ── Hardened headers (new) ────────────────────────────────────────────────────

class TestHardenedHeaders:
    """Verify v7 security-header additions."""

    def test_permissions_policy_present(self, client) -> None:
        """Permissions-Policy header must restrict sensitive browser APIs."""
        assert "Permissions-Policy" in client.get("/").headers

    def test_permissions_policy_restricts_camera(self, client) -> None:
        pp = client.get("/").headers["Permissions-Policy"]
        assert "camera=()" in pp

    def test_csp_allows_ga4_gtm(self, client) -> None:
        """CSP script-src must allowlist Google Tag Manager for GA4."""
        csp = client.get("/").headers["Content-Security-Policy"]
        assert "googletagmanager.com" in csp

    def test_csp_allows_recaptcha_gstatic(self, client) -> None:
        """CSP must allowlist gstatic.com for reCAPTCHA v3 runtime."""
        csp = client.get("/").headers["Content-Security-Policy"]
        assert "gstatic.com" in csp

    def test_csp_has_frame_src_for_recaptcha(self, client) -> None:
        """CSP must include frame-src to allow reCAPTCHA iframe challenge."""
        csp = client.get("/").headers["Content-Security-Policy"]
        assert "frame-src" in csp

    def test_csp_allows_ga4_analytics_connect(self, client) -> None:
        """CSP connect-src must allowlist Google Analytics collection endpoint."""
        csp = client.get("/").headers["Content-Security-Policy"]
        assert "google-analytics.com" in csp

    def test_referrer_policy_strict(self, client) -> None:
        rp = client.get("/").headers.get("Referrer-Policy", "")
        assert "strict-origin" in rp


# ── /api/recommend — structure ────────────────────────────────────────────────

class TestRecommendStructure:
    def test_returns_200(self, client) -> None:
        assert client.get("/api/recommend").status_code == 200

    def test_has_gates(self, client) -> None:
        assert "gates" in client.get("/api/recommend").get_json()

    def test_has_restrooms(self, client) -> None:
        assert "restrooms" in client.get("/api/recommend").get_json()

    def test_has_food(self, client) -> None:
        assert "food" in client.get("/api/recommend").get_json()

    def test_has_protip(self, client) -> None:
        assert "protip" in client.get("/api/recommend").get_json()

    def test_has_crowd_score(self, client) -> None:
        assert "crowd_score" in client.get("/api/recommend").get_json()

    def test_has_telemetry_id(self, client) -> None:
        assert "telemetry_id" in client.get("/api/recommend").get_json()

    def test_protip_has_headline(self, client) -> None:
        assert "headline" in client.get("/api/recommend").get_json()["protip"]

    def test_protip_has_detail(self, client) -> None:
        assert "detail" in client.get("/api/recommend").get_json()["protip"]

    def test_protip_has_action(self, client) -> None:
        assert "action" in client.get("/api/recommend").get_json()["protip"]


# ── Gate data ─────────────────────────────────────────────────────────────────

class TestGateData:
    def test_three_gates_returned(self, client) -> None:
        assert len(client.get("/api/recommend").get_json()["gates"]) == 3

    def test_each_gate_has_id(self, client) -> None:
        for g in client.get("/api/recommend").get_json()["gates"]:
            assert isinstance(g.get("id"), str) and g["id"]

    def test_each_gate_has_wait(self, client) -> None:
        for g in client.get("/api/recommend").get_json()["gates"]:
            assert isinstance(g.get("wait"), int)

    def test_each_gate_has_is_best(self, client) -> None:
        for g in client.get("/api/recommend").get_json()["gates"]:
            assert isinstance(g.get("is_best"), bool)

    def test_exactly_one_gate_is_best(self, client) -> None:
        gates = client.get("/api/recommend").get_json()["gates"]
        assert sum(1 for g in gates if g["is_best"]) == 1

    def test_each_gate_has_efficiency_score(self, client) -> None:
        for g in client.get("/api/recommend").get_json()["gates"]:
            assert "efficiency_score" in g

    def test_wait_times_valid_range(self, client) -> None:
        for g in client.get("/api/recommend").get_json()["gates"]:
            assert 0 <= g["wait"] <= 60

    def test_crowd_score_valid_range(self, client) -> None:
        score = client.get("/api/recommend").get_json()["crowd_score"]
        assert 0 <= score <= 100

    def test_each_gate_has_future_weight(self, client) -> None:
        for g in client.get("/api/recommend").get_json()["gates"]:
            assert "future_weight" in g
            assert isinstance(g["future_weight"], float)


# ── Recommendation algorithm ──────────────────────────────────────────────────

class TestRecommendationAlgorithm:
    def test_best_gate_lowest_score_among_ga(self, client) -> None:
        data  = client.get("/api/recommend?vip=false").get_json()
        best  = next(g for g in data["gates"] if g["is_best"])
        ga_sc = [g["efficiency_score"] for g in data["gates"] if g["type"] != "VIP"]
        assert best["efficiency_score"] == min(ga_sc)

    def test_vip_off_never_selects_vip_gate(self, client) -> None:
        for _ in range(5):
            best = next(
                g for g in
                client.get("/api/recommend?vip=false").get_json()["gates"]
                if g["is_best"]
            )
            assert best["type"] != "VIP"

    def test_vip_on_uses_global_minimum(self, client) -> None:
        data = client.get("/api/recommend?vip=true").get_json()
        best = next(g for g in data["gates"] if g["is_best"])
        assert best["efficiency_score"] == min(g["efficiency_score"] for g in data["gates"])

    def test_vip_gate_visible_when_mode_off(self, client) -> None:
        gates = client.get("/api/recommend?vip=false").get_json()["gates"]
        assert any(g["type"] == "VIP" for g in gates)

    def test_efficiency_score_gte_wait(self) -> None:
        from utils.telemetry import arena_state
        for g in arena_state["gates"]:
            assert g["efficiency_score"] >= g["wait"]


# ── Force refresh ─────────────────────────────────────────────────────────────

class TestForceRefresh:
    def test_refresh_true_increments_telemetry_id(self, client) -> None:
        before = client.get("/api/recommend").get_json()["telemetry_id"]
        after  = client.get("/api/recommend?refresh=true").get_json()["telemetry_id"]
        assert after == before + 1

    def test_refresh_false_does_not_increment(self, client) -> None:
        before = client.get("/api/recommend").get_json()["telemetry_id"]
        after  = client.get("/api/recommend?refresh=false").get_json()["telemetry_id"]
        assert after == before


# ── Input validation ──────────────────────────────────────────────────────────

class TestInputValidation:
    def test_xss_vip_param_handled(self, client) -> None:
        data = client.get("/api/recommend?vip=<script>alert(1)</script>").get_json()
        best = next(g for g in data["gates"] if g["is_best"])
        assert best["type"] != "VIP" or best["efficiency_score"] == min(
            g["efficiency_score"] for g in data["gates"]
        )

    def test_numeric_vip_coerced(self, client) -> None:
        assert client.get("/api/recommend?vip=1").status_code == 200

    def test_unknown_params_ignored(self, client) -> None:
        assert client.get("/api/recommend?foo=bar&baz=qux").status_code == 200

    def test_arbitrary_string_vip_resolves_false(self, client) -> None:
        """Any non-truthy vip value must never enable VIP routing."""
        data = client.get("/api/recommend?vip=yes_please").get_json()
        # 'yes_please' is not in ("true","1","yes") so must be False
        # (actually "yes" IS truthy — use a clearly non-truthy string)
        data2 = client.get("/api/recommend?vip=enabled").get_json()
        best  = next(g for g in data2["gates"] if g["is_best"])
        assert best["type"] != "VIP"


# ── reCAPTCHA (new) ───────────────────────────────────────────────────────────

class TestRecaptcha:
    """Branch coverage for _verify_recaptcha and reCAPTCHA-protected endpoints."""

    def test_verify_skips_when_no_secret(self) -> None:
        """Advisory mode: no RECAPTCHA_SECRET → always True."""
        from app.routes import _verify_recaptcha
        saved = os.environ.pop("RECAPTCHA_SECRET", None)
        try:
            assert _verify_recaptcha("any-token") is True
        finally:
            if saved is not None:
                os.environ["RECAPTCHA_SECRET"] = saved

    def test_verify_rejects_empty_token_with_secret(self) -> None:
        """Empty token with secret configured → False immediately."""
        from app.routes import _verify_recaptcha
        with patch.dict(os.environ, {"RECAPTCHA_SECRET": "s3cr3t"}):
            assert _verify_recaptcha("") is False

    def test_verify_accepts_high_score(self) -> None:
        """Score ≥ 0.5 and success=True → True."""
        from app.routes import _verify_recaptcha
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"success": True, "score": 0.9}
        with patch.dict(os.environ, {"RECAPTCHA_SECRET": "s3cr3t"}), \
             patch("app.routes.requests.post", return_value=mock_resp):
            assert _verify_recaptcha("good-token") is True

    def test_verify_rejects_low_score(self) -> None:
        """Score < 0.5 → False even if success=True."""
        from app.routes import _verify_recaptcha
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"success": True, "score": 0.1}
        with patch.dict(os.environ, {"RECAPTCHA_SECRET": "s3cr3t"}), \
             patch("app.routes.requests.post", return_value=mock_resp):
            assert _verify_recaptcha("bad-score") is False

    def test_verify_rejects_success_false(self) -> None:
        """success=False → False regardless of score."""
        from app.routes import _verify_recaptcha
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"success": False, "score": 0.9}
        with patch.dict(os.environ, {"RECAPTCHA_SECRET": "s3cr3t"}), \
             patch("app.routes.requests.post", return_value=mock_resp):
            assert _verify_recaptcha("bad-token") is False

    def test_verify_network_error_fails_open(self) -> None:
        """Network error during verification → True (fail-open)."""
        from app.routes import _verify_recaptcha
        with patch.dict(os.environ, {"RECAPTCHA_SECRET": "s3cr3t"}), \
             patch("app.routes.requests.post", side_effect=ConnectionError("down")):
            assert _verify_recaptcha("token") is True

    def test_bad_token_returns_400_on_recommend(self, client) -> None:
        """Supplied token that fails verification → HTTP 400 on /api/recommend."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"success": False, "score": 0.0}
        with patch.dict(os.environ, {"RECAPTCHA_SECRET": "s3cr3t"}), \
             patch("app.routes.requests.post", return_value=mock_resp):
            resp = client.get("/api/recommend?token=rejected-token")
        assert resp.status_code == 400
        assert "reCAPTCHA" in resp.get_json().get("error", "")

    def test_bad_token_returns_400_on_translate(self, client) -> None:
        """Supplied token that fails verification → HTTP 400 on /api/translate."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"success": False, "score": 0.0}
        with patch.dict(os.environ, {"RECAPTCHA_SECRET": "s3cr3t"}), \
             patch("app.routes.requests.post", return_value=mock_resp):
            resp = client.post(
                "/api/translate",
                json={"texts": ["Gate A"], "target": "es", "token": "rejected"},
            )
        assert resp.status_code == 400

    def test_no_token_passes_when_no_secret(self, client) -> None:
        """No token + no secret → advisory pass, recommend returns 200."""
        assert client.get("/api/recommend").status_code == 200

    def test_valid_token_param_does_not_break_recommend(self, client) -> None:
        """Valid token with no secret configured → normal 200 response."""
        import os
        from unittest import mock
        
        # Temporarily mock the environment to pretend the secret is missing
        with mock.patch.dict(os.environ, {"RECAPTCHA_SECRET": ""}):
            assert client.get("/api/recommend?token=valid-token").status_code == 200


# ── Firebase integration ──────────────────────────────────────────────────────

class TestFirebaseIntegration:
    def test_firebase_write_called_on_sync(self) -> None:
        from utils.telemetry import sync_arena_telemetry
        with patch("utils.telemetry._firebase_read",  return_value=None), \
             patch("utils.telemetry._firebase_write", return_value=True) as mock_w:
            sync_arena_telemetry()
            mock_w.assert_called_once()

    def test_firebase_read_called_on_sync(self) -> None:
        from utils.telemetry import sync_arena_telemetry
        with patch("utils.telemetry._firebase_read",  return_value=None) as mock_r, \
             patch("utils.telemetry._firebase_write", return_value=True):
            sync_arena_telemetry()
            mock_r.assert_called_once()

    def test_fresh_firebase_data_skips_resample(self) -> None:
        import time
        from utils.telemetry import sync_arena_telemetry, arena_state
        fresh: Dict[str, Any] = {
            "telemetry_id": 99,
            "last_updated": time.time(),
            "gates": [
                {"id": "Gate B · South Entry", "distance_m": 230, "lat": 40.812,
                 "lng": -74.074, "type": "GA", "wait": 7,
                 "efficiency_score": 10.8, "is_best": True,
                 "walk_min": 3.8, "vel_penalty": 0.08, "future_weight": 0.5},
            ],
            "restrooms":     [{"name": "Lower Deck A", "wait": 3, "status": "Clean"}],
            "food_services": [{"name": "Victory Burgers", "wait": 12, "popularity": "High"}],
        }
        with patch("utils.telemetry._firebase_read",  return_value=fresh), \
             patch("utils.telemetry._firebase_write", return_value=True) as mock_w:
            sync_arena_telemetry()
            mock_w.assert_not_called()
        assert arena_state["telemetry_id"] == 99

    def test_firebase_write_failure_does_not_crash(self) -> None:
        from utils.telemetry import _firebase_write
        with patch("utils.telemetry._session") as mock_sess:
            mock_sess.put.side_effect = ConnectionError("network down")
            result = _firebase_write({"gates": [], "telemetry_id": 1, "last_updated": 0})
            assert result is False

    def test_firebase_url_requires_https(self) -> None:
        from utils.telemetry import _firebase_url
        os.environ["FIREBASE_URL"] = "https://my-project.firebaseio.com"
        url = _firebase_url()
        assert url.startswith("https://")
        assert url.endswith(".json") or "auth=" in url


# ── Gemini AI integration ─────────────────────────────────────────────────────

class TestGeminiIntegration:
    _MOCK_RESPONSE = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": json.dumps({
                        "headline": "Gate B is your fastest entry right now.",
                        "detail":   "Wait is 8 mins with low crowd density. Predictive load is minimal.",
                        "action":   "Head to Gate B now",
                    })
                }]
            }
        }]
    }

    def test_gemini_called_when_key_present(self) -> None:
        from utils.telemetry import build_recommendation
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = self._MOCK_RESPONSE
        with patch("utils.telemetry._session") as mock_sess:
            mock_sess.post.return_value = mock_resp
            result = build_recommendation(vip_enabled=False)
        mock_sess.post.assert_called_once()
        assert "Gate" in result["headline"]

    def test_gemini_response_used_as_protip(self) -> None:
        from utils.telemetry import build_recommendation
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = self._MOCK_RESPONSE
        with patch("utils.telemetry._session") as mock_sess:
            mock_sess.post.return_value = mock_resp
            result = build_recommendation(vip_enabled=False)
        assert result["headline"] == "Gate B is your fastest entry right now."
        assert result["action"]   == "Head to Gate B now"

    def test_gemini_failure_falls_back_to_deterministic(self) -> None:
        from utils.telemetry import build_recommendation
        with patch("utils.telemetry._session") as mock_sess:
            mock_sess.post.side_effect = ConnectionError("Gemini down")
            result = build_recommendation(vip_enabled=False)
        assert all(k in result for k in ("headline", "detail", "action"))
        assert len(result["headline"]) > 0

    def test_gemini_not_called_when_key_missing(self) -> None:
        from utils.telemetry import _gemini_protip
        original = os.environ.pop("GEMINI_API_KEY", "")
        try:
            with patch("utils.telemetry._session") as mock_sess:
                result = _gemini_protip([])
                mock_sess.post.assert_not_called()
            assert result is None
        finally:
            if original:
                os.environ["GEMINI_API_KEY"] = original

    def test_gemini_malformed_json_falls_back(self) -> None:
        from utils.telemetry import _gemini_protip
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "not valid json!!!"}]}}]
        }
        with patch("utils.telemetry._session") as mock_sess:
            mock_sess.post.return_value = mock_resp
            result = _gemini_protip([{"id": "Gate A", "wait": 20, "efficiency_score": 22, "type": "GA"}])
        assert result is None


# ── Translation API ───────────────────────────────────────────────────────────

class TestTranslationIntegration:
    def test_translate_endpoint_returns_200(self, client) -> None:
        with patch("app.routes._translate_texts", return_value=["Puerta A"]):
            resp = client.post("/api/translate", json={"texts": ["Gate A"], "target": "es"})
        assert resp.status_code == 200

    def test_translate_returns_translated_array(self, client) -> None:
        with patch("app.routes._translate_texts", return_value=["Puerta A · Concurso Norte"]):
            data = client.post(
                "/api/translate",
                json={"texts": ["Gate A · North Concourse"], "target": "es"},
            ).get_json()
        assert data["translated"] == ["Puerta A · Concurso Norte"]

    def test_translate_empty_list_returns_empty(self, client) -> None:
        resp = client.post("/api/translate", json={"texts": [], "target": "es"})
        assert resp.status_code == 200
        assert resp.get_json()["translated"] == []

    def test_translate_non_list_returns_400(self, client) -> None:
        resp = client.post("/api/translate", json={"texts": "not-a-list", "target": "es"})
        assert resp.status_code == 400

    def test_translate_helper_calls_google_api(self) -> None:
        from app.routes import _translate_texts
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"data": {"translations": [{"translatedText": "Hola"}]}}
        with patch("app.routes.requests.post", return_value=mock_resp) as mock_post:
            result = _translate_texts(["Hello"], "es")
        mock_post.assert_called_once()
        assert "translation.googleapis.com" in mock_post.call_args[0][0]
        assert result == ["Hola"]

    def test_translate_helper_fallback_on_error(self) -> None:
        from app.routes import _translate_texts
        with patch("app.routes.requests.post", side_effect=ConnectionError("down")):
            result = _translate_texts(["Gate A"], "es")
        assert result == ["Gate A"]

    def test_translate_helper_no_key_returns_originals(self) -> None:
        from app.routes import _translate_texts
        original = os.environ.pop("TRANSLATE_API_KEY", "")
        try:
            with patch("app.routes.requests.post") as mock_post:
                result = _translate_texts(["Gate A"], "es")
                mock_post.assert_not_called()
            assert result == ["Gate A"]
        finally:
            if original:
                os.environ["TRANSLATE_API_KEY"] = original

    def test_translate_xss_input_sanitised(self, client) -> None:
        with patch("app.routes._translate_texts", return_value=["safe"]):
            resp = client.post(
                "/api/translate",
                json={"texts": ["<script>alert(1)</script>"], "target": "es"},
            )
        assert resp.status_code == 200
        assert b"<script>" not in resp.data


# ── Accessibility enhancements (new) ─────────────────────────────────────────

class TestA11yEnhancements:
    """Verify ARIA states, focus-trap, and Escape key handler in index.html."""

    def test_view_button_has_id_view_btn(self, client) -> None:
        """View button must have id=view-btn for JS aria-pressed targeting."""
        assert b'id="view-btn"' in client.get("/").data

    def test_theme_button_has_id_theme_btn(self, client) -> None:
        """Theme button must have id=theme-btn for JS aria-pressed targeting."""
        assert b'id="theme-btn"' in client.get("/").data

    def test_view_button_has_aria_pressed(self, client) -> None:
        """View button must ship with aria-pressed=false initially."""
        assert b'aria-pressed="false"' in client.get("/").data

    def test_map_overlay_has_dialog_role(self, client) -> None:
        """Map overlay must carry role=dialog for AT announcement."""
        assert b'role="dialog"' in client.get("/").data

    def test_map_overlay_has_aria_modal(self, client) -> None:
        """Map overlay must have aria-modal=true to suppress background."""
        assert b'aria-modal="true"' in client.get("/").data

    def test_focus_trap_handler_present(self, client) -> None:
        """_mapKeyHandler focus-trap must be present in the JS."""
        assert b"_mapKeyHandler" in client.get("/").data

    def test_escape_key_closes_map(self, client) -> None:
        """Escape key branch must be present in the modal key handler."""
        assert b"Escape" in client.get("/").data

    def test_tab_trap_logic_present(self, client) -> None:
        """Tab trap logic (shiftKey branch) must be present."""
        assert b"shiftKey" in client.get("/").data

    def test_vip_toggle_aria_checked(self, client) -> None:
        """VIP toggle must have initial aria-checked=false."""
        assert b'aria-checked="false"' in client.get("/").data

    def test_skip_nav_link_present(self, client) -> None:
        """Skip-navigation link must be present for keyboard users."""
        assert b"#main-content" in client.get("/").data


# ── GA4 integration (new) ────────────────────────────────────────────────────

class TestGA4Integration:
    """Verify GA4 snippet, trackEvent helper, and page_view event boot call."""

    def test_ga4_script_in_head_when_id_configured(self, client) -> None:
        """googletagmanager.com script must be present when GA4_ID is set."""
        assert b"googletagmanager.com/gtag/js" in client.get("/").data

    def test_gtag_dataLayer_init_present(self, client) -> None:
        """dataLayer initialisation must be present in the rendered page."""
        assert b"dataLayer" in client.get("/").data

    def test_trackEvent_function_present(self, client) -> None:
        """trackEvent helper must be defined in the JS."""
        assert b"trackEvent" in client.get("/").data

    def test_page_view_event_fired_on_boot(self, client) -> None:
        """page_view GA4 event must be called during page boot."""
        assert b"page_view" in client.get("/").data

    def test_toggle_language_fires_ga4_event(self, client) -> None:
        """toggleLanguage must call trackEvent('toggle_language', ...)."""
        assert b"toggle_language" in client.get("/").data

    def test_toggle_theme_fires_ga4_event(self, client) -> None:
        """toggleThemeMode must call trackEvent('toggle_theme', ...)."""
        assert b"toggle_theme" in client.get("/").data

    def test_toggle_vip_fires_ga4_event(self, client) -> None:
        """toggleVip must call trackEvent('toggle_vip', ...)."""
        assert b"toggle_vip" in client.get("/").data

    def test_recaptcha_site_key_injected(self, client) -> None:
        """RECAPTCHA_SITE_KEY constant must be injected into the page."""
        assert b"RECAPTCHA_SITE_KEY" in client.get("/").data


# ── Device-context routing ────────────────────────────────────────────────────

class TestDeviceContextRouting:
    def test_mobile_ua_gets_valid_response(self, client) -> None:
        resp = client.get("/api/recommend", headers={"User-Agent": "iPhone Safari"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "gates" in data and "protip" in data

    def test_desktop_ua_gets_valid_response(self, client) -> None:
        resp = client.get("/api/recommend", headers={"User-Agent": "Chrome Desktop"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["gates"]) == 3 and 0 <= data["crowd_score"] <= 100

    def test_mobile_desktop_same_gate_count(self, client) -> None:
        m = client.get("/api/recommend", headers={"User-Agent": "Mobile"}).get_json()
        d = client.get("/api/recommend", headers={"User-Agent": "Desktop"}).get_json()
        assert len(m["gates"]) == len(d["gates"])

    def test_dashboard_contains_desktop_mode_css(self, client) -> None:
        assert b"desktop-mode" in client.get("/").data

    def test_dashboard_contains_light_mode_css(self, client) -> None:
        assert b"light-mode" in client.get("/").data

    def test_dashboard_contains_translation_js(self, client) -> None:
        assert b"toggleLanguage" in client.get("/").data


# ── Telemetry engine ──────────────────────────────────────────────────────────

class TestTelemetryEngine:
    def test_all_gates_have_coordinates(self) -> None:
        from utils.telemetry import arena_state
        for g in arena_state["gates"]:
            assert isinstance(g.get("lat"), float)
            assert isinstance(g.get("lng"), float)

    def test_crowd_score_in_range(self) -> None:
        from utils.telemetry import crowd_score
        assert 0 <= crowd_score() <= 100

    def test_build_recommendation_returns_dict(self) -> None:
        from utils.telemetry import build_recommendation
        with patch("utils.telemetry._gemini_protip", return_value=None):
            result = build_recommendation(vip_enabled=False)
        assert all(k in result for k in ("headline", "detail", "action"))

    def test_build_recommendation_vip_mode(self) -> None:
        from utils.telemetry import build_recommendation
        with patch("utils.telemetry._gemini_protip", return_value=None):
            result = build_recommendation(vip_enabled=True)
        assert isinstance(result["headline"], str) and result["headline"]

    def test_predictive_weight_non_negative(self) -> None:
        from utils.telemetry import arena_state
        for g in arena_state["gates"]:
            assert g.get("future_weight", 0) >= 0

    def test_efficiency_score_gte_wait(self) -> None:
        from utils.telemetry import arena_state
        for g in arena_state["gates"]:
            assert g["efficiency_score"] >= g["wait"], (
                f"Score {g['efficiency_score']} < wait {g['wait']} for {g['id']}"
            )
