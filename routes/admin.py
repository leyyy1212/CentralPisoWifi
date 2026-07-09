from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from config import supabase
from middleware import require_admin

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@require_admin
def admin_dashboard():
    return render_template("admin.html")


@admin_bp.route("/dashboard", methods=["GET"])
@require_admin
def dashboard():
    vouchers     = supabase.table("vouchers").select("*").order("created_at", desc=True).execute()
    sessions     = supabase.table("sessions").select("*").order("login_time", desc=True).execute()
    transactions = supabase.table("transactions").select("*").order("created_at", desc=True).execute()
    hotspots     = supabase.table("hotspots").select("*").execute()

    all_vouchers     = vouchers.data or []
    all_sessions     = sessions.data or []
    all_transactions = transactions.data or []
    all_hotspots     = hotspots.data or []

    total_income    = sum(t["amount"] for t in all_transactions)
    active_sessions = [s for s in all_sessions if s["active"]]
    active_vouchers = [v for v in all_vouchers if v["status"].lower() == "active"]

    return jsonify({
        "success": True,
        "stats": {
            "total_vouchers": len(all_vouchers),
            "active_vouchers": len(active_vouchers),
            "active_sessions": len(active_sessions),
            "total_income": round(total_income, 2),
            "total_transactions": len(all_transactions),
            "total_hotspots": len(all_hotspots),
        },
        "vouchers": all_vouchers,
        "sessions": all_sessions[:20],
        "transactions": all_transactions[:20],
        "hotspots": all_hotspots,
    }), 200


@admin_bp.route("/admin/voucher", methods=["POST"])
@require_admin
def create_voucher():
    data = request.get_json()
    if not data or "voucher_code" not in data or "minutes" not in data:
        return jsonify({"success": False, "message": "voucher_code and minutes are required"}), 400

    voucher_code   = data["voucher_code"].strip().upper()
    minutes        = int(data["minutes"])
    amount         = float(data.get("amount", 0))
    payment_method = data.get("payment_method", "cash").strip().lower()

    existing = supabase.table("vouchers").select("id").eq("voucher_code", voucher_code).execute()
    if existing.data:
        return jsonify({"success": False, "message": "Voucher code already exists"}), 409

    result = supabase.table("vouchers").insert({
        "voucher_code": voucher_code,
        "total_minutes": minutes,
        "remaining_minutes": minutes,
        "status": "active"
    }).execute()

    if amount > 0:
        supabase.table("transactions").insert({
            "voucher_code": voucher_code,
            "amount": amount,
            "minutes": minutes,
            "payment_method": payment_method
        }).execute()

    return jsonify({"success": True, "voucher": result.data[0]}), 201


@admin_bp.route("/admin/voucher/<voucher_code>", methods=["DELETE"])
@require_admin
def delete_voucher(voucher_code):
    supabase.table("vouchers").delete().eq("voucher_code", voucher_code.upper()).execute()
    return jsonify({"success": True, "message": f"Voucher {voucher_code} deleted"}), 200


@admin_bp.route("/admin/voucher/<voucher_code>/suspend", methods=["POST"])
@require_admin
def suspend_voucher(voucher_code):
    voucher = supabase.table("vouchers").select("status").eq("voucher_code", voucher_code.upper()).execute()
    if not voucher.data:
        return jsonify({"success": False, "message": "Voucher not found"}), 404

    current    = voucher.data[0]["status"].lower()
    new_status = "active" if current == "suspended" else "suspended"

    supabase.table("vouchers").update({"status": new_status}).eq("voucher_code", voucher_code.upper()).execute()
    return jsonify({"success": True, "status": new_status}), 200


@admin_bp.route("/admin/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("auth.admin_login_page"))


@admin_bp.route("/admin/analytics", methods=["GET"])
@require_admin
def analytics():
    """Portal analytics data."""
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)

    # Sessions in last 7 days
    week_ago = (now - timedelta(days=7)).isoformat()
    sessions_week = supabase.table("sessions").select("*").gte("login_time", week_ago).execute()

    # Sessions today
    today = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    sessions_today = supabase.table("sessions").select("*").gte("login_time", today).execute()

    # Transactions this week
    tx_week = supabase.table("transactions").select("*").gte("created_at", week_ago).execute()

    # Income today
    tx_today = supabase.table("transactions").select("*").gte("created_at", today).execute()

    # Active sessions right now
    active = supabase.table("sessions").select("*").eq("active", True).execute()

    # Top vouchers by session count
    all_sessions = supabase.table("sessions").select("voucher_code, hotspot_code, login_time, logout_time, active").order("login_time", desc=True).limit(100).execute()

    # Sessions per day (last 7 days)
    daily = {}
    for s in (sessions_week.data or []):
        day = s["login_time"][:10]
        daily[day] = daily.get(day, 0) + 1

    # Sessions per hotspot
    by_hotspot = {}
    for s in (all_sessions.data or []):
        hc = s.get("hotspot_code", "Unknown")
        if hc == "PORTAL": hc = "Web Portal"
        by_hotspot[hc] = by_hotspot.get(hc, 0) + 1

    # Average session duration (minutes)
    durations = []
    for s in (all_sessions.data or []):
        if s.get("login_time") and s.get("logout_time"):
            try:
                login  = datetime.fromisoformat(s["login_time"].replace("Z", "+00:00"))
                logout = datetime.fromisoformat(s["logout_time"].replace("Z", "+00:00"))
                dur = (logout - login).total_seconds() / 60
                if 0 < dur < 1440:  # ignore unrealistic values
                    durations.append(round(dur, 1))
            except: pass

    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

    # Income per payment method this week
    by_payment = {}
    for t in (tx_week.data or []):
        pm = t.get("payment_method", "other")
        by_payment[pm] = round(by_payment.get(pm, 0) + float(t.get("amount", 0)), 2)

    return jsonify({
        "success": True,
        "summary": {
            "sessions_today": len(sessions_today.data or []),
            "sessions_week": len(sessions_week.data or []),
            "active_now": len(active.data or []),
            "income_today": round(sum(float(t.get("amount", 0)) for t in (tx_today.data or [])), 2),
            "income_week": round(sum(float(t.get("amount", 0)) for t in (tx_week.data or [])), 2),
            "avg_duration_mins": avg_duration,
        },
        "daily_sessions": daily,
        "by_hotspot": by_hotspot,
        "by_payment": by_payment,
        "recent_sessions": (all_sessions.data or [])[:20]
    }), 200
