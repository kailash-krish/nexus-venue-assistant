"""
NEXUS · utils/telemetry.py
==========================
Persistent Telemetry State Engine.

Simulates live IoT sensor data from stadium hardware. In production this
layer would subscribe to a Firestore / Pub-Sub stream; for the hackathon
demo it maintains a global in-memory state that prevents UI flickering
between reloads (data only refreshes on an explicit force-sync).

Algorithm: Weighted Multi-Variable Pathfinding
----------------------------------------------
  composite_score = wait_time
                  + (distance_m / WALKING_SPEED_M_PER_MIN)   # walk penalty
                  + crowd_velocity_penalty                    # density factor
                  + historical_decay_bonus                    # recency weight
"""

from __future__ import annotations

import logging
import math
import random
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("NEXUS-TELEMETRY")

# ── Physics Constants ────────────────────────────────────────────────────────

WALKING_SPEED_M_PER_MIN: float = 60.0   # avg pedestrian: 5 km/h ≈ 83 m/min (reduced for crowds)
MAX_WAIT_SCALING_FACTOR: int   = 50     # wait ceiling used for crowd-score normalisation
VELOCITY_WEIGHT: float         = 0.35   # influence of crowd density on composite score
DECAY_HALF_LIFE_MIN: float     = 8.0    # historical wait decays over this window (mins)

# ── Arena Coordinates ────────────────────────────────────────────────────────

ARENA_LAT: float = 40.8128
ARENA_LNG: float = -74.0743

# ── Persistent Global State ──────────────────────────────────────────────────

arena_state: Dict[str, Any] = {
    "telemetry_id":   0,
    "last_updated":   0.0,
    "gates":          [],
    "restrooms":      [],
    "food_services":  [],
    # Stores the last N wait measurements per gate for decay calculation
    "_history":       {},
}


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _crowd_velocity_penalty(wait: int, distance_m: int) -> float:
    """
    Estimate how crowd density near a gate inflates effective travel time.

    Higher wait → denser crowd → slower walking speed near the gate.
    Returns an additive minute penalty.

    Args:
        wait:        Simulated queue wait time in minutes.
        distance_m:  Gate distance from reference point in metres.

    Returns:
        Float penalty in minutes.
    """
    density_ratio = wait / MAX_WAIT_SCALING_FACTOR          # 0.0 – 1.0
    approach_slowdown = density_ratio * (distance_m / 200)  # heavier far away
    return round(approach_slowdown * VELOCITY_WEIGHT, 2)


def _historical_decay_bonus(gate_id: str, current_wait: int) -> float:
    """
    Compute a recency-weighted bonus that rewards gates whose queues are
    trending downward.  Uses exponential decay over DECAY_HALF_LIFE_MIN.

    Args:
        gate_id:       Unique gate identifier string.
        current_wait:  Latest observed wait time in minutes.

    Returns:
        Float score adjustment (negative = bonus, positive = penalty).
    """
    history: List[tuple[float, int]] = arena_state["_history"].get(gate_id, [])
    if len(history) < 2:
        return 0.0

    prev_time, prev_wait = history[-1]
    elapsed = (time.time() - prev_time) / 60.0          # convert to minutes
    decay_factor = math.exp(-elapsed / DECAY_HALF_LIFE_MIN)
    trend = (current_wait - prev_wait) * decay_factor   # positive = getting worse
    return round(trend * 0.5, 2)


def _record_history(gate_id: str, wait: int) -> None:
    """Append a (timestamp, wait) sample to the rolling history buffer."""
    buf = arena_state["_history"].setdefault(gate_id, [])
    buf.append((time.time(), wait))
    if len(buf) > 10:   # keep last 10 samples
        buf.pop(0)


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────

def sync_arena_telemetry() -> None:
    """
    Simulate a hardware handshake with all arena IoT sensors.

    Refreshes gate, restroom, and food-service wait times in-place using
    the composite pathfinding score so the recommendation engine always has
    pre-computed values ready.

    Side-effects:
        Mutates the global `arena_state` dict.
    """
    logger.info("NEXUS-ENGINE: Initiating full telemetry sync (id=%d)", arena_state["telemetry_id"] + 1)

    arena_state["telemetry_id"] += 1
    arena_state["last_updated"] = time.time()

    # ── Gate Telemetry ────────────────────────────────────────────────────────
    raw_gates = [
        {"id": "Gate A · North Concourse", "distance_m": 120, "lat": 40.8140, "lng": -74.0750, "type": "GA",  "wait": random.randint(18, 45)},
        {"id": "Gate B · South Entry",     "distance_m": 230, "lat": 40.8120, "lng": -74.0740, "type": "GA",  "wait": random.randint(5,  18)},
        {"id": "Gate C · VIP East Deck",   "distance_m": 310, "lat": 40.8130, "lng": -74.0730, "type": "VIP", "wait": random.randint(2,   8)},
    ]

    for g in raw_gates:
        gid   = g["id"]
        wait  = g["wait"]
        dist  = g["distance_m"]

        walk_time = dist / WALKING_SPEED_M_PER_MIN
        vel_pen   = _crowd_velocity_penalty(wait, dist)
        decay_adj = _historical_decay_bonus(gid, wait)

        raw_score = wait + walk_time + vel_pen + decay_adj
        g["efficiency_score"] = round(max(wait, raw_score), 2)
        g["is_best"]          = False   # resolved in recommendation engine
        g["walk_min"]         = round(walk_time, 1)
        g["vel_penalty"]      = vel_pen

        _record_history(gid, wait)

    arena_state["gates"] = raw_gates

    # ── Restroom Telemetry ────────────────────────────────────────────────────
    arena_state["restrooms"] = [
        {"name": "Lower Deck A",       "wait": random.randint(1, 10), "status": "Clean"},
        {"name": "VIP Lounge North",   "wait": random.randint(0,  4), "status": "Premium"},
        {"name": "Upper Concourse B",  "wait": random.randint(2, 14), "status": "Clean"},
    ]

    # ── Food Service Telemetry ────────────────────────────────────────────────
    arena_state["food_services"] = [
        {"name": "Victory Burgers",    "wait": random.randint(10, 30), "popularity": "High"},
        {"name": "Espresso Pit Stop",  "wait": random.randint(2,   8), "popularity": "Medium"},
        {"name": "Nacho Libre Tacos",  "wait": random.randint(5,  15), "popularity": "Medium"},
        {"name": "Quick-Sip Bar",      "wait": random.randint(1,   6), "popularity": "Low"},
    ]

    logger.info(
        "NEXUS-ENGINE: Sync complete — gates=%d restrooms=%d food=%d",
        len(arena_state["gates"]),
        len(arena_state["restrooms"]),
        len(arena_state["food_services"]),
    )


def build_recommendation(vip_enabled: bool = False) -> Dict[str, str]:
    """
    Determine optimal fan routing using the composite efficiency scores.

    When ``vip_enabled`` is False, VIP-type gates are excluded from
    consideration (they remain visible in the gate list but never receive
    the OPTIMAL badge).

    Args:
        vip_enabled: Whether the requesting user has VIP access unlocked.

    Returns:
        Dictionary with ``headline``, ``detail``, and ``action`` strings.
    """
    try:
        eligible: List[Dict[str, Any]] = (
            arena_state["gates"]
            if vip_enabled
            else [g for g in arena_state["gates"] if g["type"] != "VIP"]
        )

        if not eligible:
            eligible = arena_state["gates"]   # safety fallback

        best = min(eligible, key=lambda g: g["efficiency_score"])

        # Mark is_best across the full gate list
        for g in arena_state["gates"]:
            g["is_best"] = g["id"] == best["id"]

        alt_gates = [g for g in eligible if g["id"] != best["id"]]
        alt: Optional[Dict[str, Any]] = min(alt_gates, key=lambda g: g["efficiency_score"]) if alt_gates else None

        vip_prefix = "👑 VIP Routing Active — " if (vip_enabled and best["type"] == "VIP") else ""

        # ── Narrative generation ──────────────────────────────────────────────
        if alt:
            wait_delta = alt["wait"] - best["wait"]
            dist_delta = best["distance_m"] - alt["distance_m"]

            if wait_delta >= 8 and dist_delta < 100:
                headline = f"{vip_prefix}{best['id']} is {wait_delta} mins faster."
                detail   = (
                    f"NEXUS composite score: {best['efficiency_score']} vs {alt['efficiency_score']}. "
                    f"Crowd velocity penalty factored in. Move now — queue is trending clear."
                )
            elif abs(wait_delta) <= 3 and dist_delta < -80:
                headline = f"{vip_prefix}{best['id']} vs {alt['id']}: near-identical queues."
                detail   = (
                    f"{alt['id']} is {abs(dist_delta)}m closer. NEXUS recommends it for "
                    f"total transit savings ({alt['efficiency_score']} min score)."
                )
            else:
                headline = f"{vip_prefix}{best['id']} is your optimal route."
                detail   = (
                    f"Composite score: {best['efficiency_score']} mins (wait + walk + density). "
                    f"Saves ~{round(alt['efficiency_score'] - best['efficiency_score'], 1)} mins vs next best."
                )
        else:
            headline = f"{vip_prefix}{best['id']} is optimal."
            detail   = f"Composite score: {best['efficiency_score']} mins total transit time."

        return {
            "headline": headline,
            "detail":   detail,
            "action":   f"Navigate to {best['id']}",
        }

    except Exception as exc:
        logger.error("Recommendation engine failure: %s", exc)
        return {
            "headline": "Intelligence System Syncing",
            "detail":   "Recalculating safest routes…",
            "action":   "Stand by",
        }


def crowd_score() -> int:
    """
    Compute a 0-100 crowd-flow score (higher = less congested).

    Returns:
        Integer crowd score.
    """
    if not arena_state["gates"]:
        return 50
    avg_wait = sum(g["wait"] for g in arena_state["gates"]) / len(arena_state["gates"])
    return max(0, min(100, round(100 - (avg_wait / MAX_WAIT_SCALING_FACTOR) * 100)))


# Boot-time acquisition
sync_arena_telemetry()
