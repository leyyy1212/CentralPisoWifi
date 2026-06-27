from flask import Blueprint, request, jsonify
from services.voucher_service import get_voucher_by_code, is_voucher_valid
from services.session_service import create_session, get_active_session

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    # Validate request body
    if not data or "voucher_code" not in data:
        return jsonify({"success": False, "message": "voucher_code is required"}), 400
    if "hotspot_code" not in data:
        return jsonify({"success": False, "message": "hotspot_code is required"}), 400
    if "device_mac" not in data:
        return jsonify({"success": False, "message": "device_mac is required"}), 400

    voucher_code = data["voucher_code"].strip().upper()
    hotspot_code = data["hotspot_code"].strip().upper()
    device_mac   = data["device_mac"].strip().lower()

    # Check voucher exists
    voucher = get_voucher_by_code(voucher_code)
    if not voucher:
        return jsonify({"success": False, "message": "Voucher not found"}), 404

    # Check voucher is usable
    valid, reason = is_voucher_valid(voucher)
    if not valid:
        return jsonify({"success": False, "message": reason}), 403

    # Prevent duplicate active sessions
    existing = get_active_session(voucher_code, hotspot_code)
    if existing:
        return jsonify({
            "success": False,
            "message": "An active session already exists for this voucher"
        }), 409

    # Create session
    session = create_session(voucher_code, hotspot_code, device_mac)
    if not session:
        return jsonify({"success": False, "message": "Failed to create session"}), 500

    return jsonify({
        "success": True,
        "session_id": session["id"],
        "voucher_code": voucher["voucher_code"],
        "remaining_minutes": voucher["remaining_minutes"],
        "hotspot_code": hotspot_code,
        "device_mac": device_mac
    }), 200
