from flask import Flask, jsonify, render_template_string, request
import random
import os
import logging
from typing import List, Dict

# ─── 1. CONSTANTS ───
WALKING_SPEED_M_PER_MIN = 60
MAX_WAIT_SCALING_FACTOR = 50
DEFAULT_PORT = 8080

# ─── 2. LOGGING ───
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ─── 3. GLOBAL PERSISTENCE (Fixes the Randomizer Issue) ───
# Data is generated once and only changes when "Refresh" is explicitly triggered
arena_data = {
    "gates": [],
    "restrooms": [],
    "food": []
}

def generate_arena_telemetry():
    """Generates a fresh set of arena data."""
    arena_data["gates"] = [
        {"id": "Gate A · North",  "distance_m": 120, "wait": random.randint(15, 50)},
        {"id": "Gate B · South",  "distance_m": 230, "wait": random.randint(5,  22)},
        {"id": "Gate C · VIP East", "distance_m": 310, "wait": random.randint(3,  15)}
    ]
    arena_data["restrooms"] = [
        {"name": "Lower Deck", "wait": random.randint(1, 10)},
        {"name": "VIP Lounge", "wait": random.randint(0, 5)},
    ]
    arena_data["food"] = [
        {"name": "Victory Burgers", "wait": random.randint(5, 25)},
        {"name": "Espresso Pit",    "wait": random.randint(1, 8)},
        {"name": "Nacho Libre",      "wait": random.randint(3, 18)},
    ]
    for g in arena_data["gates"]:
        g["score"] = g["wait"] + (g["distance_m"] / WALKING_SPEED_M_PER_MIN)

# Initial data generation
generate_arena_telemetry()

# ─────────────────────────────────────────────────────────────────────────────
#  NEXUS VENUE ASSISTANT | EXACT UI RESTORED (UNTOUCHED PIXELS)
# ─────────────────────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>NEXUS · Venue Intelligence</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet"/>
<style>
  :root {
    --glow-cyan:  #00f5ff;
    --glow-rose:  #ff2d78;
    --glow-amber: #ffaa00;
    --glass-bg:   rgba(255,255,255,0.06);
    --glass-bdr:  rgba(255,255,255,0.14);
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'DM Sans', sans-serif;
    background: #04050f;
    min-height: 100vh;
    overflow-x: hidden;
    color: #e8eaf6;
  }

  .mesh {
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background:
      radial-gradient(ellipse 80% 60% at 10% 20%,  rgba(0,245,255,0.13) 0%, transparent 60%),
      radial-gradient(ellipse 60% 50% at 90% 80%,  rgba(255,45,120,0.12) 0%, transparent 60%),
      radial-gradient(ellipse 70% 40% at 50% 50%,  rgba(80,40,200,0.10) 0%, transparent 70%),
      #04050f;
    animation: meshshift 12s ease-in-out infinite alternate;
  }
  @keyframes meshshift {
    0%   { background-position: 0% 0%, 100% 100%, 50% 50%; }
    100% { background-position: 20% 30%, 80% 60%, 60% 40%; }
  }

  .glass {
    background: var(--glass-bg);
    border: 1px solid var(--glass-bdr);
    backdrop-filter: blur(18px) saturate(160%);
    -webkit-backdrop-filter: blur(18px) saturate(160%);
    border-radius: 20px;
    transition: border-color .3s, box-shadow .3s;
  }
  .glass:hover { border-color: rgba(255,255,255,0.26); }

  .live-pill {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(0,245,255,0.12); border: 1px solid rgba(0,245,255,0.3);
    border-radius: 999px; padding: 4px 14px; font-size: .72rem;
    font-family: 'Syne', sans-serif; font-weight: 700;
    letter-spacing: .1em; text-transform: uppercase; color: var(--glow-cyan);
  }
  .live-dot { width:7px; height:7px; border-radius:50%; background:var(--glow-cyan); animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:.3;} }

  .score-ring { position:relative; display:inline-flex; align-items:center; justify-content:center; }
  .score-ring svg { transform: rotate(-90deg); }
  .score-ring .ring-val {
    position:absolute; font-family:'Syne',sans-serif; font-weight:800; font-size:1.7rem; line-height:1;
  }

  .wait-low  { color:#4ade80; }
  .wait-mid  { color:#fbbf24; }
  .wait-high { color:#f87171; }

  .grad-cyan { background: linear-gradient(135deg,#00f5ff,#00aaff); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
  .grad-rose { background: linear-gradient(135deg,#ff2d78,#ff8c42); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
  .grad-amber{ background: linear-gradient(135deg,#ffaa00,#ff6b35); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }

  .protip-bar { width:4px; border-radius:4px; background:linear-gradient(to bottom,#00f5ff,#7b2ff7); min-height:100%; }

  .btn-refresh {
    background: linear-gradient(135deg,rgba(0,245,255,.15),rgba(123,47,247,.15));
    border: 1px solid rgba(0,245,255,.35);
    color: var(--glow-cyan);
    font-family:'Syne',sans-serif; font-weight:700; font-size:.82rem;
    letter-spacing:.06em; text-transform:uppercase;
    padding: 12px 28px; border-radius:999px; cursor:pointer;
    transition: all .25s; display:inline-flex; align-items:center; gap:8px;
  }
  .btn-refresh:hover {
    background:linear-gradient(135deg,rgba(0,245,255,.28),rgba(123,47,247,.28));
    box-shadow: 0 0 24px rgba(0,245,255,.25);
  }
  .btn-refresh.loading { opacity:.6; pointer-events:none; }

  .fade-in { animation: fadein .55s ease both; }
  @keyframes fadein { from{opacity:0;transform:translateY(14px);} to{opacity:1;transform:translateY(0);} }
  .delay-1{animation-delay:.08s;} .delay-2{animation-delay:.16s;} .delay-3{animation-delay:.24s;}

  .section-title {
    font-family:'Syne',sans-serif; font-size:.7rem; font-weight:700;
    letter-spacing:.14em; text-transform:uppercase; color:rgba(255,255,255,.38);
    margin-bottom:14px;
  }

  .skeleton { background:linear-gradient(90deg,rgba(255,255,255,.05) 25%,rgba(255,255,255,.12) 50%,rgba(255,255,255,.05) 75%); background-size:200% 100%; animation:shimmer 1.4s infinite; border-radius:8px; }
  @keyframes shimmer { 0%{background-position:200% 0;} 100%{background-position:-200% 0;} }

  ::-webkit-scrollbar { width:5px; }
  ::-webkit-scrollbar-track { background:transparent; }
  ::-webkit-scrollbar-thumb { background:rgba(255,255,255,.15); border-radius:9999px; }

  /* ── ADDED TOGGLE STYLE (PREMIUM GLASS) ── */
  .vip-toggle-wrap {
    display: inline-flex; align-items: center; gap: 10px;
    background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);
    border-radius: 999px; padding: 6px 14px; cursor: pointer; transition: 0.3s;
    margin: 16px auto 0 auto;
  }
  .vip-toggle-wrap.active { border-color: #ffaa00; background: rgba(255, 170, 0, 0.1); }
  .vip-track { width: 34px; height: 18px; background: rgba(255,255,255,0.15); border-radius: 20px; position: relative; }
  .vip-toggle-wrap.active .vip-track { background: #ffaa00; }
  .vip-thumb { width: 14px; height: 14px; background: #fff; border-radius: 50%; position: absolute; top: 2px; left: 2px; transition: 0.3s; }
  .vip-toggle-wrap.active .vip-thumb { transform: translateX(16px); }
  .vip-label { font-family: 'Syne'; font-size: 11px; font-weight: 800; color: rgba(255,255,255,0.4); letter-spacing: 1px; }
  .vip-toggle-wrap.active .vip-label { color: #ffaa00; }
</style>
</head>
<body>
<div class="mesh"></div>

<main class="relative z-10 max-w-md mx-auto px-4 py-8 space-y-5">

  <header class="text-center fade-in">
    <div class="flex items-center justify-center gap-2 mb-3">
      <span class="live-pill"><span class="live-dot"></span>Live Intelligence</span>
    </div>
    <h1 class="font-['Syne'] font-extrabold text-4xl tracking-tight mb-1">
      <span class="grad-cyan">NEXUS</span>
    </h1>
    <p class="text-white/40 text-sm font-light tracking-widest uppercase">Antigravity Arena · Crowd OS</p>
    
    <div class="flex justify-center">
      <div id="vip-toggle" class="vip-toggle-wrap" onclick="toggleVip()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ffaa00" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"></path></svg>
        <div class="vip-track"><div class="vip-thumb"></div></div>
        <span class="vip-label">VIP MODE</span>
      </div>
    </div>
  </header>

  <section id="smartnav" class="glass p-5 fade-in delay-1" aria-label="Smart Navigation Recommendations">
    <p class="section-title">Smart Navigation</p>
    <div class="flex gap-4">
      <div class="protip-bar flex-shrink-0"></div>
      <div id="protip-content" class="space-y-2 w-full">
        <div class="skeleton h-5 w-3/4"></div>
        <div class="skeleton h-4 w-full"></div>
      </div>
    </div>
  </section>

  <section class="glass p-5 fade-in delay-2" aria-label="Entry Gate Wait Times">
    <p class="section-title">Entry Gates</p>
    <div id="gates-list" class="space-y-3"></div>
  </section>

  <div class="grid grid-cols-2 gap-4 fade-in delay-3">
    <section class="glass p-4" aria-label="Restroom Availability">
      <p class="section-title">Restrooms</p>
      <div id="restrooms-list" class="space-y-2"></div>
    </section>
    <section class="glass p-4" aria-label="Food and Drink Stalls">
      <p class="section-title">Food & Drinks</p>
      <div id="food-list" class="space-y-2"></div>
    </section>
  </div>

  <section class="glass p-5 flex items-center gap-5 fade-in delay-3" aria-label="Overall Crowd Safety Score">
    <div class="score-ring flex-shrink-0">
      <svg width="84" height="84" viewBox="0 0 84 84">
        <circle cx="42" cy="42" r="36" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="8"/>
        <circle id="score-arc" cx="42" cy="42" r="36" fill="none"
          stroke="url(#arcGrad)" stroke-width="8" stroke-linecap="round"
          stroke-dasharray="226" stroke-dashoffset="226"
          style="transition:stroke-dashoffset 1.2s cubic-bezier(.4,0,.2,1)"/>
        <defs>
          <linearGradient id="arcGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#00f5ff"/>
            <stop offset="100%" stop-color="#7b2ff7"/>
          </linearGradient>
        </defs>
      </svg>
      <span id="score-val" class="score-ring ring-val text-white/90">—</span>
    </div>
    <div>
      <p class="section-title mb-1">Crowd Score</p>
      <p id="score-label" class="font-['Syne'] font-bold text-lg text-white/90">—</p>
      <p id="score-sub" class="text-white/45 text-xs mt-1">Calculating conditions…</p>
    </div>
  </section>

  <div class="text-center pb-4 fade-in delay-3">
    <button id="refresh-btn" class="btn-refresh" onclick="fetchData(true)">
      <i data-lucide="refresh-cw" style="width:15px;height:15px;"></i>
      Refresh Data
    </button>
    <p id="last-updated" class="text-white/25 text-xs mt-3"></p>
  </div>

</main>

<script>
let vipEnabled = false;

function toggleVip() {
  vipEnabled = !vipEnabled;
  document.getElementById('vip-toggle').classList.toggle('active', vipEnabled);
  fetchData(false); // Update recommendations without re-randomizing the numbers
}

function waitClass(w) {
  if (w <= 8)  return 'wait-low';
  if (w <= 18) return 'wait-mid';
  return 'wait-high';
}

function waitLabel(w) {
  if (w <= 8)  return '🟢';
  if (w <= 18) return '🟡';
  return '🔴';
}

async function fetchData(forceRefresh) {
  const btn = document.getElementById('refresh-btn');
  btn.classList.add('loading');
  
  try {
    const res  = await fetch(`/api/recommend?vip=${vipEnabled}&refresh=${forceRefresh}&t=${Date.now()}`);
    const data = await res.json();

    document.getElementById('gates-list').innerHTML = data.gates.map(g => {
        const barW = Math.min(100, (g.wait / 50) * 100);
        const barCol = g.wait <= 8 ? '#4ade80' : g.wait <= 18 ? '#fbbf24' : '#f87171';
        return `
        <div class="flex items-center gap-3 ${g.is_best ? 'opacity-100' : 'opacity-75'}">
            <div class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${g.is_best ? 'bg-cyan-400/20 border border-cyan-400/50' : 'bg-white/5 border border-white/10'}">
                <i data-lucide="door-open" style="width:14px;height:14px;color:${g.is_best ? 'var(--glow-cyan)' : 'rgba(255,255,255,.4)'}"></i>
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex justify-between items-center mb-1">
                    <span class="text-sm font-medium text-white/90 truncate">${g.id}${g.is_best ? ' <span class="text-[10px] ml-1 text-cyan-400 font-bold uppercase">BEST</span>' : ''}</span>
                    <span class="font-bold ${waitClass(g.wait)}">${g.wait}m</span>
                </div>
                <div class="h-1.5 rounded-full bg-white/8 overflow-hidden">
                    <div style="width:${barW}%;background:${barCol};height:100%;border-radius:999px;transition:width 0.6s ease;"></div>
                </div>
            </div>
        </div>`;
    }).join('');

    document.getElementById('restrooms-list').innerHTML = data.restrooms.map(r => `
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0">
          <i data-lucide="toilet" style="width:13px;height:13px;flex-shrink:0;color:rgba(255,255,255,.4)"></i>
          <span class="text-xs text-white/70 truncate">${r.name}</span>
        </div>
        <div class="flex items-center gap-1">${waitLabel(r.wait)} <span class="text-xs font-semibold ${waitClass(r.wait)}">${r.wait}m</span></div>
      </div>`).join('');

    document.getElementById('food-list').innerHTML = data.food.map(f => `
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0">
          <i data-lucide="utensils" style="width:13px;height:13px;flex-shrink:0;color:rgba(255,255,255,.4)"></i>
          <span class="text-xs text-white/70 truncate">${f.name}</span>
        </div>
        <div class="flex items-center gap-1">${waitLabel(f.wait)} <span class="text-xs font-semibold ${waitClass(f.wait)}">${f.wait}m</span></div>
      </div>`).join('');

    document.getElementById('protip-content').innerHTML = `<p class="text-white/90 font-medium text-sm leading-relaxed">${data.protip.headline}</p><p class="text-white/50 text-xs leading-relaxed mt-1">${data.protip.detail}</p><div class="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-400"><i data-lucide="zap" style="width:12px;height:12px;"></i>${data.protip.action}</div>`;

    document.getElementById('score-val').textContent = data.crowd_score;
    document.getElementById('score-arc').style.strokeDashoffset = 226 - (data.crowd_score / 100) * 226;
    
    const lbl = document.getElementById('score-label');
    const sub = document.getElementById('score-sub');
    if (data.crowd_score >= 75) { lbl.textContent = 'Smooth Flow'; sub.textContent = 'Low congestion — great time to move.'; }
    else if (data.crowd_score >= 45) { lbl.textContent = 'Moderate Crowd'; sub.textContent = 'Some bottlenecks. Follow Nexus routing.'; }
    else { lbl.textContent = 'High Congestion'; sub.textContent = 'Peak crowding. Use alternate routes.'; }

    document.getElementById('last-updated').textContent = 'Last updated ' + new Date().toLocaleTimeString();
    if (window.lucide) lucide.createIcons();
  } catch(e) { console.error(e); } finally { btn.classList.remove('loading'); }
}
fetchData(false);
</script>
</body>
</html>"""

def _build_protip(gates: List[Dict], food: List[Dict], vip_mode: bool = False) -> Dict:
    try:
        # Filter for recommendation but don't remove from gate list
        eligible = arena_data["gates"] if vip_mode else [g for g in arena_data["gates"] if "vip" not in g["id"].lower()]
        sorted_eligible = sorted(eligible, key=lambda g: g.get("score", 999))
        best = sorted_eligible[0]
        
        for g in arena_data["gates"]:
            g["is_best"] = (g["id"] == best["id"])
        
        prefix = "👑 VIP Path: " if vip_mode and "vip" in best["id"].lower() else ""
        return {
            "headline": f"{prefix}{best['id']} is optimal.",
            "detail": f"Routing calculated based on your {'VIP' if vip_mode else 'General'} access level.",
            "action": f"Proceed to {best['id']}"
        }
    except Exception as e:
        logger.error(f"Logic Error: {e}")
        return {"headline": "Syncing...", "detail": "Calculating routes."}

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/recommend")
def recommend():
    try:
        # Check if user clicked "Refresh Data"
        if request.args.get("refresh") == "true":
            generate_arena_telemetry()
            
        vip_mode = request.args.get("vip", "false").lower() == "true"
        protip = _build_protip(arena_data["gates"], arena_data["food"], vip_mode=vip_mode)
        
        avg_wait = sum(g["wait"] for g in arena_data["gates"]) / len(arena_data["gates"])
        score = max(0, min(100, round(100 - (avg_wait / MAX_WAIT_SCALING_FACTOR) * 100)))
        
        return jsonify({
            "gates": arena_data["gates"], 
            "restrooms": arena_data["restrooms"], 
            "food": arena_data["food"], 
            "protip": protip, 
            "crowd_score": score
        })
    except Exception as e:
        logger.error(f"Telemetry Failure: {e}")
        return jsonify({"error": "Internal Error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", DEFAULT_PORT)))