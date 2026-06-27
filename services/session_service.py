from config import supabase
from datetime import datetime, timezone


def create_session(voucher_code: str, hotspot_code: str, device_mac: str) -> dict | None:
    """Auto-register device if needed, then create a new active session."""

    # Upsert device (insert if not exists, update last_seen if exists)
    supabase.table("devices").upsert({
        "mac_address": device_mac,
        "last_seen": datetime.now(timezone.utc).isoformat()
    }, on_conflict="mac_address").execute()

    # Create the session
    response = supabase.table("sessions").insert({
        "voucher_code": voucher_code,
        "hotspot_code": hotspot_code,
        "device_mac": device_mac,
        "login_time": datetime.now(timezone.utc).isoformat(),
        "active": True
    }).execute()

    return response.data[0] if response.data else None


def end_session(session_id: str) -> bool:
    """Mark a session as ended. Returns False if session not found."""
    check = supabase.table("sessions").select("id").eq("id", session_id).eq("active", True).execute()
    if not check.data:
        return False

    supabase.table("sessions").update({
        "logout_time": datetime.now(timezone.utc).isoformat(),
        "active": False
    }).eq("id", session_id).execute()

    return True


def get_active_session(voucher_code: str, hotspot_code: str) -> dict | None:
    """Find an active session for a voucher+hotspot combination."""
    response = (
        supabase
        .table("sessions")
        .select("*")
        .eq("voucher_code", voucher_code)
        .eq("hotspot_code", hotspot_code)
        .eq("active", True)
        .execute()
    )
    return response.data[0] if response.data else None
