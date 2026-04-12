import json

def get_recommendation(user_lat, user_lng):
    with open('stadium_data.json', 'r') as f:
        data = json.load(f)
    
    # Simple logic: Find the gate with the shortest wait time
    best_gate = min(data['gates'], key=lambda x: x['current_wait_min'])
    
    return f"Welcome to {data['stadium_name']}! Avoid the crowds at Gate A. Head to {best_gate['id']} for a {best_gate['current_wait_min']} minute wait."

if __name__ == "__main__":
    # Simulating a user arriving
    print(get_recommendation(40.7581, -73.9854))