from __future__ import annotations

from flask import Flask, redirect, render_template, session, url_for

from config import settings
from database.db import close_connection, ensure_default_admin, ensure_schema_compatibility, get_connection, init_db, seed_if_empty
from routes.admin_routes import admin_bp
from routes.appointment_routes import appointment_bp
from routes.auth_routes import auth_bp
from routes.chat_routes import chat_bp
from routes.doctor_routes import recommendation_bp
from routes.history_routes import history_bp
from services.firebase_auth_service import firebase_auth_status

def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = settings.secret_key

    with app.app_context():
        conn = get_connection()
        init_db(conn)
        ensure_schema_compatibility(conn)
        ensure_default_admin(conn)
        seed_if_empty(conn)
        close_connection(None)

    @app.route("/")
    def index() -> str:
        return render_template("landing.html", app_name=settings.app_name)

    @app.route("/user/login")
    def user_login_page() -> str:
        if session.get("role") == "user" and session.get("user_id"):
            return redirect(url_for("user_dashboard"))
        return render_template("user_login.html", app_name=settings.app_name)

    @app.route("/user/signup")
    def user_signup_page() -> str:
        if session.get("role") == "user" and session.get("user_id"):
            return redirect(url_for("user_dashboard"))
        return render_template("signup.html", app_name=settings.app_name)

    @app.route("/user")
    def user_dashboard() -> str:
        if session.get("role") != "user" or not session.get("user_id"):
            return redirect(url_for("user_login_page"))
        return render_template("dashboard.html", app_name=settings.app_name)

    @app.route("/dashboard")
    def dashboard_redirect() -> str:
        return redirect(url_for("user_dashboard"))

    @app.route("/admin")
    def admin_denied() -> str:
        if session.get("role") == "admin" and session.get("admin_id"):
            return redirect(url_for("admin_dashboard"))
        return render_template("access_denied.html", app_name=settings.app_name), 403

    @app.route("/admin/login")
    def admin_login_page() -> str:
        if session.get("role") == "admin" and session.get("admin_id"):
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_login.html", app_name=settings.app_name)

    @app.route("/admin/dashboard")
    def admin_dashboard() -> str:
        if session.get("role") != "admin" or not session.get("admin_id"):
            return render_template("access_denied.html", app_name=settings.app_name), 403
        return render_template("admin.html", app_name=settings.app_name)

    @app.get("/api/health")
    def health() -> dict[str, object]:
        firebase_status = firebase_auth_status()
        return {
            "status": "ok",
            "app_name": settings.app_name,
            "db_engine": settings.db_engine,
            "model_path": settings.model_path,
            "firebase_project_id": settings.firebase_project_id,
            "firebase_auth_ready": firebase_status["ready"],
            "firebase_auth_message": firebase_status["message"],
            "mysql_database": settings.mysql_database if settings.db_engine == "mysql" else None,
        }

    app.register_blueprint(auth_bp)
    app.register_blueprint(recommendation_bp)
    app.register_blueprint(appointment_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(admin_bp)

    @app.teardown_appcontext
    def teardown(_: BaseException | None) -> None:
        close_connection(None)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
