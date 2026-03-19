"""Webhook 冪等測試。MVP-2.4：同一 MerchantTradeNo 重送僅處理一次。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.payment_service import payment_service

FAKE_FORM_DATA = {
    "MerchantTradeNo": "GPtest123456789012",
    "RtnCode": "1",
    "TradeNo": "2403190001",
    "TradeAmt": "100",
    "PaymentDate": "2025/03/19 12:00:00",
    "PaymentType": "Credit_CreditCard",
}


def test_webhook_duplicate_external_event_id_returns_1ok(client, app) -> None:
    """
    webhook_events INSERT 觸發 UNIQUE 違規（同 external_event_id 已存在）時，
    應回傳 1|OK 且不執行後續出票。MVP-2.4 冪等。
    """
    app.config["ECPAY_HASH_KEY"] = "test"
    app.config["ECPAY_HASH_IV"] = "test"
    with app.app_context():
        with patch("app.services.payment_service.verify_webhook_checkmac", return_value=True):
            mock_svc = MagicMock()

            def table(name):
                t = MagicMock()
                t.insert.return_value.execute.side_effect = Exception(
                    "duplicate key value violates unique constraint "
                    "'webhook_events_provider_external_event_id_key'"
                )
                return t

            mock_svc.table.side_effect = table

            with patch(
                "app.services.payment_service.supabase_client.service_role_client",
                return_value=mock_svc,
            ):
                result = payment_service.handle_ecpay_webhook(FAKE_FORM_DATA)
                assert result == "1|OK"


def test_webhook_duplicate_23505_returns_1ok(client, app) -> None:
    """PostgreSQL 錯誤碼 23505（unique_violation）亦應視為已處理。"""
    app.config["ECPAY_HASH_KEY"] = "test"
    app.config["ECPAY_HASH_IV"] = "test"
    with app.app_context():
        with patch("app.services.payment_service.verify_webhook_checkmac", return_value=True):
            mock_svc = MagicMock()

            def table(name):
                t = MagicMock()
                t.insert.return_value.execute.side_effect = Exception(
                    "insert or update violation 23505"
                )
                return t

            mock_svc.table.side_effect = table

            with patch(
                "app.services.payment_service.supabase_client.service_role_client",
                return_value=mock_svc,
            ):
                result = payment_service.handle_ecpay_webhook(FAKE_FORM_DATA)
                assert result == "1|OK"
