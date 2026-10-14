"""
Pink Cafe Backend - Flask entrypoint.

Dev:        python app.py
Production: gunicorn app:app
"""

import os
from pathlib import Path
from flask import Flask, abort, send_from_directory
from flask_cors import CORS
from db import init_db
from routes import register_routes

# --- Configuration (read from environment, with sensible defaults) ---
DEBUG        = os.getenv("FLASK_ENV", "development") == "development"
SECRET_KEY   = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join("data", "pinkcafe.db"))


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["DATABASE_PATH"] = DATABASE_PATH
    app.secret_key = SECRET_KEY

    # Allow cross-origin requests from the React frontend
    CORS(app, origins=CORS_ORIGINS)

    # Create DB tables if they don't exist yet (safe to run every startup)
    init_db(DATABASE_PATH)

    # Attach all API routes
    register_routes(app)

    # In the production image, serve the compiled React single-page app from
    # Flask. The development compose setup uses the React dev server instead.
    frontend_dir = os.getenv("FRONTEND_DIR")
    if frontend_dir and Path(frontend_dir).is_dir():
        @app.get("/")
        def frontend_index():
            return send_from_directory(frontend_dir, "index.html")

        @app.get("/<path:requested_path>")
        def frontend_route(requested_path: str):
            if requested_path == "api" or requested_path.startswith("api/"):
                abort(404)

            requested_file = Path(frontend_dir, requested_path)
            if requested_file.is_file():
                return send_from_directory(frontend_dir, requested_path)
            return send_from_directory(frontend_dir, "index.html")

    # Security: add OWASP-recommended response headers to every reply
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' data:;"
        )
        return response

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    print(f"Flask server starting on http://0.0.0.0:{port}")
    app.run(debug=DEBUG, host="0.0.0.0", port=port)
