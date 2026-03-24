"""Webhook 簽名驗證失敗場景測試。驗證 invalid CheckMacValue 被拒絕。"""

from __future__ import annotations

from app.services.payment_service import payment_service


def test_webhook_rejects_invalid_checkmac(client, app) -> None:
    """CheckMacValue 驗證失敗時回傳 0|CHECKMAC_FAILED。"""
    app.config["ECPAY_HASH_KEY"] = "testkey"
    app.config["ECPAY_HASH_IV"] = "testiv"

    form_data = {
        "MerchantTradeNo": "GPtest123456789012",
        "RtnCode": "1",
        "TradeNo": "2403190001",
        "CheckMacValue": "INVALID_MAC_VALUE",
    }

    with app.app_context():
        result = payment_service.handle_ecpay_webhook(form_data)
    assert result == "0|CHECKMAC_FAILED"


def test_webhook_rejects_missing_checkmac(client, app) -> None:
    """缺少 CheckMacValue 時回傳 0|CHECKMAC_FAILED。"""
    app.config["ECPAY_HASH_KEY"] = "testkey"
    app.config["ECPAY_HASH_IV"] = "testiv"

    form_data = {
        "MerchantTradeNo": "GPtest123456789012",
        "RtnCode": "1",
    }

    with app.app_context():
        result = payment_service.handle_ecpay_webhook(form_data)
    assert result == "0|CHECKMAC_FAILED"


def test_webhook_rejects_empty_checkmac(client, app) -> None:
    """空字串 CheckMacValue 時回傳 0|CHECKMAC_FAILED。"""
    app.config["ECPAY_HASH_KEY"] = "testkey"
    app.config["ECPAY_HASH_IV"] = "testiv"

    form_data = {
        "MerchantTradeNo": "GPtest123456789012",
        "RtnCode": "1",
        "CheckMacValue": "",
    }

    with app.app_context():
        result = payment_service.handle_ecpay_webhook(form_data)
    assert result == "0|CHECKMAC_FAILED"


def test_webhook_returns_config_error_when_keys_missing(client, app) -> None:
    """HashKey/HashIV 未設定時回傳 0|CONFIG_ERROR。"""
    app.config["ECPAY_HASH_KEY"] = ""
    app.config["ECPAY_HASH_IV"] = ""

    form_data = {
        "MerchantTradeNo": "GPtest123456789012",
        "RtnCode": "1",
        "CheckMacValue": "SOMEMAC",
    }

    with app.app_context():
        result = payment_service.handle_ecpay_webhook(form_data)
    assert result == "0|CONFIG_ERROR"


def test_webhook_endpoint_returns_checkmac_failed_via_http(client, app) -> None:
    """透過 HTTP POST 端點驗證 CheckMacValue 失敗時仍回傳 200 + 0|CHECKMAC_FAILED。"""
    app.config["ECPAY_HASH_KEY"] = "testkey"
    app.config["ECPAY_HASH_IV"] = "testiv"

    resp = client.post(
        "/api/v1/webhooks/ecpay",
        data={
            "MerchantTradeNo": "GPtest123456789012",
            "RtnCode": "1",
            "CheckMacValue": "BAD_MAC",
        },
        content_type="application/x-www-form-urlencoded",
    )

    assert resp.status_code == 200
    assert resp.data.decode() == "0|CHECKMAC_FAILED"
