from flask import Flask, jsonify, render_template_string
import random
import os

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  NEXUS VENUE ASSISTANT  |  Antigravity Arena
#  Single-file Flask app for Google Cloud Run (≤1 MB)
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
</style>
</head>
<body>
<div class="mesh"></div>

<div class="relative z-10 max-w-md mx-auto px-4 py-8 space-y-5">

  <header class="text-center fade-in">
    <div class="flex items-center justify-center gap-2 mb-3">
      <span class="live-pill"><span class="live-dot"></span>Live Intelligence</span>
    </div>
    <h1 class="font-['Syne'] font-extrabold text-4xl tracking-tight mb-1">
      <span class="grad-cyan">NEXUS</span>
    </h1>
    <p class="text-white/40 text-sm font-light tracking-widest uppercase">Antigravity Arena · Crowd OS</p>
  </header>

  <div id="smartnav" class="glass p-5 fade-in delay-1">
    <p class="section-title">Smart Navigation</p>
    <div class="flex gap-4">
      <div class="protip-bar flex-shrink-0"></div>
      <div id="protip-content" class="space-y-2 w-full">
        <div class="skeleton h-5 w-3/4"></div>
        <div class="skeleton h-4 w-full"></div>
        <div class="skeleton h-4 w-5/6"></div>
      </div>
    </div>
  </div>

  <div class="glass p-5 fade-in delay-2">
    <p class="section-title">Entry Gates</p>
    <div id="gates-list" class="space-y-3">
      <div class="skeleton h-14 w-full"></div>
      <div class="skeleton h-14 w-full"></div>
      <div class="skeleton h-14 w-full"></div>
    </div>
  </div>

  <div class="grid grid-cols-2 gap-4 fade-in delay-3">
    <div class="glass p-4">
      <p class="section-title">Restrooms</p>
      <div id="restrooms-list" class="space-y-2">
        <div class="skeleton h-10 w-full"></div>
        <div class="skeleton h-10 w-full"></div>
      </div>
    </div>
    <div class="glass p-4">
      <p class="section-title">Food & Drinks</p>
      <div id="food-list" class="space-y-2">
        <div class="skeleton h-10 w-full"></div>
        <div class="skeleton h-10 w-full"></div>
      </div>
    </div>
  </div>

  <div class="glass p-5 flex items-center gap-5 fade-in delay-3">
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
  </div>

  <div class="text-center pb-4 fade-in delay-3">
    <button id="refresh-btn" class="btn-refresh" onclick="fetchData()">
      <i data-lucide="refresh-cw" style="width:15px;height:15px;"></i>
      Refresh Data
    </button>
    <p id="last-updated" class="text-white/25 text-xs mt-3"></p>
  </div>

</div>

<script>
// Logic to handle Lucide Icons safely
function initIcons() {
    if (window.lucide) {
        lucide.createIcons();
    }
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

function gateRow(g, isBest) {
  const barW = Math.min(100, (g.wait / 50) * 100);
  const barCol = g.wait <= 8 ? '#4ade80' : g.wait <= 18 ? '#fbbf24' : '#f87171';
  return `
    <div class="flex items-center gap-3 ${isBest ? 'opacity-100' : 'opacity-75'}">
      <div class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
        ${isBest ? 'bg-cyan-400/20 border border-cyan-400/50' : 'bg-white/5 border border-white/10'}">
        <i data-lucide="door-open" style="width:14px;height:14px;color:${isBest ? 'var(--glow-cyan)' : 'rgba(255,255,255,.4)'}"></i>
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex justify-between items-center mb-1">
          <span class="text-sm font-medium text-white/90 truncate">${g.id}${isBest ? ' <span class="text-xs ml-1 text-cyan-400 font-bold">BEST</span>' : ''}</span>
          <span class="font-bold ${waitClass(g.wait)}">${g.wait}m</span>
        </div>
        <div class="h-1.5 rounded-full bg-white/8 overflow-hidden">
          <div style="width:${barW}%;background:${barCol};height:100%;border-radius:999px;transition:width 1s ease;"></div>
        </div>
      </div>
    </div>`;
}

function smallRow(icon, name, wait) {
  return `
    <div class="flex items-center justify-between gap-2">
      <div class="flex items-center gap-2 min-w-0">
        <i data-lucide="${icon}" style="width:13px;height:13px;flex-shrink:0;color:rgba(255,255,255,.4)"></i>
        <span class="text-xs text-white/70 truncate">${name}</span>
      </div>
      <div class="flex items-center gap-1">${waitLabel(wait)} <span class="text-xs font-semibold ${waitClass(wait)}">${wait}m</span></div>
    </div>`;
}

async function fetchData() {
  const btn = document.getElementById('refresh-btn');
  btn.classList.add('loading');
  
  try {
    const res  = await fetch('./api/recommend?t=' + Date.now());
    const data = await res.json();

    document.getElementById('gates-list').innerHTML = data.gates.map(g => gateRow(g, g.is_best)).join('');
    document.getElementById('restrooms-list').innerHTML = data.restrooms.map(r => smallRow('toilet', r.name, r.wait)).join('');
    document.getElementById('food-list').innerHTML = data.food.map(f => smallRow('utensils', f.name, f.wait)).join('');

    const protip = data.protip;
    let protipHtml = `<p class="text-white/90 font-medium text-sm leading-relaxed">${protip.headline}</p>
                      <p class="text-white/50 text-xs leading-relaxed mt-1">${protip.detail}</p>`;
    if (protip.action) {
      protipHtml += `<div class="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-400">
                     <i data-lucide="zap" style="width:12px;height:12px;"></i>${protip.action}</div>`;
    }
    document.getElementById('protip-content').innerHTML = protipHtml;

    const score = data.crowd_score;
    const arc = document.getElementById('score-arc');
    const offset = 226 - (score / 100) * 226;
    arc.style.strokeDashoffset = offset;
    document.getElementById('score-val').textContent = score;
    
    const lbl = document.getElementById('score-label');
    const sub = document.getElementById('score-sub');
    if (score >= 75) {
      lbl.textContent = 'Smooth Flow'; lbl.className = 'font-["Syne"] font-bold text-lg grad-cyan';
      sub.textContent = 'Low congestion — great time to move.';
    } else if (score >= 45) {
      lbl.textContent = 'Moderate Crowd'; lbl.className = 'font-["Syne"] font-bold text-lg grad-amber';
      sub.textContent = 'Some bottlenecks. Follow Nexus routing.';
    } else {
      lbl.textContent = 'High Congestion'; lbl.className = 'font-["Syne"] font-bold text-lg grad-rose';
      sub.textContent = 'Peak crowding. Use alternate routes.';
    }

    document.getElementById('last-updated').textContent = 'Last updated ' + new Date().toLocaleTimeString();
    initIcons();
  } catch(e) {
    document.getElementById('protip-content').innerHTML = '<p class="text-rose-400 text-sm">Offline. Reconnecting...</p>';
  } finally {
    btn.classList.remove('loading');
    initIcons();
  }
}

initIcons();
fetchData();
</script>
</body>
</html>"""

def _build_protip(gates, food):
    sorted_gates = sorted(gates, key=lambda g: g["score"])
    best = sorted_gates[0]
    alt  = sorted_gates[1] if len(sorted_gates) > 1 else None
    time_diff = best["wait"] - alt["wait"] if alt else 0
    dist_diff = best["distance_m"] - alt["distance_m"] if alt else 0
    for g in gates:
        g["is_best"] = (g["id"] == best["id"])
    best_food = min(food, key=lambda f: f["wait"])
    if alt and abs(time_diff) <= 4 and abs(dist_diff) >= 80:
        headline = f"{best['id']} and {alt['id']} are similar."
        detail = f"{best['id']} is {abs(dist_diff)}m closer. Recommended for total speed."
        action = f"Head to {best['id']}"
    elif alt and time_diff <= -5:
        headline = f"{best['id']} is {abs(time_diff)}m faster right now."
        detail = f"Saves real time despite the extra {abs(dist_diff)}m walk."
        action = f"Fast lane: {best['id']}"
    else:
        headline = f"{best['id']} is optimal."
        detail = f"Optimized based on wait ({best['wait']}m) and distance."
        action = f"Proceed to {best['id']}"
    return {"headline": headline, "detail": detail, "action": action, "best_food": best_food["name"]}

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/recommend")
def recommend():
    gates = [
        {"id": "Gate A · North",  "distance_m": 120, "wait": random.randint(15, 50)},
        {"id": "Gate B · South",  "distance_m": 200, "wait": random.randint(5,  22)},
        {"id": "Gate C · VIP East","distance_m": 310, "wait": random.randint(3,  15)},
    ]
    for g in gates:
        g["score"] = g["wait"] + (g["distance_m"] / 60)
        g["is_best"] = False
    restrooms = [
        {"name": "Lower Concourse", "wait": random.randint(1, 12)},
        {"name": "Upper Deck West", "wait": random.randint(1, 8)},
        {"name": "VIP Lounge",      "wait": random.randint(0, 5)},
    ]
    food = [
        {"name": "Victory Burgers",  "wait": random.randint(5, 25)},
        {"name": "Quick-Sip Drinks", "wait": random.randint(1, 8)},
        {"name": "Nacho Libre",      "wait": random.randint(3, 18)},
    ]
    protip = _build_protip(gates, food)
    avg_gate_wait = sum(g["wait"] for g in gates) / len(gates)
    crowd_score = max(0, min(100, round(100 - (avg_gate_wait / 50) * 100)))
    return jsonify({"gates": gates, "restrooms": restrooms, "food": food, "protip": protip, "crowd_score": crowd_score})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)