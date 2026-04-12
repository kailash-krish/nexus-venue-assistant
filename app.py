from flask import Flask, jsonify, render_template_string
import random
import os

app = Flask(__name__)

# Basic HTML template for the "User Experience"
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Nexus Venue Assistant</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; padding: 50px; background: #eef2f7; }
        .card { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); display: inline-block; max-width: 500px; }
        h1 { color: #1a73e8; margin-bottom: 10px; }
        p { font-size: 1.2rem; color: #3c4043; line-height: 1.6; }
        .highlight { font-weight: bold; color: #d93025; }
        button { background: #1a73e8; color: white; border: none; padding: 12px 24px; border-radius: 5px; cursor: pointer; font-size: 1rem; margin-top: 20px; transition: background 0.3s; }
        button:hover { background: #1765cc; }
        .live-tag { display: inline-block; background: #e6f4ea; color: #137333; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="live-tag">● LIVE STADIUM UPDATES</div>
        <h1>🏟️ Nexus Assistant</h1>
        <p id="advice">Optimizing your experience...</p>
        <button onclick="location.reload()">Check Newest Lines</button>
    </div>

    <script>
        // Use a timestamp to bypass browser caching and ensure fresh data
        fetch('/api/recommend?t=' + new Date().getTime())
            .then(response => response.json())
            .then(data => {
                document.getElementById('advice').innerHTML = data.recommendation;
            })
            .catch(err => {
                document.getElementById('advice').innerText = "Unable to load live data. Please try again.";
            });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/recommend')
def recommend():
    """
    Simulates real-time crowd data and applies decision logic.
    In a real-world scenario, this data would come from IoT sensors via Firebase.
    """
    # 1. Simulate the current "vibe" of the stadium gates
    # We generate random wait times to represent fluctuating crowd flow
    gates = [
        {"id": "Gate A (North)", "wait": random.randint(15, 50)},
        {"id": "Gate B (South)", "wait": random.randint(5, 20)},
        {"id": "Gate C (VIP/East)", "wait": random.randint(10, 30)}
    ]
    
    # 2. Logic: Smart Decision Making
    # We pick the gate with the lowest wait time
    best_gate = min(gates, key=lambda x: x['wait'])
    
    # 3. Decision for Concessions
    concessions = [
        {"name": "Victory Burgers", "wait": random.randint(5, 25)},
        {"name": "Quick-Sip Drinks", "wait": random.randint(1, 8)}
    ]
    best_snack = min(concessions, key=lambda x: x['wait'])

    # Format the response for the frontend
    recommendation_text = (
        f"For the fastest entry, head to <span class='highlight'>{best_gate['id']}</span>. "
        f"Current wait is only <strong>{best_gate['wait']} minutes</strong>.<br><br>"
        f"Hungry? <strong>{best_snack['name']}</strong> is currently moving fast ({best_snack['wait']}m wait)!"
    )
    
    return jsonify({
        "recommendation": recommendation_text,
        "raw_data": gates # Optional: useful for debugging
    })

if __name__ == "__main__":
    # Cloud Run dynamic port handling
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)