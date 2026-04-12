# Nexus-Venue Assistant 🏟️
**Vertical:** Sporting Venue Experience

## 🚀 Approach and Logic
The Nexus-Venue Assistant optimizes the attendee experience by using a **Weighted Decision Engine**. Instead of just showing a map, the system calculates the "Best Path" by weighing:
1. **Real-time Queue Data:** Wait times at gates and concessions.
2. **Crowd Density:** Distributing users to underutilized areas of the stadium.

## 🛠️ How it Works
- `stadium_data.json`: Acts as a real-time digital twin of the venue.
- `main.py`: The core engine that calculates the most efficient entry points.
- `assistant.py`: Uses AI logic to provide natural language guidance to attendees.

## 💡 Assumptions
- Attendees have a mobile device with GPS enabled.
- The stadium provides a data feed of gate wait times (simulated via JSON).