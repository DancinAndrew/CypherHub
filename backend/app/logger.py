from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from flask import Flask, g, has_request_context, request

UTC = getattr(datetime, "UTC", UTC)


class JSONFormatter(logging.Formatter):
    """Formatter that outputs JSON strings after parsing the LogRecord."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        if has_request_context():
            log_data["trace_id"] = getattr(g, "trace_id", None)
            log_data["user_id"] = getattr(g, "user_id", None)
            log_data["method"] = request.method
            log_data["path"] = request.path
            log_data["remote_addr"] = request.remote_addr

        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_structured_logging(app: Flask) -> None:
    """Configures the Flask app to use structured JSON logging."""
    # Remove default Flask handlers
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)

    # Create stream handler with JSON formatter
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO if app.config.get("APP_ENV") == "production" else logging.DEBUG)
    
    # Set werkzeug and gunicorn logger to use the same handler if needed
    logging.getLogger("werkzeug").addHandler(handler)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    @app.before_request
    def assign_trace_id() -> None:
        """Assign a unique trace ID to each request."""
        g.trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))

