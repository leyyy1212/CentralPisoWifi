from config import supabase


def get_voucher_by_code(voucher_code: str):
    """Fetch a single voucher by its code."""
    response = (
        supabase
        .table("vouchers")
        .select("*")
        .eq("voucher_code", voucher_code.upper())
        .execute()
    )
    return response.data[0] if response.data else None


def is_voucher_valid(voucher: dict) -> tuple[bool, str]:
    """
    Check if a voucher can be used.
    Returns (True, "") if valid, or (False, reason) if not.
    """
    if voucher["status"].lower() not in ("active",):
        return False, f"Voucher is {voucher['status']}"
    if voucher.get("remaining_seconds", voucher["remaining_minutes"] * 60) <= 0:
        return False, "Voucher has no remaining time"
    return True, ""


def get_remaining_seconds(voucher: dict) -> int:
    """Get accurate remaining seconds from voucher."""
    if voucher.get("remaining_seconds") is not None:
        return voucher["remaining_seconds"]
    return voucher["remaining_minutes"] * 60


def deduct_seconds(voucher_code: str, seconds: int) -> bool:
    """
    Deduct exact seconds from a voucher.
    Updates both remaining_seconds and remaining_minutes.
    Returns True if successful.
    """
    voucher = get_voucher_by_code(voucher_code)
    if not voucher:
        return False

    current_seconds = get_remaining_seconds(voucher)
    new_seconds     = max(0, current_seconds - seconds)
    new_minutes     = max(0, new_seconds // 60)
    new_status      = "exhausted" if new_seconds == 0 else voucher["status"]

    supabase.table("vouchers").update({
        "remaining_seconds": new_seconds,
        "remaining_minutes": new_minutes,
        "status": new_status
    }).eq("voucher_code", voucher_code).execute()

    return True


def deduct_minutes(voucher_code: str, minutes: int) -> bool:
    """Deduct minutes (converts to seconds internally)."""
    return deduct_seconds(voucher_code, minutes * 60)


def sync_seconds(voucher_code: str, remaining_seconds: int) -> bool:
    """
    Sync exact remaining seconds from the client.
    Called on disconnect/logout so the server knows the precise time left.
    """
    voucher = get_voucher_by_code(voucher_code)
    if not voucher:
        return False

    new_seconds = max(0, remaining_seconds)
    new_minutes = max(0, new_seconds // 60)
    new_status  = "exhausted" if new_seconds == 0 else voucher["status"]

    supabase.table("vouchers").update({
        "remaining_seconds": new_seconds,
        "remaining_minutes": new_minutes,
        "status": new_status
    }).eq("voucher_code", voucher_code).execute()

    return True
