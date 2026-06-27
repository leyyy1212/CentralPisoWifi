from flask import Blueprint, request, jsonify, render_template
from config import supabase

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
def admin_dashboard():
    """Serve the admin dashboard UI."""
    return render_template("admin.html")


@admin_bp.route("/dashboard", methods=["GET"])
def dashboard():
    """Return all dashboard data as JSON."""
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
def create_voucher():
    """Create a new voucher from the admin panel."""
    data = request.get_json()
    if not data or "voucher_code" not in data or "minutes" not in data:
        return jsonify({"success": False, "message": "voucher_code and minutes are required"}), 400

    voucher_code = data["voucher_code"].strip().upper()
    minutes      = int(data["minutes"])

    existing = supabase.table("vouchers").select("id").eq("voucher_code", voucher_code).execute()
    if existing.data:
        return jsonify({"success": False, "message": "Voucher code already exists"}), 409

    result = supabase.table("vouchers").insert({
        "voucher_code": voucher_code,
        "total_minutes": minutes,
        "remaining_minutes": minutes,
        "status": "active"
    }).execute()

    return jsonify({"success": True, "voucher": result.data[0]}), 201


@admin_bp.route("/admin/voucher/<voucher_code>", methods=["DELETE"])
def delete_voucher(voucher_code):
    """Delete a voucher."""
    supabase.table("vouchers").delete().eq("voucher_code", voucher_code.upper()).execute()
    return jsonify({"success": True, "message": f"Voucher {voucher_code} deleted"}), 200


@admin_bp.route("/admin/voucher/<voucher_code>/suspend", methods=["POST"])
def suspend_voucher(voucher_code):
    """Suspend or reactivate a voucher."""
    voucher = supabase.table("vouchers").select("status").eq("voucher_code", voucher_code.upper()).execute()
    if not voucher.data:
        return jsonify({"success": False, "message": "Voucher not found"}), 404

    current    = voucher.data[0]["status"].lower()
    new_status = "active" if current == "suspended" else "suspended"

    supabase.table("vouchers").update({"status": new_status}).eq("voucher_code", voucher_code.upper()).execute()
    return jsonify({"success": True, "status": new_status}), 200
