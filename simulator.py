import json
import random
import time

def simulate_stadium_traffic():
    print("🏟️  Starting Real-Time Stadium Simulation...")
    
    try:
        while True:
            # 1. Load the current data
            with open('stadium_data.json', 'r') as f:
                data = json.load(f)

            # 2. Randomly shift wait times (Simulating crowds moving)
            for gate in data['gates']:
                change = random.randint(-2, 5) # Crowds usually grow or shrink slightly
                gate['current_wait_min'] = max(2, gate['current_wait_min'] + change)

            for item in data['concessions']:
                change = random.randint(-3, 3)
                item['wait_time'] = max(1, item['wait_time'] + change)

            # 3. Save the "Updated" data back to the file
            with open('stadium_data.json', 'w') as f:
                json.dump(data, f, indent=4)

            print(f"🔄 Updates synced. Gate B wait is now: {data['gates'][1]['current_wait_min']}m")
            
            # Wait 5 seconds before the next "sensor update"
            time.sleep(5) 
            
    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped.")

if __name__ == "__main__":
    simulate_stadium_traffic()