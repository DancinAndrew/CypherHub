"""MVP-2 Webhook 接收端。金流回調，無 JWT。"""

from __future__ import annotations

from flask import Blueprint, Response, request

from app.services.payment_service import payment_service

bp = Blueprint("webhooks", __name__, url_prefix="/api/v1/webhooks")


@bp.post("/ecpay")
def ecpay_return() -> Response:
    """
    綠界 ReturnURL 回調。Content-Type: application/x-www-form-urlencoded。
    驗簽 → 冪等 → paid 出票。回傳純字串 1|OK。
    """
    # ECPay 傳 application/x-www-form-urlencoded
    form_data = request.form.to_dict(flat=True) if request.form else {}
    if not form_data and request.is_json:
        form_data = request.get_json(silent=True) or {}
    result = payment_service.handle_ecpay_webhook(form_data)
    return Response(result, mimetype="text/plain", status=200)
