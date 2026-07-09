import hashlib
from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from services.voucher_service import (
    get_voucher_by_code, is_voucher_valid,
    deduct_seconds, get_remaining_seconds, sync_seconds
)
from services.session_service import (
    create_session, get_active_session, get_any_active_session,
    end_all_active_sessions, check_cooldown, end_session,
    get_session_by_id
)
from middleware import require_api_key
from config import supabase

auth_bp = Blueprint("auth", __name__)

COOLDOWN_SECONDS = 60


# ── Customer Portal ───────────────────────────────────────────

@auth_bp.route("/portal")
def portal():
    return render_template("portal.html")


# ── Portal sync — saves exact seconds BEFORE anything else ────

@auth_bp.route("/portal/sync", methods=["POST"])
def portal_sync():
    """
    Client pushes exact remaining seconds to the server.
    Must be called before logout or switching devices.
    Uses navigator.sendBeacon so it fires even on page close.
    """
    data              = request.get_json(silent=True) or {}
    voucher_code      = data.get("voucher_code", "").strip().upper()
    remaining_seconds = data.get("remaining_seconds", 0)

    if not voucher_code:
        return jsonify({"success": False}), 400

    sync_seconds(voucher_code, int(remaining_seconds))
    return jsonify({"success": True}), 200


# ── Portal login ──────────────────────────────────────────────

@auth_bp.route("/portal/login", methods=["POST"])
def portal_login():
    data         = request.get_json()
    voucher_code = data.get("voucher_code", "").strip().upper()
    hotspot_code = data.get("hotspot_code", "PORTAL").strip().upper()
    device_fp    = data.get("device_mac", "browser-client").strip().lower()
    # Client sends its current remaining_seconds BEFORE switching
    client_remaining = data.get("remaining_seconds")

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
        if existing_fp == device_fp:
            # Same device reconnecting — end old session, start fresh
            end_all_active_sessions(voucher_code)
        else:
            # Different device — check cooldown
            if check_cooldown(voucher_code, hotspot_code, COOLDOWN_SECONDS):
                return jsonify({
                    "success": False,
                    "message": f"This voucher was just used on another device. Please wait {COOLDOWN_SECONDS} seconds before connecting."
                }), 429
            # End old session — time was already synced by the other device's beforeunload
            end_all_active_sessions(voucher_code)

    # If client sent its remaining seconds (switching devices), sync it first
    if client_remaining is not None:
        sync_seconds(voucher_code, int(client_remaining))
        # Re-fetch voucher to get updated seconds
        voucher = get_voucher_by_code(voucher_code)

    session_record = create_session(voucher_code, hotspot_code, device_fp)
    if not session_record:
        return jsonify({"success": False, "message": "Failed to create session"}), 500

    remaining_secs = get_remaining_seconds(voucher)

    return jsonify({
        "success": True,
        "session_id": session_record["id"],
        "voucher_code": voucher["voucher_code"],
        "remaining_seconds": remaining_secs,
        "remaining_minutes": remaining_secs // 60,
    }), 200


# ── Portal verify ─────────────────────────────────────────────

@auth_bp.route("/portal/verify", methods=["POST"])
def portal_verify():
    """Check session is alive + return exact remaining seconds. No time deducted."""
    data         = request.get_json()
    session_id   = data.get("session_id")
    voucher_code = data.get("voucher_code", "").strip().upper()

    if not session_id or not voucher_code:
        return jsonify({"success": False, "message": "session_id and voucher_code required"}), 400

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

    remaining_secs = get_remaining_seconds(voucher)

    return jsonify({
        "success": True,
        "remaining_seconds": remaining_secs,
        "remaining_minutes": remaining_secs // 60,
        "action": "continue" if remaining_secs > 0 else "disconnect"
    }), 200


# ── Portal heartbeat ──────────────────────────────────────────

@auth_bp.route("/portal/heartbeat", methods=["POST"])
def portal_heartbeat():
    """Deducts exactly 60 seconds every minute. Checks session is still active."""
    data         = request.get_json()
    session_id   = data.get("session_id")
    voucher_code = data.get("voucher_code", "").strip().upper()
    # Client sends its current seconds so we can sync if needed
    client_remaining = data.get("remaining_seconds")

    if not session_id or not voucher_code:
        return jsonify({"success": False, "message": "session_id and voucher_code required"}), 400

    session_record = get_session_by_id(session_id)
    if not session_record:
        return jsonify({"success": False, "action": "disconnect", "message": "Session not found."}), 404

    if not session_record.get("active"):
        return jsonify({
            "success": False,
            "action": "disconnect",
            "message": "Your session was ended because another device connected using the same voucher code."
        }), 403

    voucher = get_voucher_by_code(voucher_code)
    if not voucher:
        return jsonify({"success": False, "action": "disconnect"}), 404

    valid, reason = is_voucher_valid(voucher)
    if not valid:
        end_session(session_id)
        return jsonify({"success": False, "message": reason, "action": "disconnect"}), 403

    # Deduct exactly 60 seconds
    deduct_seconds(voucher_code, 60)

    # Re-fetch to get updated value
    voucher = get_voucher_by_code(voucher_code)
    remaining_secs = get_remaining_seconds(voucher)

    return jsonify({
        "success": True,
        "remaining_seconds": remaining_secs,
        "remaining_minutes": remaining_secs // 60,
        "action": "continue" if remaining_secs > 0 else "disconnect"
    }), 200


# ── Portal logout ─────────────────────────────────────────────

@auth_bp.route("/portal/logout", methods=["POST"])
def portal_logout():
    """End session. Syncs exact seconds before closing."""
    data              = request.get_json()
    session_id        = data.get("session_id")
    voucher_code      = data.get("voucher_code", "").strip().upper()
    remaining_seconds = data.get("remaining_seconds")

    if not session_id:
        return jsonify({"success": False, "message": "session_id is required"}), 400

    # Sync exact seconds FIRST before ending session
    if voucher_code and remaining_seconds is not None:
        sync_seconds(voucher_code, int(remaining_seconds))

    end_session(session_id)
    return jsonify({"success": True, "message": "Logged out successfully"}), 200


# ── Hotspot machine login (requires API key) ──────────────────

@auth_bp.route("/login", methods=["POST"])
@require_api_key
def login():
    data         = request.get_json()
    voucher_code = data.get("voucher_code", "").strip().upper()
    device_mac   = data.get("device_mac", "").strip().lower()
    hotspot_code = request.hotspot_code

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

    existing = get_active_session(voucher_code, hotspot_code)
    if existing:
        return jsonify({"success": False, "message": "Already connected at this hotspot"}), 409

    other = get_any_active_session(voucher_code)
    if other:
        if check_cooldown(voucher_code, hotspot_code, COOLDOWN_SECONDS):
            return jsonify({"success": False, "message": f"Please wait {COOLDOWN_SECONDS} seconds before switching hotspots."}), 429
        end_all_active_sessions(voucher_code)

    session_record = create_session(voucher_code, hotspot_code, device_mac)
    if not session_record:
        return jsonify({"success": False, "message": "Failed to create session"}), 500

    remaining_secs = get_remaining_seconds(voucher)

    return jsonify({
        "success": True,
        "session_id": session_record["id"],
        "voucher_code": voucher["voucher_code"],
        "remaining_seconds": remaining_secs,
        "remaining_minutes": remaining_secs // 60,
        "hotspot_code": hotspot_code,
        "device_mac": device_mac
    }), 200


# ── Admin login / logout ──────────────────────────────────────

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
