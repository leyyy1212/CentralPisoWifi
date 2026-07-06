"""
Central PisoWiFi - Hotspot Client
Runs on each PisoWiFi machine.
"""

import time
import uuid
import requests
import threading
from client_config import SERVER_URL, HOTSPOT_CODE, HOTSPOT_API_KEY, HEARTBEAT_INTERVAL

def get_mac_address() -> str:
    mac = uuid.getnode()
    return ':'.join(f'{(mac >> i) & 0xff:02x}' for i in reversed(range(0, 48, 8)))

DEVICE_MAC = get_mac_address()


def login(voucher_code: str) -> dict:
    try:
        response = requests.post(f"{SERVER_URL}/login", json={
            "voucher_code": voucher_code,
            "device_mac": DEVICE_MAC,
            "api_key": HOTSPOT_API_KEY
        }, timeout=10)
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Cannot reach server."}
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Server timed out."}


def heartbeat(session_id: str, voucher_code: str) -> dict:
    try:
        response = requests.post(f"{SERVER_URL}/heartbeat", json={
            "session_id": session_id,
            "voucher_code": voucher_code,
            "api_key": HOTSPOT_API_KEY
        }, timeout=10)
        return response.json()
    except Exception:
        return {"success": False, "action": "continue"}


def logout(session_id: str) -> dict:
    try:
        response = requests.post(f"{SERVER_URL}/logout", json={
            "session_id": session_id,
            "api_key": HOTSPOT_API_KEY
        }, timeout=10)
        return response.json()
    except Exception:
        return {"success": False}


class SessionManager:
    def __init__(self):
        self.session_id   = None
        self.voucher_code = None
        self.remaining    = 0
        self.active       = False
        self._thread      = None
        self._stop_event  = threading.Event()

    def start(self, session_id, voucher_code, remaining_minutes):
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
        if not self.active:
            return
        self.active = False
        self._stop_event.set()
        print(f"\n🔴 {reason}. Logging out...")
        result = logout(self.session_id)
        if result.get("success"):
            print("   Session ended successfully.")
        else:
            print(f"   Warning: logout may not have reached server.")
        self.session_id = self.voucher_code = None
        self.remaining  = 0

    def _heartbeat_loop(self):
        while not self._stop_event.wait(HEARTBEAT_INTERVAL):
            if not self.active:
                break
            result    = heartbeat(self.session_id, self.voucher_code)
            action    = result.get("action", "continue")
            remaining = result.get("remaining_minutes", self.remaining - 1)
            self.remaining = remaining
            if action == "disconnect" or remaining <= 0:
                self.stop(reason="Time expired")
                break
            else:
                print(f"   ⏱  {remaining} minutes remaining")


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
            input()
            session.stop(reason="Customer logged out")
            print("\n--- Ready for next customer ---\n")
            continue

        print("\nEnter voucher code (or 'q' to quit): ", end="")
        voucher_code = input().strip().upper()

        if voucher_code == "Q":
            print("Shutting down. Goodbye.")
            break
        if not voucher_code:
            continue

        print(f"  Validating {voucher_code}...")
        result = login(voucher_code)

        if result.get("success"):
            session.start(
                session_id        = result["session_id"],
                voucher_code      = result["voucher_code"],
                remaining_minutes = result["remaining_minutes"]
            )
        else:
            print(f"\n❌ {result.get('message', 'Login failed')}")

if __name__ == "__main__":
    main()
