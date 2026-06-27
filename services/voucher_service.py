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
    if voucher["remaining_minutes"] <= 0:
        return False, "Voucher has no remaining time"
    return True, ""


def deduct_minutes(voucher_code: str, minutes: int) -> bool:
    """Deduct minutes from a voucher. Returns True if successful."""
    voucher = get_voucher_by_code(voucher_code)
    if not voucher:
        return False

    new_remaining = max(0, voucher["remaining_minutes"] - minutes)
    new_status = "exhausted" if new_remaining == 0 else voucher["status"]

    supabase.table("vouchers").update({
        "remaining_minutes": new_remaining,
        "status": new_status
    }).eq("voucher_code", voucher_code).execute()

    return True
