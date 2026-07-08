import hashlib
from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from services.voucher_service import get_voucher_by_code, is_voucher_valid, deduct_minutes
from services.session_service import (
    create_session, get_active_session, get_any_active_session,
    end_all_active_sessions, check_cooldown, end_session
)
from middleware import require_api_key
from config import supabase

auth_bp = Blueprint("auth", __name__)

COOLDOWN_SECONDS = 60  # Abuse prevention: 60 second cooldown between hotspot switches


# ── Customer Portal ───────────────────────────────────────────

@auth_bp.route("/portal")
def portal():
    return render_template("portal.html")


# ── Voucher Login (requires API key from hotspot machines) ────

@auth_bp.route("/login", methods=["POST"])
@require_api_key
def login():
    data         = request.get_json()
    voucher_code = data.get("voucher_code", "").strip().upper()
    device_mac   = data.get("device_mac", "").strip().lower()
    hotspot_code = request.hotspot_code  # set by middleware

    if not voucher_code:
        return jsonify({"success": False, "message": "voucher_code is required"}), 400
    if not device_mac:
        return jsonify({"success": False, "message": "device_mac is required"}), 400

    voucher = get_voucher_by_code(voucher_code)
    if not voucher:
        return jsonify({"success": False, "message": "Voucher not found"}), 404

    valid, reason = is_voucher_valid(voucher)
    if not valid:
        return jsonify({"success": False, "message": reason}), 403

    # Check if already connected at THIS hotspot
    existing = get_active_session(voucher_code, hotspot_code)
    if existing:
        return jsonify({
            "success": False,
            "message": "Already connected at this hotspot"
        }), 409

    # Check if connected at a DIFFERENT hotspot
    other_session = get_any_active_session(voucher_code)
    if other_session:
        # Check cooldown (abuse prevention)
        if check_cooldown(voucher_code, hotspot_code, COOLDOWN_SECONDS):
            return jsonify({
                "success": False,
                "message": f"Please wait {COOLDOWN_SECONDS} seconds before switching hotspots."
            }), 429

        # Auto-switch: end all sessions at other hotspots
        ended = end_all_active_sessions(voucher_code)

    # Create new session
    session_record = create_session(voucher_code, hotspot_code, device_mac)
    if not session_record:
        return jsonify({"success": False, "message": "Failed to create session"}), 500

    return jsonify({
        "success": True,
        "session_id": session_record["id"],
        "voucher_code": voucher["voucher_code"],
        "remaining_minutes": voucher["remaining_minutes"],
        "hotspot_code": hotspot_code,
        "device_mac": device_mac
    }), 200


# ── Portal Login (no API key — browser-based) ─────────────────

@auth_bp.route("/portal/login", methods=["POST"])
def portal_login():
    data         = request.get_json()
    voucher_code = data.get("voucher_code", "").strip().upper()
    hotspot_code = data.get("hotspot_code", "PORTAL").strip().upper()
    device_fp    = data.get("device_mac", "browser-client").strip().lower()

    if not voucher_code:
        return jsonify({"success": False, "message": "Voucher code is required"}), 400

    voucher = get_voucher_by_code(voucher_code)
    if not voucher:
        return jsonify({"success": False, "message": "Voucher not found"}), 404

    valid, reason = is_voucher_valid(voucher)
    if not valid:
        return jsonify({"success": False, "message": reason}), 403

    # Check for existing active session
    existing = get_any_active_session(voucher_code)

    if existing:
        existing_fp = existing.get("device_mac", "")

        # Same device reconnecting — just reuse or replace session
        if existing_fp == device_fp:
            end_all_active_sessions(voucher_code)
        else:
            # Different device — check cooldown (abuse prevention)
            if check_cooldown(voucher_code, hotspot_code, COOLDOWN_SECONDS):
                return jsonify({
                    "success": False,
                    "message": f"This voucher was just used on another device. Please wait {COOLDOWN_SECONDS} seconds before connecting."
                }), 429

            # Auto-switch: end the other device's session
            end_all_active_sessions(voucher_code)

    session_record = create_session(voucher_code, hotspot_code, device_fp)
    if not session_record:
        return jsonify({"success": False, "message": "Failed to create session"}), 500

    return jsonify({
        "success": True,
        "session_id": session_record["id"],
        "voucher_code": voucher["voucher_code"],
        "remaining_minutes": voucher["remaining_minutes"],
    }), 200


@auth_bp.route("/portal/heartbeat", methods=["POST"])
def portal_heartbeat():
    data         = request.get_json()
    session_id   = data.get("session_id")
    voucher_code = data.get("voucher_code", "").strip().upper()

    if not session_id or not voucher_code:
        return jsonify({"success": False, "message": "session_id and voucher_code required"}), 400

    # Check if THIS specific session is still active
    # If not, it means another device took over
    from services.session_service import get_session_by_id
    session_record = get_session_by_id(session_id)

    if not session_record:
        return jsonify({
            "success": False,
            "action": "disconnect",
            "message": "Session not found."
        }), 404

    if not session_record.get("active"):
        return jsonify({
            "success": False,
            "action": "disconnect",
            "message": "Your session was ended because another device connected using the same voucher code."
        }), 403

    voucher = get_voucher_by_code(voucher_code)
    if not voucher:
        return jsonify({"success": False, "action": "disconnect", "message": "Voucher not found."}), 404

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


@auth_bp.route("/portal/logout", methods=["POST"])
def portal_logout():
    data = request.get_json()
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"success": False, "message": "session_id is required"}), 400
    end_session(session_id)
    return jsonify({"success": True, "message": "Logged out successfully"}), 200


# ── Admin Login / Logout ──────────────────────────────────────

@auth_bp.route("/admin/login", methods=["GET"])
def admin_login_page():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_dashboard"))
    return render_template("login.html")


@auth_bp.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    username      = data["username"].strip()
    password_hash = hashlib.sha256(data["password"].encode()).hexdigest()

    result = supabase.table("admins").select("*").eq("username", username).eq("password_hash", password_hash).execute()

    if not result.data:
        return jsonify({"success": False, "message": "Invalid username or password"}), 401

    admin = result.data[0]
    session["admin_logged_in"] = True
    session["admin_username"]  = admin["username"]
    session["admin_role"]      = admin["role"]

    return jsonify({"success": True, "username": admin["username"], "role": admin["role"]}), 200


@auth_bp.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out"}), 200


@auth_bp.route("/portal/verify", methods=["POST"])
def portal_verify():
    """
    Verify a session is still active without deducting time.
    Used on page load/refresh to restore session state.
    """
    data       = request.get_json()
    session_id = data.get("session_id")
    voucher_code = data.get("voucher_code", "").strip().upper()

    if not session_id or not voucher_code:
        return jsonify({"success": False, "message": "session_id and voucher_code required"}), 400

    from services.session_service import get_session_by_id
    from services.voucher_service import get_voucher_by_code

    session_record = get_session_by_id(session_id)

    if not session_record or not session_record.get("active"):
        return jsonify({
            "success": False,
            "action": "disconnect",
            "message": "Session is no longer active."
        }), 403

    voucher = get_voucher_by_code(voucher_code)
    if not voucher:
        return jsonify({"success": False, "action": "disconnect"}), 404

    return jsonify({
        "success": True,
        "remaining_minutes": voucher["remaining_minutes"],
        "action": "continue"
    }), 200
