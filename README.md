NEXUS · Stadium Intelligence OS 🏟️⚡

NEXUS is a cloud-native, geospatial venue management dashboard designed to optimize crowd flow, reduce queue bottlenecks, and enhance fan experience at mega-events.

This project was built for the Hack2Skill PromptWars, strictly adhering to a <1MB repository limit while delivering a multi-cloud enterprise architecture.

📍 1. Chosen Vertical:

Smart City & Venue Management (Crowd Flow Optimization)
Mega-venues (stadiums, theme parks, airports) suffer from severe crowd imbalances, where one entry gate is overwhelmed while another sits empty. NEXUS solves this by aggregating simulated IoT sensor data into a centralized, AI-driven dashboard that actively routes foot traffic away from high-density bottlenecks using predictive analytics.

🧠 2. Approach and Logic:

The core of NEXUS is the Weighted Multi-Variable Pathfinding Algorithm. Rather than simply routing users to the gate with the shortest current line, NEXUS calculates a Composite Efficiency Score for every route.

The logic evaluates five factors:

Queue Wait Time: Current base wait at the gate.

Transit Distance: Walking time from a central reference point.

Crowd Velocity Penalty: How dense crowds slow down physical walking speed near the gate.

Historical Decay Bonus: Exponential decay algorithm rewarding gates whose lines are actively trending downward.

Predictive Arrival Penalty: Simulates inbound foot traffic to penalize gates that look empty now, but are about to surge.

Architectural Approach: To maintain the strict 1MB repository constraint, we completely avoided heavy SDKs (like firebase-admin or google-cloud-core). Instead, the backend relies on highly optimized REST APIs (requests) to communicate with Google Cloud services, ensuring the footprint remains microscopic while the cloud capability remains massive.

⚙️ 3. How the Solution Works:

NEXUS operates on a decoupled Client-Server architecture, heavily integrated with the Google Cloud ecosystem.

The Backend (Flask): Acts as the API gateway. It polls simulated stadium hardware, calculates the pathfinding logic, and manages state.

State Persistence (Firebase RTDB): Telemetry data (Gates, Restrooms, Dining) is written to a Firebase Realtime Database via REST, allowing state to persist across server reloads.

AI Intelligence (Gemini 2.5 Flash): The backend feeds the calculated telemetry to the Gemini API, which dynamically generates conversational "ProTips" and routing advice for the dashboard.

Global Accessibility (Cloud Translation API): A toggle in the UI fires a REST call to Google Cloud Translation, instantly localizing the entire dashboard (Gate names, AI tips, UI elements) from English to Spanish.

The Frontend (Vanilla JS + Tailwind): Features a responsive "Aero-Glass" UI that shifts from a mobile "Field-Ops" view to a side-by-side desktop "Command Center".

Geospatial Visualization (Google Maps API): Renders a real-time crowd heatmap. The map dynamically switches between dark and light themes corresponding to the OS toggle.

📌 4. Assumptions Made:

To scope this project for a hackathon environment, the following assumptions were made:

Hardware Abstraction: We assume the venue already has physical turnstile IoT sensors, LiDAR crowd-density cameras, and POS systems. Since we lack physical hardware, telemetry.py simulates this live data stream.

Constant Walking Speed: The algorithm assumes an average pedestrian walking speed of ~60 meters per minute, which scales down proportionally as crowd density increases.

Location Data: The application hardcodes the geospatial coordinates to a fictional "Antigravity Arena" (Lat: 40.8128, Lng: -74.0743) for the sake of the heatmap visualization.

VIP Routing: We assume VIP ticket holders have dedicated lanes that bypass the standard mathematical queue modeling, resulting in universally lower baseline wait times.
