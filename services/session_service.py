from config import supabase
from datetime import datetime, timezone, timedelta


def create_session(voucher_code: str, hotspot_code: str, device_mac: str) -> dict | None:
    """Auto-register device if needed, then create a new active session."""

    # Upsert device
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


def end_all_active_sessions(voucher_code: str) -> int:
    """
    End all active sessions for a voucher.
    Returns the number of sessions ended.
    Used for auto-switch when customer moves to a different hotspot.
    """
    active = (
        supabase.table("sessions")
        .select("id")
        .eq("voucher_code", voucher_code)
        .eq("active", True)
        .execute()
    )

    count = 0
    for s in (active.data or []):
        supabase.table("sessions").update({
            "logout_time": datetime.now(timezone.utc).isoformat(),
            "active": False
        }).eq("id", s["id"]).execute()
        count += 1

    return count


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


def get_any_active_session(voucher_code: str) -> dict | None:
    """Find any active session for a voucher (any hotspot)."""
    response = (
        supabase
        .table("sessions")
        .select("*")
        .eq("voucher_code", voucher_code)
        .eq("active", True)
        .execute()
    )
    return response.data[0] if response.data else None


def check_cooldown(voucher_code: str, new_hotspot_code: str, cooldown_seconds: int = 60) -> bool:
    """
    Check if voucher recently switched hotspots (abuse prevention).
    Returns True if still in cooldown period (should block).
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=cooldown_seconds)).isoformat()

    recent = (
        supabase
        .table("sessions")
        .select("hotspot_code, logout_time")
        .eq("voucher_code", voucher_code)
        .eq("active", False)
        .gte("logout_time", cutoff)
        .execute()
    )

    if not recent.data:
        return False

    # Check if any recent session was from a DIFFERENT hotspot
    for s in recent.data:
        if s["hotspot_code"] != new_hotspot_code:
            return True

    return False
