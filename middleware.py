from functools import wraps
from flask import request, jsonify, session, redirect, url_for
from config import supabase


def require_api_key(f):
    """
    Decorator for hotspot-facing routes.
    Every request must include a valid api_key in the JSON body.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        data = request.get_json(silent=True) or {}
        api_key = data.get("api_key") or request.headers.get("X-API-Key")

        if not api_key:
            return jsonify({"success": False, "message": "api_key is required"}), 401

        result = supabase.table("hotspots").select("hotspot_code, status").eq("api_key", api_key).execute()

        if not result.data:
            return jsonify({"success": False, "message": "Invalid API key"}), 401

        hotspot = result.data[0]
        if hotspot["status"].lower() != "active":
            return jsonify({"success": False, "message": "Hotspot is not active"}), 403

        request.hotspot_code = hotspot["hotspot_code"]
        return f(*args, **kwargs)

    return decorated


def require_admin(f):
    """
    Decorator for admin-facing routes.
    Always redirects to login page if not authenticated.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            # If it's an API call (starts with /dashboard or /admin/voucher), return JSON
            if request.path.startswith("/dashboard") or (
                request.path.startswith("/admin/") and request.method != "GET"
            ):
                return jsonify({"success": False, "message": "Admin login required"}), 401
            # Otherwise redirect to login page
            return redirect("/admin/login")
        return f(*args, **kwargs)

    return decorated
