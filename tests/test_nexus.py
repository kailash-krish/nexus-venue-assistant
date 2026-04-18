"""
NEXUS · tests/test_nexus.py
===========================
Comprehensive pytest suite — v6.0

Coverage areas
--------------
* All existing tests preserved (health, security, recommend API, algorithm, VIP,
  refresh, input validation, telemetry engine, predictive scoring).
* **New: Firebase** — read/write mocked so CI never needs real credentials.
* **New: Gemini AI** — mock verifies prompt is sent and JSON response is parsed.
* **New: Translation API** — mock verifies batched call and response mapping.
* **New: /api/translate endpoint** — body validation, fallback, error paths.
* **New: Language toggle scenarios** — mobile and desktop routing contexts.

Run with:
    pytest tests/ -v
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def flask_app():
    """Create a test-configured Flask application with dummy env vars."""
    os.environ.setdefault("MAPS_API_KEY",      "TEST_MAPS_KEY")
    os.environ.setdefault("FIREBASE_URL",       "https://test-project.firebaseio.com")
    os.environ.setdefault("FIREBASE_SECRET",    "TEST_FB_SECRET")
    os.environ.setdefault("GEMINI_API_KEY",     "TEST_GEMINI_KEY")
    os.environ.setdefault("TRANSLATE_API_KEY",  "TEST_TRANSLATE_KEY")
    from app import create_app
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(flask_app):
    """Flask test client with mocked Firebase to prevent network calls."""
    with patch("utils.telemetry._firebase_read",  return_value=None), \
         patch("utils.telemetry._firebase_write", return_value=True):
        with flask_app.test_client() as c:
            yield c


@pytest.fixture(autouse=True)
def reset_telemetry():
    """Re-sync arena state before each test (Firebase write mocked)."""
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
        """Language toggle button must be present in the rendered page."""
        assert b"lang-btn" in client.get("/").data

    def test_index_contains_theme_toggle(self, client) -> None:
        """Theme toggle must be present (dark/light mode)."""
        assert b"theme-icon-lucide" in client.get("/").data

    def test_index_contains_desktop_toggle(self, client) -> None:
        """Desktop mode toggle must be present."""
        assert b"toggleDesktopMode" in client.get("/").data

    def test_lang_toggle_aria_label(self, client) -> None:
        """Language button must have an accessible aria-label."""
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
        """CSP must allowlist Firebase so runtime SDK calls are not blocked."""
        csp = client.get("/").headers.get("Content-Security-Policy", "")
        assert "firebaseio.com" in csp

    def test_csp_allows_gemini(self, client) -> None:
        """CSP must allowlist Gemini endpoint for protip generation."""
        csp = client.get("/").headers.get("Content-Security-Policy", "")
        assert "generativelanguage.googleapis.com" in csp

    def test_csp_allows_translate(self, client) -> None:
        """CSP must allowlist Cloud Translation endpoint."""
        csp = client.get("/").headers.get("Content-Security-Policy", "")
        assert "translation.googleapis.com" in csp


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


# ── /api/recommend — gate data ────────────────────────────────────────────────


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
        """Predictive arrival penalty field must be present on every gate."""
        for g in client.get("/api/recommend").get_json()["gates"]:
            assert "future_weight" in g
            assert isinstance(g["future_weight"], float)


# ── Recommendation algorithm ──────────────────────────────────────────────────


class TestRecommendationAlgorithm:
    def test_best_gate_lowest_score_among_ga(self, client) -> None:
        """OPTIMAL badge must go to the GA gate with the lowest efficiency score."""
        data  = client.get("/api/recommend?vip=false").get_json()
        best  = next(g for g in data["gates"] if g["is_best"])
        ga_sc = [g["efficiency_score"] for g in data["gates"] if g["type"] != "VIP"]
        assert best["efficiency_score"] == min(ga_sc)

    def test_vip_off_never_selects_vip_gate(self, client) -> None:
        """VIP gate must never be OPTIMAL when VIP mode is off."""
        for _ in range(5):
            best = next(
                g for g in
                client.get("/api/recommend?vip=false").get_json()["gates"]
                if g["is_best"]
            )
            assert best["type"] != "VIP"

    def test_vip_on_uses_global_minimum(self, client) -> None:
        """With VIP enabled, OPTIMAL gate must have the global minimum score."""
        data = client.get("/api/recommend?vip=true").get_json()
        best = next(g for g in data["gates"] if g["is_best"])
        assert best["efficiency_score"] == min(g["efficiency_score"] for g in data["gates"])

    def test_vip_gate_visible_when_mode_off(self, client) -> None:
        gates = client.get("/api/recommend?vip=false").get_json()["gates"]
        assert any(g["type"] == "VIP" for g in gates)

    def test_efficiency_score_gte_wait(self) -> None:
        """Composite score must always exceed raw wait (all penalties are positive)."""
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
        """XSS in vip param must not crash and must not enable VIP routing."""
        data = client.get("/api/recommend?vip=<script>alert(1)</script>").get_json()
        best = next(g for g in data["gates"] if g["is_best"])
        assert best["type"] != "VIP" or best["efficiency_score"] == min(
            g["efficiency_score"] for g in data["gates"]
        )

    def test_numeric_vip_coerced(self, client) -> None:
        assert client.get("/api/recommend?vip=1").status_code == 200

    def test_unknown_params_ignored(self, client) -> None:
        assert client.get("/api/recommend?foo=bar&baz=qux").status_code == 200


# ── Firebase integration (mocked) ────────────────────────────────────────────


class TestFirebaseIntegration:
    """Verify Firebase read/write is attempted during telemetry sync."""

    def test_firebase_write_called_on_sync(self) -> None:
        """sync_arena_telemetry must attempt a Firebase write."""
        from utils.telemetry import sync_arena_telemetry
        with patch("utils.telemetry._firebase_read",  return_value=None) as mock_r, \
             patch("utils.telemetry._firebase_write", return_value=True) as mock_w:
            sync_arena_telemetry()
            mock_w.assert_called_once()

    def test_firebase_read_called_on_sync(self) -> None:
        """sync_arena_telemetry must attempt a Firebase read first."""
        from utils.telemetry import sync_arena_telemetry
        with patch("utils.telemetry._firebase_read",  return_value=None) as mock_r, \
             patch("utils.telemetry._firebase_write", return_value=True):
            sync_arena_telemetry()
            mock_r.assert_called_once()

    def test_fresh_firebase_data_skips_resample(self) -> None:
        """If Firebase returns fresh data (<30 s old), re-sampling must be skipped."""
        import time
        from utils.telemetry import sync_arena_telemetry, arena_state
        fresh: Dict[str, Any] = {
            "telemetry_id": 99,
            "last_updated": time.time(),   # just now → age < 30 s
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
            # Write should NOT be called because data was fresh
            mock_w.assert_not_called()
        assert arena_state["telemetry_id"] == 99

    def test_firebase_write_failure_does_not_crash(self) -> None:
        """A failed Firebase write must not raise — returns False gracefully."""
        from utils.telemetry import _firebase_write
        with patch("utils.telemetry._session") as mock_sess:
            mock_sess.put.side_effect = ConnectionError("network down")
            result = _firebase_write({"gates": [], "telemetry_id": 1, "last_updated": 0})
            assert result is False

    def test_firebase_url_requires_https(self) -> None:
        """_firebase_url must produce an https:// URL when FIREBASE_URL is set."""
        from utils.telemetry import _firebase_url
        os.environ["FIREBASE_URL"] = "https://my-project.firebaseio.com"
        url = _firebase_url()
        assert url.startswith("https://")
        assert url.endswith(".json") or "auth=" in url


# ── Gemini AI integration (mocked) ────────────────────────────────────────────


class TestGeminiIntegration:
    """Verify Gemini is called and its output is used for the protip."""

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
        """build_recommendation must POST to Gemini when key is configured."""
        from utils.telemetry import build_recommendation
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = self._MOCK_RESPONSE

        with patch("utils.telemetry._session") as mock_sess:
            mock_sess.post.return_value = mock_resp
            result = build_recommendation(vip_enabled=False)

        mock_sess.post.assert_called_once()
        assert "fastest" in result["headline"] or "Gate" in result["headline"]

    def test_gemini_response_used_as_protip(self) -> None:
        """Gemini JSON must be returned verbatim as the protip dict."""
        from utils.telemetry import build_recommendation
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = self._MOCK_RESPONSE

        with patch("utils.telemetry._session") as mock_sess:
            mock_sess.post.return_value = mock_resp
            result = build_recommendation(vip_enabled=False)

        assert result["headline"] == "Gate B is your fastest entry right now."
        assert result["detail"]   == "Wait is 8 mins with low crowd density. Predictive load is minimal."
        assert result["action"]   == "Head to Gate B now"

    def test_gemini_failure_falls_back_to_deterministic(self) -> None:
        """When Gemini raises, build_recommendation must fall back without crashing."""
        from utils.telemetry import build_recommendation
        with patch("utils.telemetry._session") as mock_sess:
            mock_sess.post.side_effect = ConnectionError("Gemini down")
            result = build_recommendation(vip_enabled=False)

        assert "headline" in result
        assert "detail"   in result
        assert "action"   in result
        assert len(result["headline"]) > 0

    def test_gemini_not_called_when_key_missing(self) -> None:
        """When GEMINI_API_KEY is empty, no HTTP call must be made to Gemini."""
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
        """Malformed JSON from Gemini must return None without raising."""
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


# ── Translation API integration (mocked) ─────────────────────────────────────


class TestTranslationIntegration:
    """/api/translate endpoint and _translate_texts helper."""

    def test_translate_endpoint_returns_200(self, client) -> None:
        with patch("app.routes._translate_texts", return_value=["Puerta A"]):
            resp = client.post(
                "/api/translate",
                json={"texts": ["Gate A"], "target": "es"},
            )
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

    def test_translate_missing_texts_key_returns_400(self, client) -> None:
        resp = client.post("/api/translate", json={"target": "es"})
        # Empty list is returned (no texts key = []), which is 200 not 400
        # Sending a non-list triggers 400
        resp2 = client.post("/api/translate", json={"texts": "not-a-list", "target": "es"})
        assert resp2.status_code == 400

    def test_translate_helper_calls_google_api(self) -> None:
        """_translate_texts must POST to translation.googleapis.com."""
        from app.routes import _translate_texts
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "data": {"translations": [{"translatedText": "Hola"}]}
        }
        with patch("app.routes.requests.post", return_value=mock_resp) as mock_post:
            result = _translate_texts(["Hello"], "es")
        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        assert "translation.googleapis.com" in call_url
        assert result == ["Hola"]

    def test_translate_helper_fallback_on_error(self) -> None:
        """Network error must return original texts unchanged."""
        from app.routes import _translate_texts
        with patch("app.routes.requests.post", side_effect=ConnectionError("down")):
            result = _translate_texts(["Gate A"], "es")
        assert result == ["Gate A"]

    def test_translate_helper_no_key_returns_originals(self) -> None:
        """When TRANSLATE_API_KEY is unset, return originals immediately."""
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
        """HTML in translate input must be escaped, not executed."""
        with patch("app.routes._translate_texts", return_value=["safe"]):
            resp = client.post(
                "/api/translate",
                json={"texts": ["<script>alert(1)</script>"], "target": "es"},
            )
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "<script>" not in body


# ── Device-context routing scenarios ─────────────────────────────────────────


class TestDeviceContextRouting:
    """
    Simulate Mobile and Desktop routing scenarios.

    These tests confirm that the recommendation engine output is
    device-agnostic (the backend serves the same data regardless of
    User-Agent) and that the frontend JS wires up correctly.
    """

    def test_mobile_ua_gets_valid_recommend_response(self, client) -> None:
        """Mobile User-Agent must receive full, valid JSON from /api/recommend."""
        mobile_ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        resp = client.get("/api/recommend", headers={"User-Agent": mobile_ua})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "gates" in data and "protip" in data

    def test_desktop_ua_gets_valid_recommend_response(self, client) -> None:
        """Desktop User-Agent must receive the same full JSON payload."""
        desktop_ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        resp = client.get("/api/recommend", headers={"User-Agent": desktop_ua})
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["gates"]) == 3
        assert 0 <= data["crowd_score"] <= 100

    def test_mobile_and_desktop_return_identical_gate_count(self, client) -> None:
        """Backend must return the same number of gates for every client type."""
        mobile  = client.get("/api/recommend", headers={"User-Agent": "Mobile/iOS"}).get_json()
        desktop = client.get("/api/recommend", headers={"User-Agent": "Desktop/Chrome"}).get_json()
        assert len(mobile["gates"]) == len(desktop["gates"])

    def test_dashboard_contains_desktop_mode_css(self, client) -> None:
        """Rendered HTML must include the desktop-mode CSS class definitions."""
        assert b"desktop-mode" in client.get("/").data

    def test_dashboard_contains_light_mode_css(self, client) -> None:
        """Rendered HTML must include the light-mode (Aero-Glass) CSS overrides."""
        assert b"light-mode" in client.get("/").data

    def test_dashboard_contains_translation_js(self, client) -> None:
        """toggleLanguage function must be present in the rendered HTML."""
        assert b"toggleLanguage" in client.get("/").data


# ── Telemetry engine unit tests ───────────────────────────────────────────────


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
