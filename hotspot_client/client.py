"""
Central PisoWiFi - Hotspot Client
Runs on each PisoWiFi machine.
Talks to the central Flask server to validate vouchers and track sessions.
"""

import time
import uuid
import requests
import threading

# ── Configuration ─────────────────────────────────────────────
SERVER_URL   = "http://127.0.0.1:5000"   # Change to your deployed URL in production
HOTSPOT_CODE = "DAV001"                   # Change per machine
HEARTBEAT_INTERVAL = 60                  # seconds between heartbeats

# Auto-detect this machine's MAC address
def get_mac_address() -> str:
    mac = uuid.getnode()
    return ':'.join(f'{(mac >> i) & 0xff:02x}' for i in reversed(range(0, 48, 8)))

DEVICE_MAC = get_mac_address()


# ── API Calls ──────────────────────────────────────────────────

def login(voucher_code: str) -> dict:
    """Send login request to server. Returns session data or error."""
    try:
        response = requests.post(f"{SERVER_URL}/login", json={
            "voucher_code": voucher_code,
            "hotspot_code": HOTSPOT_CODE,
            "device_mac": DEVICE_MAC
        }, timeout=10)
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Cannot reach server. Check internet connection."}
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Server timed out."}


def heartbeat(session_id: str, voucher_code: str) -> dict:
    """Send heartbeat to deduct 1 minute. Returns remaining time."""
    try:
        response = requests.post(f"{SERVER_URL}/heartbeat", json={
            "session_id": session_id,
            "voucher_code": voucher_code
        }, timeout=10)
        return response.json()
    except Exception:
        return {"success": False, "action": "continue"}  # Keep going on network hiccup


def logout(session_id: str) -> dict:
    """End the session on the server."""
    try:
        response = requests.post(f"{SERVER_URL}/logout", json={
            "session_id": session_id
        }, timeout=10)
        return response.json()
    except Exception:
        return {"success": False, "message": "Logout failed silently."}


# ── Session Manager ────────────────────────────────────────────

class SessionManager:
    """
    Manages a single active WiFi session.
    Runs heartbeat in a background thread every 60 seconds.
    """

    def __init__(self):
        self.session_id    = None
        self.voucher_code  = None
        self.remaining     = 0
        self.active        = False
        self._thread       = None
        self._stop_event   = threading.Event()

    def start(self, session_id: str, voucher_code: str, remaining_minutes: int):
        """Start a session and begin the heartbeat loop."""
        self.session_id   = session_id
        self.voucher_code = voucher_code
        self.remaining    = remaining_minutes
        self.active       = True
        self._stop_event.clear()

        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()

        print(f"\n✅ Internet ON — {remaining_minutes} minutes remaining")
        print("   Press ENTER to logout manually.\n")

    def stop(self, reason="Manual logout"):
        """Stop the session and notify the server."""
        if not self.active:
            return

        self.active = False
        self._stop_event.set()

        print(f"\n🔴 {reason}. Logging out...")
        result = logout(self.session_id)
        if result.get("success"):
            print("   Session ended successfully.")
        else:
            print(f"   Warning: {result.get('message', 'Logout may not have reached server.')}")

        self.session_id   = None
        self.voucher_code = None
        self.remaining    = 0

    def _heartbeat_loop(self):
        """Background thread: sends heartbeat every 60 seconds."""
        while not self._stop_event.wait(HEARTBEAT_INTERVAL):
            if not self.active:
                break

            result = heartbeat(self.session_id, self.voucher_code)

            if not result.get("success"):
                print(f"\n⚠️  Heartbeat failed: {result.get('message', 'Unknown error')}")

            action    = result.get("action", "continue")
            remaining = result.get("remaining_minutes", self.remaining - 1)
            self.remaining = remaining

            if action == "disconnect" or remaining <= 0:
                self.stop(reason="Time expired")
                break
            else:
                print(f"   ⏱  {remaining} minutes remaining")


# ── Main Loop ──────────────────────────────────────────────────

def main():
    print("=" * 45)
    print("  Central PisoWiFi — Hotspot Client")
    print(f"  Hotspot : {HOTSPOT_CODE}")
    print(f"  Device  : {DEVICE_MAC}")
    print(f"  Server  : {SERVER_URL}")
    print("=" * 45)

    session = SessionManager()

    while True:
        if session.active:
            # Wait for manual logout
            input()
            session.stop(reason="Customer logged out")
            print("\n--- Ready for next customer ---\n")
            continue

        # Prompt for voucher
        print("\nEnter voucher code (or 'q' to quit): ", end="")
        voucher_code = input().strip().upper()

        if voucher_code == "Q":
            print("Shutting down client. Goodbye.")
            break

        if not voucher_code:
            continue

        print(f"  Validating {voucher_code}...")
        result = login(voucher_code)

        if result.get("success"):
            session.start(
                session_id      = result["session_id"],
                voucher_code    = result["voucher_code"],
                remaining_minutes = result["remaining_minutes"]
            )
        else:
            print(f"\n❌ {result.get('message', 'Login failed')}")


if __name__ == "__main__":
    main()
