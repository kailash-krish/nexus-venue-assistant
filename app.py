from flask import Flask, jsonify, render_template_string
import json
import os

app = Flask(__name__)

# Basic HTML template for the "User Experience"
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Nexus Venue Assistant</title>
    <style>
        body { font-family: sans-serif; text-align: center; padding: 50px; background: #f4f4f9; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); display: inline-block; }
        h1 { color: #1a73e8; }
        .status { font-weight: bold; color: green; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🏟️ Nexus Venue Assistant</h1>
        <p id="advice">Loading smart recommendations...</p>
        <button onclick="location.reload()">Refresh Live Data</button>
    </div>

    <script>
        fetch('/api/recommend')
            .then(response => response.json())
            .then(data => {
                document.getElementById('advice').innerText = data.recommendation;
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
    with open('stadium_data.json', 'r') as f:
        data = json.load(f)
    
    # Smart logic: Recommend the gate with the shortest wait
    best_gate = min(data['gates'], key=lambda x: x['current_wait_min'])
    
    return jsonify({
        "recommendation": f"Welcome! For the fastest entry, head to {best_gate['id']}. Current wait: {best_gate['current_wait_min']} minutes."
    })

if __name__ == "__main__":
    # Cloud Run requires the app to listen on the port defined by the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)