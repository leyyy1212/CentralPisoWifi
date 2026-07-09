from config import supabase


def get_voucher_by_code(voucher_code: str):
    response = (
        supabase
        .table("vouchers")
        .select("*")
        .eq("voucher_code", voucher_code.upper())
        .execute()
    )
    return response.data[0] if response.data else None


def is_voucher_valid(voucher: dict) -> tuple[bool, str]:
    if voucher["status"].lower() not in ("active",):
        return False, f"Voucher is {voucher['status']}"
    if get_remaining_seconds(voucher) <= 0:
        return False, "Voucher has no remaining time"
    return True, ""


def get_remaining_seconds(voucher: dict) -> int:
    """
    Always use remaining_seconds as the source of truth.
    Falls back to remaining_minutes * 60 only if column doesn't exist yet.
    """
    rs = voucher.get("remaining_seconds")
    if rs is not None:
        return int(rs)
    return int(voucher.get("remaining_minutes", 0)) * 60


def sync_seconds(voucher_code: str, remaining_seconds: int) -> bool:
    """
    Save exact remaining seconds to the database.
    This is the single source of truth for time.
    """
    new_seconds = max(0, int(remaining_seconds))
    new_minutes = new_seconds // 60
    new_status  = "exhausted" if new_seconds == 0 else "active"

    # Get current status first to avoid overwriting suspended etc
    voucher = get_voucher_by_code(voucher_code)
    if not voucher:
        return False

    current_status = voucher.get("status", "active").lower()
    if current_status not in ("active", "exhausted"):
        # Don't change suspended vouchers
        new_status = current_status

    supabase.table("vouchers").update({
        "remaining_seconds": new_seconds,
        "remaining_minutes": new_minutes,
        "status": new_status
    }).eq("voucher_code", voucher_code).execute()

    return True


def deduct_seconds(voucher_code: str, seconds: int) -> bool:
    """Deduct exact seconds from a voucher."""
    voucher = get_voucher_by_code(voucher_code)
    if not voucher:
        return False
    current  = get_remaining_seconds(voucher)
    new_secs = max(0, current - seconds)
    return sync_seconds(voucher_code, new_secs)


def deduct_minutes(voucher_code: str, minutes: int) -> bool:
    return deduct_seconds(voucher_code, minutes * 60)
