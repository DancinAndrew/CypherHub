"""ECPay 綠界金流 provider. 依 .cursor/skills/ecpay guides/13 CheckMacValue 實作。"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

# 全方位金流 AioCheckOut V5
ECPAY_CASHIER_URL_PROD = "https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5"
ECPAY_CASHIER_URL_STAGE = "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5"


def _ecpay_url_encode(source: str) -> str:
    """對應 UrlService::ecpayUrlEncode()：quote_plus → ~→%7E → lower → .NET 替換。
    空格必須為 + 非 %20；~ 必須編碼為 %7e。
    """
    encoded = quote_plus(source)
    encoded = encoded.replace("~", "%7E")
    encoded = encoded.lower()
    for old, new in [
        ("%2d", "-"),
        ("%5f", "_"),
        ("%2e", "."),
        ("%21", "!"),
        ("%2a", "*"),
        ("%28", "("),
        ("%29", ")"),
    ]:
        encoded = encoded.replace(old, new)
    return encoded


def _compute_checkmac(
    params: dict[str, Any], hash_key: str, hash_iv: str, exclude_empty: bool = False
) -> str:
    """依 ECPay 檢查碼機制：key 不區分大小寫排序，前加 HashKey、後加 HashIV，
    ecpayUrlEncode → SHA256 → 大寫。
    exclude_empty: True=建立訂單時略過空值；False=驗證 Webhook 時含空值。
    """
    excluded = {"CheckMacValue"}
    items = [(k, str(v)) for k, v in params.items() if k not in excluded]
    if exclude_empty:
        items = [(k, v) for k, v in items if v is not None and v != ""]
    sorted_items = sorted(items, key=lambda x: x[0].lower())
    data_str = "&".join(f"{k}={v}" for k, v in sorted_items)
    to_encode = f"HashKey={hash_key}&{data_str}&HashIV={hash_iv}"
    encoded = _ecpay_url_encode(to_encode)
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    return digest.upper()


def create_checkout_params(
    *,
    merchant_id: str,
    merchant_trade_no: str,
    total_amount: int,
    item_name: str,
    return_url: str,
    hash_key: str,
    hash_iv: str,
    trade_desc: str = "GroovePass 票券",
    choose_payment: str = "ALL",
    client_back_url: str | None = None,
    order_result_url: str | None = None,
    is_stage: bool = False,
) -> dict[str, Any]:
    """產生導向綠界金流頁的 Form 參數。total_amount 為整數（NTD）。"""
    trade_date = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    params: dict[str, Any] = {
        "MerchantID": merchant_id,
        "MerchantTradeNo": merchant_trade_no,
        "MerchantTradeDate": trade_date,
        "PaymentType": "aio",
        "TotalAmount": total_amount,
        "TradeDesc": trade_desc,
        "ItemName": item_name[:400],  # 400 字元限制
        "ReturnURL": return_url,
        "ChoosePayment": choose_payment,
        "EncryptType": 1,
    }
    if client_back_url:
        params["ClientBackURL"] = client_back_url
    if order_result_url:
        params["OrderResultURL"] = order_result_url

    params["CheckMacValue"] = _compute_checkmac(params, hash_key, hash_iv, exclude_empty=True)
    return params


def verify_webhook_checkmac(params: dict[str, Any], hash_key: str, hash_iv: str) -> bool:
    """驗證 Webhook 回傳的 CheckMacValue。params 為收到的表單資料（含 CheckMacValue）。"""
    received = (params.get("CheckMacValue") or "").strip()
    if not received:
        return False
    # Webhook 驗證時含空值，與綠界回傳格式一致
    computed = _compute_checkmac(params, hash_key, hash_iv, exclude_empty=False)
    return computed == received
