from flask import Blueprint, request, jsonify
from config import supabase

hotspot_bp = Blueprint("hotspot", __name__)


@hotspot_bp.route("/hotspot/<hotspot_code>", methods=["GET"])
def get_hotspot(hotspot_code):
    """Get hotspot details by code. (Phase 3 - full implementation coming)"""
    return jsonify({
        "success": False,
        "message": "Not yet implemented"
    }), 501
