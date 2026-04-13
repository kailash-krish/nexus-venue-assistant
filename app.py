"""
NEXUS: ADVANCED VENUE INTELLIGENCE OS (ULTRA BUILD)
==================================================
Version: 4.2.0-PRO
Author: NEXUS Core Intelligence
Environment: Python 3.10+ / Flask / Google Cloud
Dependencies: 
    - flask
    - python-dotenv
    - typing
    - logging

SYSTEM ARCHITECTURE:
-------------------
The NEXUS system operates on a Persistent Telemetry Layer. Unlike standard
prototypes that rely on volatile random numbers, this build utilizes a
Global State Engine to ensure data consistency across multiple client-side
requests. The UI is a Glassmorphic High-Fidelity Dashboard, optimized for
mobile-first venue navigation.

GOOGLE CLOUD INTEGRATION:
------------------------
1. Maps JavaScript API: Used for Geospatial Intelligence.
2. Visualization Library: Implemented for Heatmap Density Analysis.
3. Environment Secrets: Secured via .env for production readiness.
"""

import os
import random
import logging
import time
from typing import List, Dict, Any, Optional

# Industry-standard environment management
# Setup: pip install python-dotenv
try:
    from flask import Flask, jsonify, render_template_string, request
    from dotenv import load_dotenv
except ImportError:
    print("CRITICAL: Missing dependencies. Run 'pip install flask python-dotenv'")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
#  1. CORE ENGINE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Load secure credentials from .env
load_dotenv()

# The system pulls the API key from the environment to prevent credential leaks
# Ensure your .env file contains: MAPS_API_KEY=YOUR_ACTUAL_KEY
MAPS_KEY = os.getenv("MAPS_API_KEY")

# Operational Constants
# These values define the 'Physics' of the venue intelligence algorithm
WALKING_SPEED_M_PER_MIN = 60    # Standardized walking velocity for routing
MAX_WAIT_SCALING_FACTOR = 50    # Baseline for 0% Efficiency Score
ARENA_LAT = 40.8128            # Center Latitude (MetLife Stadium Example)
ARENA_LNG = -74.0743           # Center Longitude
DEFAULT_PORT = 8080            # Cloud Run compatible port

# ─────────────────────────────────────────────────────────────────────────────
#  2. LOGGING & TRACEABILITY
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("NEXUS-ULTRA")

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  3. PERSISTENT DATA LAYER (TELEMETRY ENGINE)
# ─────────────────────────────────────────────────────────────────────────────

# This dictionary acts as our 'Live Database' for the hackathon prototype.
# In a production environment, this would be replaced by a Redis or Firestore stream.
arena_state = {
    "telemetry_id": 0,
    "last_updated": 0,
    "gates": [],
    "restrooms": [],
    "food_services": []
}

def sync_arena_telemetry() -> None:
    """
    Simulates a synchronized handshake with stadium IoT hardware.
    Updates the global state with consistent, non-flickering telemetry.
    """
    logger.info("NEXUS-ENGINE: Initiating telemetry handshake...")
    
    arena_state["telemetry_id"] += 1
    arena_state["last_updated"] = time.time()
    
    # Gates Telemetry: ID, Physical Distance, Wait Time, Coordinates
    # Coordinates are specifically mapped around the Arena Center
    arena_state["gates"] = [
        {
            "id": "Gate A · North Concourse",
            "distance_m": 120,
            "wait": random.randint(18, 45),
            "lat": 40.8140,
            "lng": -74.0750,
            "type": "GA"
        },
        {
            "id": "Gate B · South Entry",
            "distance_m": 230,
            "wait": random.randint(5, 15),
            "lat": 40.8120,
            "lng": -74.0740,
            "type": "GA"
        },
        {
            "id": "Gate C · VIP East Deck",
            "distance_m": 310,
            "wait": random.randint(2, 8),
            "lat": 40.8130,
            "lng": -74.0730,
            "type": "VIP"
        }
    ]

    arena_state["restrooms"] = [
        {"name": "Lower Deck A", "wait": random.randint(1, 10), "status": "Clean"},
        {"name": "VIP Lounge North", "wait": random.randint(0, 4), "status": "Premium"}
    ]

    arena_state["food_services"] = [
        {"name": "Victory Burgers", "wait": random.randint(10, 30), "popularity": "High"},
        {"name": "Espresso Pit Stop", "wait": random.randint(2, 8), "popularity": "Medium"},
        {"name": "Nacho Libre Tacos", "wait": random.randint(5, 15), "popularity": "Medium"}
    ]

    # Calculate Intelligence Scores for every gate
    for g in arena_state["gates"]:
        # Nexus Algorithm: Time (mins) + (Distance / Speed)
        g["efficiency_score"] = g["wait"] + (g["distance_m"] / WALKING_SPEED_M_PER_MIN)

# Boot-time Telemetry Acquisition
sync_arena_telemetry()

# ─────────────────────────────────────────────────────────────────────────────
#  4. MASTER HTML TEMPLATE (THE NEXUS DASHBOARD)
# ─────────────────────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/>
    <title>NEXUS · Venue Intelligence OS</title>
    
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
    
    <script src="https://maps.googleapis.com/maps/api/js?key={{ maps_key }}&libraries=visualization&callback=initMap" async defer></script>

    <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;700&display=swap" rel="stylesheet"/>
    
    <style>
        :root {
            --glow-cyan:  #00f5ff;
            --glow-rose:  #ff2d78;
            --glow-amber: #ffaa00;
            --bg-dark:    #04050f;
            --glass-bg:   rgba(255, 255, 255, 0.06);
            --glass-bdr:  rgba(255, 255, 255, 0.12);
        }

        /* ── Base Styles ── */
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
        
        body {
            font-family: 'DM Sans', sans-serif;
            background-color: var(--bg-dark);
            color: #e8eaf6;
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* ── Animated Visual Background ── */
        .mesh-container {
            position: fixed; inset: 0; z-index: 0; pointer-events: none;
            background: 
                radial-gradient(ellipse 80% 60% at 10% 20%, rgba(0, 245, 255, 0.12) 0%, transparent 60%),
                radial-gradient(ellipse 60% 50% at 90% 80%, rgba(255, 45, 120, 0.1) 0%, transparent 60%),
                var(--bg-dark);
            animation: mesh_drift 15s ease-in-out infinite alternate;
        }

        @keyframes mesh_drift {
            from { background-position: 0% 0%; }
            to { background-position: 10% 15%; }
        }

        /* ── Glassmorphism Core ── */
        .glass {
            background: var(--glass-bg);
            border: 1px solid var(--glass-bdr);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border-radius: 24px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .glass:hover {
            border-color: rgba(255, 255, 255, 0.25);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }

        /* ── UI Elements ── */
        .live-pill {
            display: inline-flex; align-items: center; gap: 8px;
            background: rgba(0, 245, 255, 0.1); border: 1px solid rgba(0, 245, 255, 0.2);
            border-radius: 100px; padding: 6px 16px; font-size: 0.7rem;
            font-family: 'Syne', sans-serif; font-weight: 800; color: var(--glow-cyan);
            letter-spacing: 0.12em; text-transform: uppercase;
        }

        .pulse-dot {
            width: 8px; height: 8px; border-radius: 50%;
            background: var(--glow-cyan); animation: pulse_anim 2s infinite;
        }

        @keyframes pulse_anim {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 245, 255, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(0, 245, 255, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 245, 255, 0); }
        }

        .grad-text-cyan {
            background: linear-gradient(135deg, #00f5ff, #7b2ff7);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }

        .section-header {
            font-family: 'Syne', sans-serif; font-size: 0.75rem; font-weight: 800;
            letter-spacing: 0.15em; text-transform: uppercase; color: rgba(255, 255, 255, 0.35);
            margin-bottom: 16px;
        }

        /* ── VIP Toggle Interface ── */
        .vip-toggle {
            display: flex; align-items: center; gap: 12px;
            background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 100px; padding: 8px 18px; cursor: pointer;
            transition: 0.4s; margin: 20px auto; width: fit-content;
        }

        .vip-toggle.active {
            background: rgba(255, 170, 0, 0.1); border-color: var(--glow-amber);
        }

        .toggle-track {
            width: 36px; height: 18px; background: rgba(255, 255, 255, 0.15);
            border-radius: 20px; position: relative; transition: 0.3s;
        }

        .vip-toggle.active .toggle-track { background: var(--glow-amber); }
        
        .toggle-thumb {
            width: 14px; height: 14px; background: white; border-radius: 50%;
            position: absolute; top: 2px; left: 2px; transition: 0.3s cubic-bezier(0.68, -0.55, 0.27, 1.55);
        }

        .vip-toggle.active .toggle-thumb { transform: translateX(18px); }

        /* ── Map Intelligence Container ── */
        #map-overlay {
            display: none; position: fixed; inset: 0; z-index: 1000;
            background: rgba(4, 5, 15, 0.98); backdrop-filter: blur(30px); padding: 15px;
        }

        #map {
            width: 100%; height: 100%; border-radius: 28px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .map-btn {
            background: rgba(0, 245, 255, 0.1); border: 1px solid rgba(0, 245, 255, 0.3);
            color: var(--glow-cyan); font-family: 'Syne', sans-serif; font-weight: 800;
            padding: 8px 16px; border-radius: 10px; font-size: 0.65rem; transition: 0.2s;
        }

        /* ── Status Colors ── */
        .status-low  { color: #4ade80; }
        .status-mid  { color: #fbbf24; }
        .status-high { color: #f87171; }

        .btn-action {
            background: linear-gradient(135deg, rgba(0, 245, 255, 0.15), rgba(123, 47, 247, 0.15));
            border: 1px solid rgba(0, 245, 255, 0.3); color: var(--glow-cyan);
            font-family: 'Syne', sans-serif; font-weight: 700; border-radius: 100px;
            padding: 14px; width: 100%; cursor: pointer; transition: 0.3s;
        }
    </style>
</head>
<body>
    <div class="mesh-container"></div>

    <div id="map-overlay">
        <div class="glass w-full h-full p-4 flex flex-col relative">
            <button onclick="toggleMap(false)" class="absolute top-6 right-6 z-[1001] bg-white/10 p-2 rounded-full border border-white/20">
                <i data-lucide="x" class="w-5 h-5 text-white/70"></i>
            </button>
            <div class="mb-4">
                <p class="section-header !mb-1">Geospatial Intelligence</p>
                <p class="text-[10px] text-white/40 uppercase tracking-widest">Antigravity Arena · Heatmap v2.0</p>
            </div>
            <div id="map" class="flex-1"></div>
        </div>
    </div>

    <main class="relative z-10 max-w-md mx-auto px-5 py-10 space-y-6">
        
        <header class="text-center space-y-3">
            <div><span class="live-pill"><span class="pulse-dot"></span>Live Arena Sync</span></div>
            <h1 class="font-['Syne'] font-extrabold text-5xl tracking-tighter">
                <span class="grad-text-cyan">NEXUS</span>
            </h1>
            <p class="text-white/30 text-[10px] tracking-[0.4em] uppercase font-bold">Stadium Operations · Intelligence</p>
            
            <div id="vip-btn" class="vip-toggle" onclick="toggleVip()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FFAA00" stroke-width="2.5">
                    <path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"></path>
                </svg>
                <div class="toggle-track"><div class="toggle-thumb"></div></div>
                <span class="text-[11px] font-extrabold text-white/40 tracking-wider">VIP ACCESS</span>
            </div>
        </header>

        <section class="glass p-6">
            <div class="flex justify-between items-start mb-4">
                <p class="section-header !mb-0">Smart Navigation</p>
                <button class="map-btn" onclick="toggleMap(true)">HEATMAP VIEW</button>
            </div>
            <div class="flex gap-4">
                <div class="w-1.5 rounded-full bg-gradient-to-b from-[#00f5ff] to-[#7b2ff7]"></div>
                <div id="narrative-box" class="space-y-2 w-full">
                    <div class="h-4 w-3/4 bg-white/5 animate-pulse rounded"></div>
                    <div class="h-3 w-full bg-white/5 animate-pulse rounded"></div>
                </div>
            </div>
        </section>

        <section class="glass p-6">
            <p class="section-header">Entry Telemetry</p>
            <div id="gates-container" class="space-y-5"></div>
        </section>

        <div class="grid grid-cols-2 gap-4">
            <section class="glass p-5">
                <p class="section-header text-[10px]">Restrooms</p>
                <div id="restrooms-container" class="space-y-3"></div>
            </section>
            <section class="glass p-5">
                <p class="section-header text-[10px]">Dining Stalls</p>
                <div id="food-container" class="space-y-3"></div>
            </section>
        </div>

        <section class="glass p-6 flex items-center justify-between">
            <div class="flex items-center gap-6">
                <div class="relative flex items-center justify-center">
                    <svg width="90" height="90" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="8"/>
                        <circle id="score-arc" cx="50" cy="50" r="42" fill="none" stroke="url(#nexus_grad)" 
                                stroke-width="8" stroke-linecap="round" stroke-dasharray="264" 
                                stroke-dashoffset="264" style="transition: 1.5s cubic-bezier(0.4, 0, 0.2, 1);"/>
                        <defs>
                            <linearGradient id="nexus_grad" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" stop-color="#00f5ff"/>
                                <stop offset="100%" stop-color="#7b2ff7"/>
                            </linearGradient>
                        </defs>
                    </svg>
                    <span id="score-text" class="absolute font-['Syne'] font-extrabold text-2xl text-white">0</span>
                </div>
                <div>
                    <p class="section-header mb-1">Crowd Score</p>
                    <p id="score-desc" class="font-['Syne'] font-bold text-lg text-white/90">Analyzing...</p>
                </div>
            </div>
        </section>

        <div class="text-center pt-2">
            <button class="btn-action" onclick="refreshTelemetry(true)">
                <i data-lucide="refresh-cw" class="w-4 h-4 inline mr-2"></i>
                FORCE TELEMETRY SYNC
            </button>
            <p id="timestamp" class="text-[10px] text-white/20 mt-4 uppercase font-bold tracking-widest"></p>
        </div>

    </main>

    <script>
        let vipEnabled = false;
        let map;
        let heatmap;
        let markers = [];

        /**
         * INITIALIZE MAP WITH ULTRA-NIGHT STYLE
         * Removes generic POI noise (like bus stops/shops) to focus on Arena
         */
        function initMap() {
            const ultraNightStyle = [
                { "elementType": "geometry", "stylers": [{ "color": "#111222" }] },
                { "elementType": "labels.text.fill", "stylers": [{ "color": "#444466" }] },
                { "featureType": "poi", "stylers": [{ "visibility": "off" }] },
                { "featureType": "transit", "stylers": [{ "visibility": "off" }] },
                { "featureType": "road", "elementType": "geometry", "stylers": [{ "color": "#18192d" }] },
                { "featureType": "water", "stylers": [{ "color": "#0a0a1a" }] }
            ];

            map = new google.maps.Map(document.getElementById("map"), {
                center: { lat: 40.8128, lng: -74.0743 },
                zoom: 17,
                disableDefaultUI: true,
                styles: ultraNightStyle
            });
        }

        /**
         * TOGGLE GEOSPATIAL OVERLAY
         */
        function toggleMap(show) {
            const overlay = document.getElementById('map-overlay');
            overlay.style.display = show ? 'block' : 'none';
            if(show) {
                google.maps.event.trigger(map, "resize");
                syncHeatmap();
            }
        }

        /**
         * SYNC GEOSPATIAL HEATMAP
         * Generates density points based on wait times
         */
        function syncHeatmap() {
            // Clean old markers
            markers.forEach(m => m.setMap(null));
            markers = [];

            fetch(`/api/recommend?vip=${vipEnabled}`).then(r => r.json()).then(data => {
                const heatmapData = [];
                
                data.gates.forEach(g => {
                    // Create visual heat points based on wait times
                    heatmapData.push({
                        location: new google.maps.LatLng(g.lat, g.lng),
                        weight: g.wait * 2 // Higher wait = more heat
                    });

                    // Add Interactive Nexus Marker
                    const marker = new google.maps.Marker({
                        position: { lat: g.lat, lng: g.lng },
                        map: map,
                        title: g.id,
                        icon: {
                            path: google.maps.SymbolPath.CIRCLE,
                            scale: 8,
                            fillColor: g.wait <= 15 ? "#00f5ff" : "#ff2d78",
                            fillOpacity: 0.8,
                            strokeWeight: 2,
                            strokeColor: "#ffffff"
                        },
                        label: { text: g.wait + "m", color: "white", fontSize: "10px", fontWeight: "bold" }
                    });
                    markers.push(marker);
                });

                if (heatmap) heatmap.setMap(null);
                heatmap = new google.maps.visualization.HeatmapLayer({
                    data: heatmapData,
                    map: map,
                    radius: 60,
                    opacity: 0.6
                });
            });
        }

        /**
         * VIP MODE TOGGLE
         */
        function toggleVip() {
            vipEnabled = !vipEnabled;
            document.getElementById('vip-btn').classList.toggle('active', vipEnabled);
            refreshTelemetry(false); // Update narrative only
        }

        /**
         * DATA ACQUISITION LOGIC
         */
        async function refreshTelemetry(force) {
            try {
                const res = await fetch(`/api/recommend?vip=${vipEnabled}&refresh=${force}&t=${Date.now()}`);
                const data = await res.json();

                // 1. GATES RENDERING
                document.getElementById('gates-container').innerHTML = data.gates.map(g => {
                    const progress = Math.min(100, (g.wait / 50) * 100);
                    const color = g.wait <= 12 ? '#4ade80' : g.wait <= 25 ? '#fbbf24' : '#f87171';
                    return `
                    <div class="flex items-center gap-4 ${g.is_best ? 'opacity-100' : 'opacity-60'}">
                        <div class="w-10 h-10 rounded-full bg-white/5 border border-white/10 flex items-center justify-center">
                            <i data-lucide="door-open" style="width:16px;height:16px;color:${g.is_best ? 'var(--glow-cyan)' : '#888'}"></i>
                        </div>
                        <div class="flex-1">
                            <div class="flex justify-between items-center mb-1.5">
                                <span class="text-sm font-bold text-white/90">${g.id}${g.is_best ? ' <span class="text-[9px] ml-1 text-cyan-400 border border-cyan-400/30 px-1 rounded">OPTIMAL</span>' : ''}</span>
                                <span class="text-sm font-black ${g.wait <= 12 ? 'status-low' : g.wait <= 25 ? 'status-mid' : 'status-high'}">${g.wait}m</span>
                            </div>
                            <div class="h-1.5 rounded-full bg-white/5 overflow-hidden">
                                <div style="width:${progress}%; background:${color}; height:100%; transition:1.2s cubic-bezier(0.4, 0, 0.2, 1); border-radius:100px;"></div>
                            </div>
                        </div>
                    </div>`;
                }).join('');

                // 2. AMENITIES RENDERING
                document.getElementById('restrooms-container').innerHTML = data.restrooms.map(r => `
                    <div class="flex justify-between items-center text-[11px] font-medium">
                        <div class="flex items-center gap-2"><i data-lucide="toilet" class="w-3.5 h-3.5 opacity-30"></i><span class="text-white/60">${r.name}</span></div>
                        <span class="font-bold text-white/90">${r.wait}m</span>
                    </div>`).join('');

                document.getElementById('food-container').innerHTML = data.food.map(f => `
                    <div class="flex justify-between items-center text-[11px] font-medium">
                        <div class="flex items-center gap-2"><i data-lucide="utensils" class="w-3.5 h-3.5 opacity-30"></i><span class="text-white/60">${f.name}</span></div>
                        <span class="font-bold text-white/90">${f.wait}m</span>
                    </div>`).join('');

                // 3. INTELLIGENCE NARRATIVE
                const protip = data.protip;
                document.getElementById('narrative-box').innerHTML = `
                    <p class="text-white/90 font-bold text-base leading-snug">${protip.headline}</p>
                    <p class="text-white/40 text-xs leading-relaxed font-medium">${protip.detail}</p>
                    <div class="mt-3 text-cyan-400 font-bold text-[10px] uppercase tracking-widest flex items-center">
                        <i data-lucide="zap" class="w-3.5 h-3.5 mr-1.5"></i> ${protip.action}
                    </div>`;

                // 4. SCORE & TIMESTAMP
                document.getElementById('score-text').textContent = data.crowd_score;
                document.getElementById('score-arc').style.strokeDashoffset = 264 - (data.crowd_score / 100) * 264;
                document.getElementById('score-desc').textContent = data.crowd_score >= 65 ? 'Optimal Flow' : 'Moderate Density';
                document.getElementById('timestamp').textContent = 'Last Telemetry Update: ' + new Date().toLocaleTimeString();

                if(window.lucide) lucide.createIcons();
            } catch(e) { console.error("NEXUS CORE ERROR:", e); }
        }

        // Initial Boot
        refreshTelemetry(false);
    </script>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────────────────────
#  5. API ARCHITECTURE (THE BRAINS)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_recommendation(gates: List[Dict], vip_enabled: bool = False) -> Dict[str, str]:
    """
    Core Recommendation Logic. 
    Filters available gates based on user authorization (GA vs VIP).
    """
    try:
        # Standard users are physically prevented from routing through VIP gates
        eligible = arena_state["gates"] if vip_enabled else [g for g in arena_state["gates"] if g["type"] != "VIP"]
        
        # Determine the absolute best path based on efficiency score
        best_gate = min(eligible, key=lambda x: x["efficiency_score"])
        
        # Update global state for UI marker 'BEST'
        for g in arena_state["gates"]:
            g["is_best"] = (g["id"] == best_gate["id"])
            
        auth_msg = "👑 VIP ROUTING ACTIVE: " if vip_enabled and best_gate["type"] == "VIP" else ""
        
        return {
            "headline": f"{auth_msg}{best_gate['id']} is your fastest route.",
            "detail": f"NEXUS calculated a total transit time of {round(best_gate['efficiency_score'])} minutes including the walk.",
            "action": f"NAVIGATE TO {best_gate['id'].upper()}"
        }
    except Exception as e:
        logger.error(f"Recommendation Algorithm Failure: {e}")
        return {"headline": "Intelligence System Offline", "detail": "Synchronizing sensors...", "action": "WAITING"}

@app.route("/")
def index():
    """Renders the high-fidelity NEXUS dashboard."""
    return render_template_string(HTML_TEMPLATE, maps_key=MAPS_KEY)

@app.route("/api/recommend")
def api_recommend():
    """
    Telemetry Service.
    Supports force-refresh for real-time demonstration.
    """
    try:
        # Check for hardware refresh request
        is_refresh = request.args.get("refresh", "false").lower() == "true"
        if is_refresh:
            sync_arena_telemetry()
            
        vip_status = request.args.get("vip", "false").lower() == "true"
        
        # Global Crowd Score Calculation (Weighted average of all gates)
        avg_wait = sum(g["wait"] for g in arena_state["gates"]) / len(arena_state["gates"])
        efficiency_pct = max(0, min(100, round(100 - (avg_wait / MAX_WAIT_SCALING_FACTOR) * 100)))
        
        return jsonify({
            "gates": arena_state["gates"],
            "restrooms": arena_state["restrooms"],
            "food": arena_state["food_services"],
            "protip": _generate_recommendation(arena_state["gates"], vip_enabled=vip_status),
            "crowd_score": efficiency_pct
        })
    except Exception as e:
        logger.critical(f"API DISRUPTION: {e}")
        return jsonify({"error": "Telemetry Service Unavailable"}), 500

# ─────────────────────────────────────────────────────────────────────────────
#  6. EXECUTION HANDLER
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Ensure port is pulled from environment for Cloud Run / Heroku compatibility
    port_id = int(os.environ.get("PORT", DEFAULT_PORT))
    
    logger.info(f"NEXUS-OS starting on port {port_id}")
    app.run(host="0.0.0.0", port=port_id)