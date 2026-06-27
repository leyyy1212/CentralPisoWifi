# ── Hotspot Client Configuration ──────────────────────────────
# Edit this file for each PisoWiFi machine you deploy.

# URL of your central Flask server
# Local testing:
SERVER_URL = "http://127.0.0.1:5000"
# Production (change after Phase 6 deployment):
# SERVER_URL = "https://your-app.railway.app"

# Unique code for this machine (must exist in hotspots table)
HOTSPOT_CODE = "DAV001"

# How often to send heartbeat (in seconds)
# 60 = deduct 1 minute every minute
HEARTBEAT_INTERVAL = 60
