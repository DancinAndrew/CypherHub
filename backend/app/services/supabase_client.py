from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import Flask

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


supabase_client = SupabaseClientWrapper()
