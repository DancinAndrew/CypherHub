from __future__ import annotations

from flask import current_app

from app.domain.errors import AppError

from .supabase_client import supabase_client


class AuthService:
    def _session_from_resp(self, resp: object) -> object | None:
        """Extract session from Supabase sign_in response (object or dict)."""
        session = getattr(resp, "session", None)
        if session is not None:
            return session
        data = getattr(resp, "data", None)
        if data is None:
            return None
        if hasattr(data, "session"):
            return data.session
        if isinstance(data, dict):
            return data.get("session")
        return None

    def _get_attr_or_key(self, obj: object, key: str, default: object = None) -> object:
        """Get attribute or dict key from session-like object."""
        val = getattr(obj, key, None)
        if val is not None:
            return val
        if isinstance(obj, dict):
            return obj.get(key, default)
        return default

    def _user_to_dict(self, user: object) -> dict:
        """Convert Supabase User object to JSON-serializable dict."""
        if hasattr(user, "model_dump"):
            return user.model_dump()
        if hasattr(user, "__dict__"):
            return dict(user.__dict__)
        return {"id": getattr(user, "id", None), "email": getattr(user, "email", None)}

    def login_with_password(self, email: str, password: str) -> dict:
        """Sign in via Supabase client; returns session dict or raises AppError."""
        url = current_app.config.get("SUPABASE_URL") or ""
        anon = current_app.config.get("SUPABASE_ANON_KEY") or ""
        if not url or not anon:
            raise AppError(
                code="CONFIG_ERROR",
                message="Auth not configured",
                http_status=500,
            )
        try:
            client = supabase_client.public_client()
            resp = client.auth.sign_in_with_password(
                {"email": email.strip().lower(), "password": password.strip()}
            )
        except Exception as exc:
            msg = str(exc).lower()
            invalid = (
                "invalid login credentials" in msg
                or "invalid_credentials" in msg
                or "invalid_grant" in msg
            )
            if invalid:
                raise AppError(
                    code="AUTH_FAILED",
                    message="Invalid login credentials",
                    http_status=400,
                ) from exc
            show = current_app.config.get("TESTING") or current_app.debug
            detail = f": {exc!s}" if show else ""
            raise AppError(
                code="AUTH_SERVICE_ERROR",
                message=f"Unable to reach auth service{detail}",
                http_status=502,
            ) from exc

        session = self._session_from_resp(resp)
        if not session:
            raise AppError(
                code="AUTH_FAILED",
                message="No session returned",
                http_status=400,
            )
        access_token = self._get_attr_or_key(session, "access_token")
        refresh_token = self._get_attr_or_key(session, "refresh_token")
        if not access_token or not refresh_token:
            raise AppError(
                code="AUTH_FAILED",
                message="Missing tokens in session",
                http_status=400,
            )
        user = self._get_attr_or_key(session, "user") or getattr(resp, "user", None)
        if user is not None and not isinstance(user, dict):
            user = self._user_to_dict(user)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": self._get_attr_or_key(session, "expires_in"),
            "token_type": self._get_attr_or_key(session, "token_type") or "bearer",
            "user": user,
        }


auth_service = AuthService()
