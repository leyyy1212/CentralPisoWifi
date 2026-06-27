from config import supabase


def get_hotspot_by_code(hotspot_code: str) -> dict | None:
    """Fetch a hotspot by its code."""
    response = (
        supabase
        .table("hotspots")
        .select("*")
        .eq("hotspot_code", hotspot_code.upper())
        .execute()
    )
    return response.data[0] if response.data else None


def is_hotspot_active(hotspot: dict) -> bool:
    """Check if a hotspot is online and active."""
    return hotspot.get("status") == "active"
