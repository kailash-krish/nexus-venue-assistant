import json

def generate_ai_advice(user_query):
    # Load our "real-time" data
    with open('stadium_data.json', 'r') as f:
        data = json.load(f)
    
    # Logic: Filter concessions for low wait times
    quick_food = [c for c in data['concessions'] if c['wait_time'] <= 5]
    best_gate = min(data['gates'], key=lambda x: x['current_wait_min'])

    # AI Logic (Simulated for Antigravity integration)
    if "hungry" in user_query.lower():
        if quick_food:
            return f"AI Assistant: I see you're hungry! Head to {quick_food[0]['name']}, the wait is only {quick_food[0]['wait_time']} mins."
        else:
            return "AI Assistant: Concessions are busy, but 'Victory Burgers' is your best bet right now."
    
    if "gate" in user_query.lower() or "entry" in user_query.lower():
        return f"AI Assistant: Welcome! Skip the main line. {best_gate['id']} is currently moving fastest with a {best_gate['current_wait_min']} min wait."

    return "AI Assistant: How can I help you navigate the stadium today?"

if __name__ == "__main__":
    # Test the AI response
    print(generate_ai_advice("Where should I enter the stadium?"))
    print(generate_ai_advice("I am hungry!"))