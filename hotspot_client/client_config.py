# ── Hotspot Client Configuration ──────────────────────────────
# Edit this file for each PisoWiFi machine you deploy.

# URL of your central Flask server
SERVER_URL = "http://127.0.0.1:5000"
# Production: SERVER_URL = "https://your-app.onrender.com"

# Unique code for this machine (must exist in hotspots table)
HOTSPOT_CODE = "DAV001"

# API key for this hotspot (get this from your hotspots table in Supabase)
# Go to Supabase → Table Editor → hotspots → copy the api_key for this machine
HOTSPOT_API_KEY = "f53ae8bd-bae1-4765-a2ce-f28498329579"

# How often to send heartbeat (seconds)
HEARTBEAT_INTERVAL = 60
