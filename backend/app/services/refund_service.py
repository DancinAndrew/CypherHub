"""MVP-2.6 退款服務。主辦方/Admin 核准後執行 ECPay 退款。"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from flask import current_app

from app.domain.errors import AppError
from app.domain.order_state_machine import ORDER_STATE_MACHINE
from app.providers.ecpay import do_action_refund
from app.services.audit_service import audit_service
from app.services.email_service import email_service
from app.services.supabase_client import supabase_client

CREDIT_PAYMENT_PREFIXES = ("Credit_", "ApplePay", "Flexible_")


def _is_credit_card_payment(payment_type: str) -> bool:
    """ECPay DoAction 僅支援信用卡。"""
    pt = (payment_type or "").strip()
    return any(pt.startswith(p) for p in CREDIT_PAYMENT_PREFIXES)


def create_refund(order_id: UUID, admin_user_id: str | None = None) -> dict:
    """
    發起訂單全額退款。需 Admin 權限（由 blueprint 檢查）。
    流程：驗證訂單 → 取得 TradeNo → 建立 refund → 呼叫 DoAction → 更新狀態/寄信。
    """
    svc = supabase_client.service_role_client()

    order_resp = (
        svc.table("orders")
        .select("id,user_id,status,total_cents,currency")
        .eq("id", str(order_id))
        .limit(1)
        .execute()
    )
    orders = supabase_client.extract_data(order_resp) or []
    if not orders:
        raise AppError(code="ORDER_NOT_FOUND", message="Order not found", http_status=404)

    order = orders[0]
    status = order.get("status") or ""
    if not ORDER_STATE_MACHINE.can_transition(status, "refunded"):
        raise AppError(
            code="ORDER_CANNOT_REFUND",
            message=f"Order status '{status}' cannot be refunded",
            http_status=409,
        )

    pay_resp = (
        svc.table("payments")
        .select("id,external_id,amount_cents,raw_payload,status")
        .eq("order_id", str(order_id))
        .eq("provider", "ecpay")
        .limit(1)
        .execute()
    )
    pay_rows = supabase_client.extract_data(pay_resp) or []
    if not pay_rows:
        raise AppError(
            code="PAYMENT_NOT_FOUND",
            message="No ECPay payment found for this order",
            http_status=404,
        )
    payment = pay_rows[0]
    if payment.get("status") != "completed":
        raise AppError(
            code="PAYMENT_NOT_COMPLETED",
            message="Payment is not completed, cannot refund",
            http_status=409,
        )

    raw = payment.get("raw_payload") or {}
    trade_no = (raw.get("TradeNo") or "").strip()
    payment_type = (raw.get("PaymentType") or "").strip()
    merchant_trade_no = payment.get("external_id") or ""

    if not trade_no:
        raise AppError(
            code="TRADE_NO_MISSING",
            message="TradeNo not found in payment (webhook may not have run)",
            http_status=400,
        )

    if not _is_credit_card_payment(payment_type):
        raise AppError(
            code="REFUND_NOT_SUPPORTED",
            message=(
                "This payment type does not support API refund. "
                "Please process via ECPay merchant dashboard."
            ),
            http_status=400,
            details={"payment_type": payment_type},
        )

    amount_cents = order.get("total_cents") or payment.get("amount_cents") or 0
    total_ntd = max(1, amount_cents // 100)

    refund_row = {
        "order_id": str(order_id),
        "amount_cents": amount_cents,
        "status": "requested",
        "provider_trade_no": trade_no,
    }
    ref_resp = svc.table("refunds").insert(refund_row).execute()
    ref_data = supabase_client.extract_data(ref_resp) or []
    if isinstance(ref_data, dict):
        ref_data = [ref_data]
    if not ref_data:
        raise AppError(
            code="REFUND_CREATE_FAILED",
            message="Failed to create refund record",
            http_status=500,
        )
    refund_id = ref_data[0]["id"]

    mid = current_app.config.get("ECPAY_MERCHANT_ID", "").strip()
    key = current_app.config.get("ECPAY_HASH_KEY", "").strip()
    iv = current_app.config.get("ECPAY_HASH_IV", "").strip()
    is_stage = current_app.config.get("ECPAY_STAGE", True)

    if not all([mid, key, iv]):
        raise AppError(
            code="ECPAY_CONFIG_MISSING",
            message="ECPay configuration not configured",
            http_status=503,
        )

    ok, msg = do_action_refund(
        merchant_id=mid,
        merchant_trade_no=merchant_trade_no,
        trade_no=trade_no,
        total_amount_ntd=total_ntd,
        hash_key=key,
        hash_iv=iv,
        is_stage=is_stage,
    )

    now = datetime.now(UTC).isoformat()
    if ok:
        svc.table("refunds").update(
            {"status": "refunded", "processed_at": now}
        ).eq("id", str(refund_id)).execute()
        svc.table("orders").update({"status": "refunded", "updated_at": now}).eq(
            "id", str(order_id)
        ).execute()
        svc.table("payments").update({"status": "refunded"}).eq(
            "order_id", str(order_id)
        ).eq("provider", "ecpay").execute()

        user_id = str(order.get("user_id", ""))
        to_email = supabase_client.get_user_email_by_id(user_id)
        frontend_url = current_app.config.get("FRONTEND_BASE_URL", "").rstrip("/")
        amount_str = f"NT$ {amount_cents / 100:.0f}"
        try:
            email_service.send_refund_complete_email(
                to_email=to_email,
                order_id=str(order_id),
                amount_display=amount_str,
                frontend_base_url=frontend_url,
            )
        except Exception as exc:
            current_app.logger.warning("[refund] send_refund_complete_email failed: %s", exc)

        if admin_user_id:
            audit_service.log_refund(order_id, admin_user_id, amount_cents)

        return {
            "refund_id": refund_id,
            "status": "refunded",
            "message": msg,
        }
    else:
        svc.table("refunds").update(
            {"status": "failed", "processed_at": now, "raw_response": {"message": msg}}
        ).eq("id", str(refund_id)).execute()
        raise AppError(
            code="REFUND_API_FAILED",
            message=f"ECPay refund failed: {msg}",
            http_status=502,
            details={"ecpay_message": msg},
        )
