from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any

from flask import Flask, current_app

try:
    from supabase import create_client
except Exception:  # pragma: no cover - fallback when dependency is not installed
    create_client = None


@dataclass
class SupabaseSettings:
    url: str = ""
    anon_key: str = ""


class SupabaseClientWrapper:
    def __init__(self) -> None:
        self.settings = SupabaseSettings()
        self._initialized = False

    def init_app(self, app: Flask) -> None:
        self.settings = SupabaseSettings(
            url=app.config.get("SUPABASE_URL", ""),
            anon_key=app.config.get("SUPABASE_ANON_KEY", ""),
        )
        self._initialized = True

    @staticmethod
    def _email_from_user_like(obj: dict) -> str | None:
        """Extract email from a user-like dict: email key or identities[].identity_data.email."""
        if not isinstance(obj, dict):
            return None
        email = (obj.get("email") or "").strip()
        if email:
            return email
        for ident in obj.get("identities") or []:
            if not isinstance(ident, dict):
                continue
            id_data = ident.get("identity_data") or {}
            if isinstance(id_data, dict):
                em = (id_data.get("email") or "").strip()
                if em:
                    return em
        return None

    @staticmethod
    def get_user_email_by_id(user_id: str) -> str | None:
        """Resolve user email by id via Auth Admin API (requires SUPABASE_SERVICE_ROLE_KEY).
        Handles both response shapes: { \"user\": {...} } or top-level user object.
        """
        url = current_app.config.get("SUPABASE_URL", "").rstrip("/")
        key = current_app.config.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not url or not key:
            current_app.logger.warning(
                "[auth] get_user_email_by_id: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set, cannot resolve email by user_id"
            )
            return None
        req = urllib.request.Request(
            f"{url}/auth/v1/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {key}", "apikey": key},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if not isinstance(data, dict):
                return None
            # Some versions return { "user": {...} }, others return the user at top level
            user = data.get("user") if data.get("user") is not None else data
            return SupabaseClientWrapper._email_from_user_like(user)
        except Exception as exc:
            current_app.logger.warning("[auth] get_user_email_by_id failed for %s: %s", user_id, exc)
            return None

    @property
    def initialized(self) -> bool:
        return self._initialized

    def get_settings(self) -> SupabaseSettings:
        return self.settings

    def public_client(self) -> Any:
        return self._create_client()

    def authed_client(self, jwt: str) -> Any:
        client = self._create_client()
        client.postgrest.auth(jwt)
        return client

    def get_user(self, jwt: str) -> dict[str, Any]:
        response = self.public_client().auth.get_user(jwt)
        user = getattr(response, "user", None)
        if user is None and isinstance(response, dict):
            user = response.get("user")

        if user is None:
            raise RuntimeError("Unable to resolve user from access token")

        if hasattr(user, "model_dump"):
            return user.model_dump()
        if isinstance(user, dict):
            return user

        return {"id": getattr(user, "id", None), "email": getattr(user, "email", None)}

    def call_rpc(
        self,
        function_name: str,
        params: dict[str, Any] | None = None,
        jwt: str | None = None,
    ) -> Any:
        client = self.authed_client(jwt) if jwt else self.public_client()
        response = client.rpc(function_name, params or {}).execute()
        error = self.extract_error(response)
        if error:
            raise RuntimeError(str(error))
        return self.extract_data(response)

    @staticmethod
    def extract_data(response: Any) -> Any:
        if response is None:
            return None

        if hasattr(response, "data"):
            return response.data

        if hasattr(response, "model_dump"):
            payload = response.model_dump()
            if isinstance(payload, dict) and "data" in payload:
                return payload.get("data")
            return payload

        if isinstance(response, dict):
            return response.get("data", response)

        return response

    @staticmethod
    def extract_error(response: Any) -> Any:
        if response is None:
            return None

        if hasattr(response, "error"):
            return response.error

        if hasattr(response, "model_dump"):
            payload = response.model_dump()
            if isinstance(payload, dict):
                return payload.get("error")

        if isinstance(response, dict):
            return response.get("error")

        return None

    def _create_client(self) -> Any:
        if not self.settings.url or not self.settings.anon_key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY")

        if create_client is None:
            raise RuntimeError("supabase package is not installed")

        return create_client(self.settings.url, self.settings.anon_key)

    def service_role_client(self) -> Any:
        """Client with service role (server-side only). Use for Storage upload etc."""
        url = current_app.config.get("SUPABASE_URL", "").rstrip("/")
        key = current_app.config.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not url or not key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        if create_client is None:
            raise RuntimeError("supabase package is not installed")
        return create_client(url, key)


supabase_client = SupabaseClientWrapper()
