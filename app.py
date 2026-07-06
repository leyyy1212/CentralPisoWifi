import os
from flask import Flask, jsonify
from routes.auth import auth_bp
from routes.voucher import voucher_bp
from routes.session import session_bp
from routes.hotspot import hotspot_bp
from routes.admin import admin_bp

app = Flask(__name__)

# Secret key for session cookies (change this to something random in production)
app.secret_key = os.environ.get("SECRET_KEY", "pisowifi-secret-change-me-in-production")

# ── Register Blueprints ──────────────────────────────────────
app.register_blueprint(auth_bp)
app.register_blueprint(voucher_bp)
app.register_blueprint(session_bp)
app.register_blueprint(hotspot_bp)
app.register_blueprint(admin_bp)


# ── Health Check ─────────────────────────────────────────────
@app.route("/")
def home():
    return jsonify({
        "service": "Central PisoWiFi Server",
        "status": "running",
        "version": "2.0.0"
    })


# ── Global Error Handlers ─────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "message": "Route not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"success": False, "message": "Method not allowed"}), 405

@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "message": "Internal server error"}), 500


# ── Run ───────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
