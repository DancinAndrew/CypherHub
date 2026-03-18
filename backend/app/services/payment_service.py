"""MVP-2 payment service. ECPay checkout + Webhook 驗簽、冪等、出票。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from flask import current_app

from app.domain.errors import AppError, map_supabase_error
from app.providers.ecpay import create_checkout_params, verify_webhook_checkmac

from .supabase_client import supabase_client


def _gen_merchant_trade_no(order_id: UUID) -> str:
    """ECPay MerchantTradeNo 最多 20 字元，英數字。每次 checkout 唯一。"""
    return f"GP{order_id.hex[:8]}{uuid4().hex[:8]}"[:20]


class PaymentService:
    def create_checkout(self, jwt: str, order_id: UUID) -> dict:
        """
        為 holding 訂單建立 ECPay 付款、回傳 Form 參數供前端 POST 導向金流頁。
        更新 order status → pending_payment，建立 payment 記錄。
        """
        mid = current_app.config.get("ECPAY_MERCHANT_ID", "").strip()
        key = current_app.config.get("ECPAY_HASH_KEY", "").strip()
        iv = current_app.config.get("ECPAY_HASH_IV", "").strip()
        return_url = current_app.config.get("ECPAY_RETURN_URL", "").strip()
        if not all([mid, key, iv, return_url]):
            raise AppError(
                code="ECPAY_CONFIG_MISSING",
                message="ECPay configuration not configured",
                http_status=503,
            )

        client = supabase_client.authed_client(jwt)
        # 1) 取得 order 詳情，確認 status=holding
        order_resp = (
            client.table("orders")
            .select("id,user_id,status,total_cents,currency")
            .eq("id", str(order_id))
            .limit(1)
            .execute()
        )
        orders = supabase_client.extract_data(order_resp) or []
        if not orders:
            raise AppError(code="ORDER_NOT_FOUND", message="Order not found", http_status=404)
        order = orders[0]
        if order.get("status") != "holding":
            raise AppError(
                code="ORDER_NOT_HOLDING",
                message="Order must be in holding status to checkout",
                http_status=409,
            )

        # 2) 以 service_role 建立 payment、更新 order
        svc = supabase_client.service_role_client()
        trade_no = _gen_merchant_trade_no(order_id)
        total_ntd = order["total_cents"] // 100  # 分→元
        if total_ntd < 1:
            total_ntd = 1

        # INSERT payment（UNIQUE provider, external_id）
        try:
            payment_ins = (
                svc.table("payments")
                .insert(
                    {
                        "order_id": str(order_id),
                        "provider": "ecpay",
                        "external_id": trade_no,
                        "amount_cents": order["total_cents"],
                        "currency": order.get("currency", "TWD"),
                        "status": "pending",
                    }
                )
                .execute()
            )
        except Exception as exc:
            raw = str(exc).upper()
            if "UNIQUE" in raw or "DUPLICATE" in raw:
                # 可能重複 checkout，查既有 payment 的 external_id
                pay_resp = svc.table("payments").select("external_id").eq("order_id", str(order_id)).execute()
                pay_rows = supabase_client.extract_data(pay_resp) or []
                if pay_rows:
                    trade_no = pay_rows[0]["external_id"]
            else:
                raise map_supabase_error(exc, "PAYMENT_CREATE_FAILED") from exc

        # UPDATE order → pending_payment
        svc.table("orders").update(
            {"status": "pending_payment", "updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", str(order_id)).execute()

        # 3) 產生 ECPay Form 參數
        frontend_url = current_app.config.get("FRONTEND_BASE_URL", "").rstrip("/")
        client_back = f"{frontend_url}/orders/{order_id}" if frontend_url else None

        params = create_checkout_params(
            merchant_id=mid,
            merchant_trade_no=trade_no,
            total_amount=total_ntd,
            item_name="GroovePass 活動票券",
            return_url=return_url,
            hash_key=key,
            hash_iv=iv,
            client_back_url=client_back,
            is_stage=current_app.config.get("ECPAY_STAGE", True),
        )

        cashier_url = (
            "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5"
            if current_app.config.get("ECPAY_STAGE", True)
            else "https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5"
        )

        return {
            "form_params": params,
            "cashier_url": cashier_url,
        }

    def handle_ecpay_webhook(self, form_data: dict) -> str:
        """
        處理綠界 ReturnURL 回調。驗簽 → 冪等 → paid 則出票。
        回傳 "1|OK" 給綠界（必須精確，不可多餘字元）。
        """
        key = current_app.config.get("ECPAY_HASH_KEY", "").strip()
        iv = current_app.config.get("ECPAY_HASH_IV", "").strip()
        if not key or not iv:
            current_app.logger.warning("[ecpay] HashKey/HashIV not configured")
            return "0|CONFIG_ERROR"

        # 1) 驗簽
        params = {k: (v if v is not None else "") for k, v in form_data.items()}
        if not verify_webhook_checkmac(params, key, iv):
            current_app.logger.warning("[ecpay] CheckMacValue verification failed")
            return "0|CHECKMAC_FAILED"

        rtn_code = form_data.get("RtnCode")
        try:
            rtn_code_int = int(rtn_code) if rtn_code not in (None, "") else 0
        except (TypeError, ValueError):
            rtn_code_int = 0

        if rtn_code_int != 1:
            # 非成功，仍回 1|OK 避免重送，但不做業務處理
            return "1|OK"

        simulate_paid = form_data.get("SimulatePaid")
        if str(simulate_paid) == "1":
            return "1|OK"

        merchant_trade_no = (form_data.get("MerchantTradeNo") or "").strip()
        if not merchant_trade_no:
            return "1|OK"

        # 2) 冪等：INSERT webhook_events，UNIQUE 違規 = 已處理過
        svc = supabase_client.service_role_client()
        try:
            svc.table("webhook_events").insert(
                {
                    "provider": "ecpay",
                    "external_event_id": merchant_trade_no,
                    "event_type": "payment.success",
                    "payload": {k: v for k, v in form_data.items() if k != "CheckMacValue"},
                }
            ).execute()
        except Exception as exc:
            raw = str(exc).upper()
            if "UNIQUE" in raw or "DUPLICATE" in raw or "CONFLICT" in raw or "23505" in raw:
                return "1|OK"  # 已處理過，直接回傳
            current_app.logger.exception("[ecpay] webhook insert failed: %s", exc)
            return "0|DB_ERROR"
        # 簡化：查 payments 取得 order_id，若 order 已 paid/issued 則跳過
        pay_resp = (
            svc.table("payments")
            .select("order_id,status")
            .eq("provider", "ecpay")
            .eq("external_id", merchant_trade_no)
            .limit(1)
            .execute()
        )
        pay_rows = supabase_client.extract_data(pay_resp) or []
        if not pay_rows:
            # 找不到對應 payment（理論上不該發生）
            return "1|OK"

        order_id = pay_rows[0]["order_id"]
        order_resp = svc.table("orders").select("status").eq("id", order_id).limit(1).execute()
        orders = supabase_client.extract_data(order_resp) or []
        if orders and orders[0]["status"] in ("paid", "issued"):
            return "1|OK"

        # 3) 更新 payment、order、出票
        svc.table("payments").update({"status": "completed", "raw_payload": form_data}).eq(
            "order_id", order_id
        ).eq("external_id", merchant_trade_no).execute()

        svc.table("orders").update(
            {"status": "paid", "updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", order_id).execute()

        # 4) 出票（RPC）
        try:
            svc.rpc("issue_tickets_for_order", {"p_order_id": order_id}).execute()
        except Exception as exc:
            current_app.logger.exception("[ecpay] issue_tickets_for_order failed: %s", exc)
            # 補償 job 會處理

        svc.table("webhook_events").update(
            {"processed_at": datetime.now(timezone.utc).isoformat()}
        ).eq("provider", "ecpay").eq("external_event_id", merchant_trade_no).execute()

        return "1|OK"


payment_service = PaymentService()
