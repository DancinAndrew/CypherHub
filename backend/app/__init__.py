from __future__ import annotations

from flask import Flask, jsonify
from flask_cors import CORS

from app.logger import setup_structured_logging

from .blueprints.admin import bp as admin_bp
from .blueprints.auth import bp as auth_bp
from .blueprints.checkin import bp as checkin_bp
from .blueprints.events import bp as events_bp
from .blueprints.jobs import bp as jobs_bp
from .blueprints.me import bp as me_bp
from .blueprints.orders import bp as orders_bp
from .blueprints.payments import bp as payments_bp
from .blueprints.progress import organizer_bp as organizer_progress_bp
from .blueprints.progress import public_bp as public_progress_bp
from .blueprints.registrations import bp as registrations_bp
from .blueprints.settlements import bp as settlements_bp
from .blueprints.ticket_types import bp as ticket_types_bp
from .blueprints.tickets import bp as tickets_bp
from .blueprints.webhooks import bp as webhooks_bp
from .config import Config
from .domain.errors import AppError
from .domain.schemas import HealthResponse
from .extensions import init_extensions

try:
    from flask_limiter.errors import RateLimitExceeded
except ImportError:
    RateLimitExceeded = None  # type: ignore[misc, assignment]


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    setup_structured_logging(app)
    init_extensions(app)
    _validate_cors_origins(app)
    _validate_production_urls(app)
    _validate_production_config(app)
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", [])}})
    _register_blueprints(app)
    # 避免 /api/v1/orders 被 308 重定向至 /api/v1/orders/，CORS preflight 不允許 redirect
    for rule in app.url_map.iter_rules():
        if rule.strict_slashes:
            rule.strict_slashes = False
    _register_error_handlers(app)
    _register_security_headers(app)

    @app.get("/")
    def index() -> tuple[dict, int]:
        return jsonify({"status": "ok", "service": "CypherHub API", "version": "v1"}), 200

    @app.get("/api/v1/health")
    def health() -> tuple[dict, int]:
        payload = HealthResponse(status="ok")
        return jsonify(payload.model_dump()), 200

    return app


def _register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(registrations_bp)  # before events so /events/<id>/register is here
    app.register_blueprint(events_bp)
    app.register_blueprint(ticket_types_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(me_bp)
    app.register_blueprint(checkin_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(webhooks_bp)
    app.register_blueprint(settlements_bp)
    app.register_blueprint(organizer_progress_bp)
    app.register_blueprint(public_progress_bp)


def _validate_production_urls(app: Flask) -> None:
    """生產環境 URL 安全檢查（SEC-1）"""
    if app.config.get("APP_ENV") != "production":
        return
    supabase_url = app.config.get("SUPABASE_URL", "")
    if supabase_url and ("localhost" in supabase_url or "127.0.0.1" in supabase_url):
        raise ValueError("SEC-1: 生產環境 SUPABASE_URL 不可指向 localhost")
    if supabase_url and not supabase_url.startswith("https://"):
        raise ValueError("SEC-1: 生產環境 SUPABASE_URL 必須使用 HTTPS")


def _validate_production_config(app: Flask) -> None:
    """SEC-4: 生產環境必要環境變數檢查，缺少則拒絕啟動。"""
    if app.config.get("APP_ENV") != "production":
        return
    required = {
        "SUPABASE_URL": "Supabase 連線 URL",
        "SUPABASE_ANON_KEY": "Supabase Anon Key",
        "SUPABASE_SERVICE_ROLE_KEY": "Supabase Service Role Key",
        "CRON_SECRET": "Cron Job 驗證密鑰",
    }
    for key, label in required.items():
        if not app.config.get(key):
            raise ValueError(f"SEC-4: 生產環境必須設定 {key}（{label}）")
    if app.config.get("FLASK_DEBUG"):
        raise ValueError("SEC-4: 生產環境禁止啟用 FLASK_DEBUG")


def _validate_cors_origins(app: Flask) -> None:
    """啟動時檢查 CORS 設定安全性（SEC-1）"""
    origins = app.config.get("CORS_ORIGINS", [])
    app.logger.info("CORS allowed origins: %s", origins)
    is_production = app.config.get("APP_ENV") == "production"
    for origin in origins:
        if origin == "*":
            if is_production:
                raise ValueError("SEC-1: CORS_ORIGINS 禁止在生產環境使用 '*'")
            app.logger.warning("CORS_ORIGINS 包含 '*'，僅限開發環境使用")
        elif is_production and origin.startswith("http://localhost"):
            app.logger.warning("CORS_ORIGINS 包含 localhost: %s，請確認是否為誤設", origin)


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def set_security_headers(response):  # type: ignore[no-untyped-def]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers.pop("Server", None)
        if app.config.get("ENABLE_HSTS"):
            max_age = app.config.get("HSTS_MAX_AGE", 31536000)
            response.headers["Strict-Transport-Security"] = f"max-age={max_age}; includeSubDomains"
        return response


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError) -> tuple[dict, int]:
        body = error.to_dict()
        # SEC-4: 生產環境不回傳內部錯誤細節（Supabase raw error 等）
        if app.config.get("APP_ENV") == "production":
            details = body.get("error", {}).get("details")
            if isinstance(details, dict):
                details.pop("raw", None)
                if not details:
                    body["error"]["details"] = None
        return jsonify(body), error.http_status

    @app.errorhandler(404)
    def handle_not_found(_: Exception) -> tuple[dict, int]:
        error = AppError(code="NOT_FOUND", message="Resource not found", http_status=404)
        return jsonify(error.to_dict()), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(_: Exception) -> tuple[dict, int]:
        error = AppError(
            code="METHOD_NOT_ALLOWED",
            message="Method not allowed",
            http_status=405,
        )
        return jsonify(error.to_dict()), 405

    if RateLimitExceeded is not None:

        @app.errorhandler(RateLimitExceeded)
        def handle_rate_limit_exceeded(exc: Exception) -> tuple[dict, int]:
            err = AppError(code="RATE_LIMIT_EXCEEDED", message="Too Many Requests", http_status=429)
            resp = jsonify(err.to_dict())
            retry_after = getattr(exc, "retry_after", None)
            if retry_after:
                resp.headers["Retry-After"] = str(int(retry_after))
            return resp, 429

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> tuple[dict, int]:
        if RateLimitExceeded is not None and isinstance(error, RateLimitExceeded):
            err_body = AppError(
                code="RATE_LIMIT_EXCEEDED",
                message="操作過於頻繁，請稍後再試。",
                http_status=429,
            )
            resp = jsonify(err_body.to_dict())
            retry_after = getattr(error, "retry_after", None)
            if retry_after:
                resp.headers["Retry-After"] = str(int(retry_after))
            return resp, 429
        app.logger.exception("Unexpected error: %s", error)
        internal_error = AppError(
            code="INTERNAL_SERVER_ERROR",
            message="Unexpected server error",
            http_status=500,
        )
        return jsonify(internal_error.to_dict()), 500
