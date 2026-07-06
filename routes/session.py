from flask import Blueprint, request, jsonify
from services.voucher_service import get_voucher_by_code, is_voucher_valid, deduct_minutes
from services.session_service import get_active_session, end_session
from middleware import require_api_key

session_bp = Blueprint("session", __name__)


@session_bp.route("/logout", methods=["POST"])
@require_api_key
def logout():
    data = request.get_json()
    if not data or "session_id" not in data:
        return jsonify({"success": False, "message": "session_id is required"}), 400

    success = end_session(data["session_id"])
    if not success:
        return jsonify({"success": False, "message": "Session not found or already ended"}), 404

    return jsonify({"success": True, "message": "Session ended successfully"}), 200


@session_bp.route("/heartbeat", methods=["POST"])
@require_api_key
def heartbeat():
    data = request.get_json()
    if not data or "session_id" not in data:
        return jsonify({"success": False, "message": "session_id is required"}), 400
    if "voucher_code" not in data:
        return jsonify({"success": False, "message": "voucher_code is required"}), 400

    session_id   = data["session_id"]
    voucher_code = data["voucher_code"].strip().upper()

    voucher = get_voucher_by_code(voucher_code)
    if not voucher:
        return jsonify({"success": False, "message": "Voucher not found"}), 404

    valid, reason = is_voucher_valid(voucher)
    if not valid:
        end_session(session_id)
        return jsonify({"success": False, "message": reason, "action": "disconnect"}), 403

    deduct_minutes(voucher_code, 1)
    remaining = voucher["remaining_minutes"] - 1

    return jsonify({
        "success": True,
        "remaining_minutes": remaining,
        "action": "continue" if remaining > 0 else "disconnect"
    }), 200


@session_bp.route("/consume", methods=["POST"])
@require_api_key
def consume():
    data = request.get_json()
    if not data or "voucher_code" not in data:
        return jsonify({"success": False, "message": "voucher_code is required"}), 400
    if "minutes" not in data:
        return jsonify({"success": False, "message": "minutes is required"}), 400

    voucher_code = data["voucher_code"].strip().upper()
    minutes      = int(data["minutes"])

    if minutes <= 0:
        return jsonify({"success": False, "message": "minutes must be greater than 0"}), 400

    voucher = get_voucher_by_code(voucher_code)
    if not voucher:
        return jsonify({"success": False, "message": "Voucher not found"}), 404

    valid, reason = is_voucher_valid(voucher)
    if not valid:
        return jsonify({"success": False, "message": reason}), 403

    if voucher["remaining_minutes"] < minutes:
        return jsonify({
            "success": False,
            "message": f"Not enough time. Only {voucher['remaining_minutes']} minutes remaining"
        }), 403

    deduct_minutes(voucher_code, minutes)

    return jsonify({
        "success": True,
        "voucher_code": voucher_code,
        "minutes_consumed": minutes,
        "remaining_minutes": voucher["remaining_minutes"] - minutes
    }), 200
