from __future__ import annotations

from flask import Flask, jsonify
from flask_cors import CORS

from .blueprints.admin import bp as admin_bp
from .blueprints.auth import bp as auth_bp
from .blueprints.checkin import bp as checkin_bp
from .blueprints.events import bp as events_bp
from .blueprints.me import bp as me_bp
from .blueprints.orders import bp as orders_bp
from .blueprints.payments import bp as payments_bp
from .blueprints.registrations import bp as registrations_bp
from .blueprints.settlements import bp as settlements_bp
from .blueprints.ticket_types import bp as ticket_types_bp
from .blueprints.tickets import bp as tickets_bp
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

    init_extensions(app)
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", [])}})
    _register_blueprints(app)
    _register_error_handlers(app)

    @app.get("/api/v1/health")
    def health() -> tuple[dict, int]:
        payload = HealthResponse(status="ok")
        return jsonify(payload.model_dump()), 200

    return app


def _register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp)
    app.register_blueprint(registrations_bp)  # before events so /events/<id>/register is here
    app.register_blueprint(events_bp)
    app.register_blueprint(ticket_types_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(me_bp)
    app.register_blueprint(checkin_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(settlements_bp)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError) -> tuple[dict, int]:
        return jsonify(error.to_dict()), error.http_status

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
            return jsonify(err.to_dict()), 429

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> tuple[dict, int]:
        if RateLimitExceeded is not None and isinstance(error, RateLimitExceeded):
            return (
                jsonify(
                    AppError(
                        code="RATE_LIMIT_EXCEEDED",
                        message="操作過於頻繁，請稍後再試。",
                        http_status=429,
                    ).to_dict()
                ),
                429,
            )
        app.logger.exception("Unexpected error: %s", error)
        internal_error = AppError(
            code="INTERNAL_SERVER_ERROR",
            message="Unexpected server error",
            http_status=500,
        )
        return jsonify(internal_error.to_dict()), 500
