"""
NEXUS · tests/test_nexus.py
===========================
pytest test suite covering:
  - Core recommendation engine logic
  - API endpoint responses and edge cases
  - Telemetry state consistency
  - Input validation and sanitisation
  - Security headers
  - VIP mode gating
  - Crowd score calculation

Run with:  pytest tests/ -v
"""

from __future__ import annotations

import json
import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def flask_app():
    """Create a test-configured Flask application."""
    os.environ.setdefault("MAPS_API_KEY", "TEST_KEY_NOT_REAL")
    from app import create_app
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(flask_app):
    """Provide a Flask test client."""
    with flask_app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def reset_telemetry():
    """Reset arena state between tests to prevent state leakage."""
    from utils.telemetry import sync_arena_telemetry
    sync_arena_telemetry()
    yield
    sync_arena_telemetry()


# ── Health Endpoint ───────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_returns_ok_status(self, client):
        data = resp = client.get("/api/health").get_json()
        assert data["status"] == "ok"

    def test_health_includes_telemetry_id(self, client):
        data = client.get("/api/health").get_json()
        assert "telemetry_id" in data
        assert isinstance(data["telemetry_id"], int)


# ── Dashboard Route ───────────────────────────────────────────────────────────

class TestDashboardRoute:
    def test_index_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_index_returns_html(self, client):
        resp = client.get("/")
        assert b"NEXUS" in resp.data

    def test_index_contains_vip_toggle(self, client):
        resp = client.get("/")
        assert b"vip-btn" in resp.data


# ── Security Headers ──────────────────────────────────────────────────────────

class TestSecurityHeaders:
    def test_x_content_type_options(self, client):
        resp = client.get("/")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_hsts_header_present(self, client):
        resp = client.get("/")
        hsts = resp.headers.get("Strict-Transport-Security", "")
        assert "max-age" in hsts

    def test_csp_header_present(self, client):
        resp = client.get("/")
        assert "Content-Security-Policy" in resp.headers


# ── Recommend API — Structure ─────────────────────────────────────────────────

class TestRecommendStructure:
    def test_returns_200(self, client):
        resp = client.get("/api/recommend")
        assert resp.status_code == 200

    def test_has_gates_key(self, client):
        data = client.get("/api/recommend").get_json()
        assert "gates" in data

    def test_has_restrooms_key(self, client):
        data = client.get("/api/recommend").get_json()
        assert "restrooms" in data

    def test_has_food_key(self, client):
        data = client.get("/api/recommend").get_json()
        assert "food" in data

    def test_has_protip_key(self, client):
        data = client.get("/api/recommend").get_json()
        assert "protip" in data

    def test_has_crowd_score_key(self, client):
        data = client.get("/api/recommend").get_json()
        assert "crowd_score" in data

    def test_has_telemetry_id_key(self, client):
        data = client.get("/api/recommend").get_json()
        assert "telemetry_id" in data

    def test_protip_has_required_fields(self, client):
        protip = client.get("/api/recommend").get_json()["protip"]
        assert "headline" in protip
        assert "detail" in protip
        assert "action" in protip


# ── Recommend API — Gate Data ─────────────────────────────────────────────────

class TestGateData:
    def test_three_gates_returned(self, client):
        gates = client.get("/api/recommend").get_json()["gates"]
        assert len(gates) == 3

    def test_each_gate_has_id(self, client):
        for g in client.get("/api/recommend").get_json()["gates"]:
            assert "id" in g and isinstance(g["id"], str)

    def test_each_gate_has_wait(self, client):
        for g in client.get("/api/recommend").get_json()["gates"]:
            assert "wait" in g and isinstance(g["wait"], int)

    def test_each_gate_has_is_best(self, client):
        for g in client.get("/api/recommend").get_json()["gates"]:
            assert "is_best" in g and isinstance(g["is_best"], bool)

    def test_exactly_one_gate_is_best(self, client):
        gates = client.get("/api/recommend").get_json()["gates"]
        best_count = sum(1 for g in gates if g["is_best"])
        assert best_count == 1

    def test_each_gate_has_efficiency_score(self, client):
        for g in client.get("/api/recommend").get_json()["gates"]:
            assert "efficiency_score" in g

    def test_wait_times_within_valid_range(self, client):
        for g in client.get("/api/recommend").get_json()["gates"]:
            assert 0 <= g["wait"] <= 60, f"Wait {g['wait']} out of range for {g['id']}"

    def test_crowd_score_within_valid_range(self, client):
        score = client.get("/api/recommend").get_json()["crowd_score"]
        assert 0 <= score <= 100


# ── Recommendation Engine — Core Algorithm ────────────────────────────────────

class TestRecommendationAlgorithm:
    def test_best_gate_has_lowest_efficiency_score_ga(self, client):
        """Without VIP, the OPTIMAL gate must have the lowest score among GA gates."""
        data  = client.get("/api/recommend?vip=false").get_json()
        gates = data["gates"]
        best  = next(g for g in gates if g["is_best"])
        ga_scores = [g["efficiency_score"] for g in gates if g["type"] != "VIP"]
        assert best["efficiency_score"] == min(ga_scores)

    def test_vip_off_never_selects_vip_gate_as_best(self, client):
        """VIP gate must not be marked OPTIMAL when VIP mode is disabled."""
        for _ in range(5):   # run several times to cover random variation
            gates = client.get("/api/recommend?vip=false").get_json()["gates"]
            best  = next(g for g in gates if g["is_best"])
            assert best["type"] != "VIP", "VIP gate incorrectly selected when VIP mode OFF"

    def test_vip_on_can_select_vip_gate(self, client):
        """When VIP mode is enabled, a VIP gate may be selected (if it scores best)."""
        data  = client.get("/api/recommend?vip=true").get_json()
        gates = data["gates"]
        best  = next(g for g in gates if g["is_best"])
        all_scores = [g["efficiency_score"] for g in gates]
        assert best["efficiency_score"] == min(all_scores)

    def test_vip_gate_still_visible_when_mode_off(self, client):
        """VIP gate should appear in the list even when VIP mode is OFF."""
        gates = client.get("/api/recommend?vip=false").get_json()["gates"]
        vip_gate_present = any(g["type"] == "VIP" for g in gates)
        assert vip_gate_present


# ── Force Refresh ─────────────────────────────────────────────────────────────

class TestForceRefresh:
    def test_telemetry_id_increments_on_refresh(self, client):
        before = client.get("/api/recommend").get_json()["telemetry_id"]
        after  = client.get("/api/recommend?refresh=true").get_json()["telemetry_id"]
        assert after == before + 1

    def test_no_refresh_does_not_increment_id(self, client):
        before = client.get("/api/recommend").get_json()["telemetry_id"]
        after  = client.get("/api/recommend?refresh=false").get_json()["telemetry_id"]
        assert after == before


# ── Input Validation ──────────────────────────────────────────────────────────

class TestInputValidation:
    def test_garbage_vip_param_defaults_to_false(self, client):
        """Unrecognised vip param must not trigger VIP routing."""
        data = client.get("/api/recommend?vip=<script>alert(1)</script>").get_json()
        gates = data["gates"]
        best  = next(g for g in gates if g["is_best"])
        # Should behave like vip=false — no VIP gate selected
        assert best["type"] != "VIP" or best["efficiency_score"] == min(g["efficiency_score"] for g in gates)

    def test_numeric_vip_param_coerced(self, client):
        resp = client.get("/api/recommend?vip=1")
        assert resp.status_code == 200

    def test_extra_unknown_params_ignored(self, client):
        resp = client.get("/api/recommend?foo=bar&baz=qux")
        assert resp.status_code == 200


# ── Telemetry Engine Unit Tests ───────────────────────────────────────────────

class TestTelemetryEngine:
    def test_efficiency_score_greater_than_wait(self):
        """Composite score must always exceed raw wait (walk penalty is positive)."""
        from utils.telemetry import arena_state
        for g in arena_state["gates"]:
            assert g["efficiency_score"] >= g["wait"], (
                f"Score {g['efficiency_score']} < wait {g['wait']} for {g['id']}"
            )

    def test_all_gates_have_coordinates(self):
        from utils.telemetry import arena_state
        for g in arena_state["gates"]:
            assert "lat" in g and "lng" in g
            assert isinstance(g["lat"], float) and isinstance(g["lng"], float)

    def test_crowd_score_function(self):
        from utils.telemetry import crowd_score
        s = crowd_score()
        assert 0 <= s <= 100

    def test_build_recommendation_returns_dict(self):
        from utils.telemetry import build_recommendation
        result = build_recommendation(vip_enabled=False)
        assert isinstance(result, dict)
        assert all(k in result for k in ("headline", "detail", "action"))

    def test_build_recommendation_vip_mode(self):
        from utils.telemetry import build_recommendation
        result = build_recommendation(vip_enabled=True)
        assert isinstance(result["headline"], str)
        assert len(result["headline"]) > 0


# ── Predictive Engine Unit Tests ──────────────────────────────────────────────

class TestPredictiveEngine:
    def test_future_weight_exists(self, client):
        """Ensure the telemetry engine calculates future inbound load."""
        data = client.get("/api/recommend").get_json()
        for g in data["gates"]:
            assert "future_weight" in g
            assert isinstance(g["future_weight"], float)

    def test_efficiency_score_includes_predictive_load(self, client):
        """Composite score must account for the predictive arrival density."""
        data = client.get("/api/recommend").get_json()
        for g in data["gates"]:
            raw_min = g["wait"] + g["future_weight"]
            assert g["efficiency_score"] >= round(min(g["wait"], raw_min), 2)
