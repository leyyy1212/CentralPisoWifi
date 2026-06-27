from flask import Blueprint, request, jsonify
from config import supabase
from services.voucher_service import get_voucher_by_code

voucher_bp = Blueprint("voucher", __name__)


@voucher_bp.route("/voucher/<voucher_code>", methods=["GET"])
def get_voucher(voucher_code):
    """Get voucher details by code."""
    voucher = get_voucher_by_code(voucher_code)

    if not voucher:
        return jsonify({"success": False, "message": "Voucher not found"}), 404

    return jsonify({
        "success": True,
        "voucher": {
            "voucher_code": voucher["voucher_code"],
            "total_minutes": voucher["total_minutes"],
            "remaining_minutes": voucher["remaining_minutes"],
            "status": voucher["status"],
            "created_at": voucher["created_at"]
        }
    }), 200


@voucher_bp.route("/buy-voucher", methods=["POST"])
def buy_voucher():
    """
    Purchase a new voucher.
    Creates a voucher record and a transaction record.
    """
    data = request.get_json()

    required = ["voucher_code", "minutes", "amount", "payment_method"]
    for field in required:
        if field not in data:
            return jsonify({"success": False, "message": f"{field} is required"}), 400

    voucher_code   = data["voucher_code"].strip().upper()
    minutes        = int(data["minutes"])
    amount         = float(data["amount"])
    payment_method = data["payment_method"].strip().lower()

    if minutes <= 0:
        return jsonify({"success": False, "message": "minutes must be greater than 0"}), 400
    if amount <= 0:
        return jsonify({"success": False, "message": "amount must be greater than 0"}), 400

    valid_payments = ("cash", "gcash", "maya", "card", "other")
    if payment_method not in valid_payments:
        return jsonify({
            "success": False,
            "message": f"payment_method must be one of: {', '.join(valid_payments)}"
        }), 400

    # Check if voucher code already exists
    existing = get_voucher_by_code(voucher_code)
    if existing:
        return jsonify({"success": False, "message": "Voucher code already exists"}), 409

    # Create the voucher
    voucher_response = supabase.table("vouchers").insert({
        "voucher_code": voucher_code,
        "total_minutes": minutes,
        "remaining_minutes": minutes,
        "status": "active"
    }).execute()

    if not voucher_response.data:
        return jsonify({"success": False, "message": "Failed to create voucher"}), 500

    # Create the transaction record
    supabase.table("transactions").insert({
        "voucher_code": voucher_code,
        "amount": amount,
        "minutes": minutes,
        "payment_method": payment_method
    }).execute()

    return jsonify({
        "success": True,
        "message": "Voucher purchased successfully",
        "voucher": {
            "voucher_code": voucher_code,
            "total_minutes": minutes,
            "remaining_minutes": minutes,
            "status": "active"
        },
        "transaction": {
            "amount": amount,
            "minutes": minutes,
            "payment_method": payment_method
        }
    }), 201
