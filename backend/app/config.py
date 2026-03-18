from __future__ import annotations

import os


class Config:
    APP_ENV = os.getenv("APP_ENV", "development")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0") in {"1", "true", "True"}

    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]

    ADMIN_ALLOWLIST = {
        value.strip() for value in os.getenv("ADMIN_ALLOWLIST", "").split(",") if value.strip()
    }

    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")

    # ECPay（綠界金流）
    ECPAY_MERCHANT_ID = os.getenv("ECPAY_MERCHANT_ID", "")
    ECPAY_HASH_KEY = os.getenv("ECPAY_HASH_KEY", "")
    ECPAY_HASH_IV = os.getenv("ECPAY_HASH_IV", "")
    ECPAY_RETURN_URL = os.getenv("ECPAY_RETURN_URL", "")  # Webhook 接收網址，如 https://api.xxx.com/api/v1/webhooks/ecpay
    ECPAY_STAGE = os.getenv("ECPAY_STAGE", "1") in {"1", "true", "True"}
