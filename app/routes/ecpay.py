# /app/routes/ecpay.py
from __future__ import annotations

import hashlib
import importlib.util
import json
import secrets
import time
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    render_template,
    request,
    send_file,
    url_for,
)

from ..extensions import db
# from ..models import DownloadToken, Order, utcnow

ecpay_bp = Blueprint("ecpay", __name__, url_prefix="/ecpay")


# ----------------------------
# Config helpers (只使用你允許的 env 對應 keys)
# ----------------------------
def _cfg(key: str, default: Any = None) -> Any:
    v = current_app.config.get(key, default)
    return default if v is None else v


def _require_cfg(key: str) -> str:
    v = _cfg(key)
    if not v:
        raise RuntimeError(f"Missing config: {key}")
    return str(v)


# ----------------------------
# Load official ECPay SDK (from ECPAY_SDK_PATH)
# ----------------------------
def _load_ecpay_sdk():
    sdk_path = _require_cfg("ECPAY_SDK_PATH")
    p = Path(sdk_path)
    if not p.exists():
        raise RuntimeError(f"ECPAY_SDK_PATH not found: {sdk_path}")

    spec = importlib.util.spec_from_file_location("ecpay_payment_sdk", sdk_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Failed to load SDK spec: {sdk_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _sdk_client():
    mod = _load_ecpay_sdk()
    merchant_id = _require_cfg("ECPAY_MERCHANT_ID")
    hash_key = _require_cfg("ECPAY_HASH_KEY")
    hash_iv = _require_cfg("ECPAY_HASH_IV")
    return mod.ECPayPaymentSdk(MerchantID=merchant_id, HashKey=hash_key, HashIV=hash_iv)


# ----------------------------
# CheckMacValue (委託官方 SDK 計算，避免規則落差)
# ----------------------------
def compute_checkmac(params: Dict[str, Any]) -> str:
    client = _sdk_client()
    # SDK 會自行補 MerchantID，且會移除 CheckMacValue 再算
    return client.generate_check_value(params)


def verify_checkmac(form: Dict[str, Any]) -> bool:
    sent = (form.get("CheckMacValue") or "").strip()
    if not sent:
        return False
    calc = compute_checkmac(form)
    return calc.upper() == sent.upper()


# ----------------------------
# MerchantTradeNo generator (<= 20 chars)
# ----------------------------
def gen_merchant_trade_no() -> str:
    prefix = (_cfg("APP_TRADE_NO_PREFIX", "NO") or "NO").strip()
    prefix = "".join([c for c in prefix if c.isalnum()])[:4]  # 安全前綴

    # 秒級時間戳 + 2 位 random；最後截到 20
    trade_no = f"{prefix}{int(time.time())}{secrets.randbelow(100):02d}"
    return trade_no[:20]


def _auto_post_html(action_url: str, params: Dict[str, Any]) -> str:
    inputs = "\n".join(
        [f'<input type="hidden" name="{k}" value="{str(v)}"/>' for k, v in params.items()]
    )
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>前往付款…</title>
</head>
<body>
  <p style="font-family:system-ui,-apple-system,Segoe UI,Roboto;padding:16px;">正在前往綠界付款頁…</p>
  <form id="ecpayForm" method="POST" action="{action_url}">
    {inputs}
  </form>
  <script>document.getElementById('ecpayForm').submit();</script>
</body>
</html>"""


def _create_or_get_token(order: Order, file_path: str, ttl_hours: int = 24) -> DownloadToken:
    now = utcnow()

    dt = (
        DownloadToken.query.filter_by(order_id=order.id)
        .order_by(DownloadToken.created_at.desc())
        .first()
    )
    if dt and dt.expires_at > now:
        if dt.file_path != file_path:
            dt.file_path = file_path
            db.session.commit()
        return dt

    token = secrets.token_urlsafe(32)
    dt = DownloadToken(
        token=token,
        order_id=order.id,
        file_path=file_path,
        expires_at=now + timedelta(hours=ttl_hours),
    )
    db.session.add(dt)
    db.session.commit()
    return dt


# ----------------------------
# POST /ecpay/create
# Server 建單 -> 回傳 auto-post HTML -> Browser POST to AioCheckOut/V5
# ----------------------------
@ecpay_bp.post("/create")
def create():
    merchant_id = _require_cfg("ECPAY_MERCHANT_ID")
    service_url = _require_cfg("ECPAY_SERVICE_URL")

    # URLs（只用你允許的 env）
    return_url = _require_cfg("ECPAY_NOTIFY_URL")          # ReturnURL (Server POST)
    order_result_url = _require_cfg("ECPAY_ORDER_RESULT_URL")
    client_back_url = _require_cfg("ECPAY_CLIENT_BACK_URL")
    choose_payment = (_cfg("ECPAY_CHOOSE_PAYMENT", "ALL") or "ALL").strip()

    app_code = (_cfg("APP_CODE", "") or "").strip()

    # MVP：金額與品名（你若怕被前端竄改，請在此 hardcode）
    # # TODO: 若某些 app 不允許前端傳 amount，請直接改成固定值
    amount = int((request.form.get("amount") or "50").strip() or 50)
    item_name = (request.form.get("item_name") or "One-time purchase").strip()

    # resume_url：若你的表單頁希望回到 step12，可傳入 /templates/<slug>/form?resume=price
    resume_url = (request.form.get("resume_url") or "").strip() or client_back_url

    # payload_json：建議前端把 sessionStorage 的資料塞入 hidden input payload_json
    payload_json = request.form.get("payload_json")
    if not payload_json:
        # fallback：把除了已知欄位外的 form 全塞入 payload_json
        known = {"amount", "item_name", "resume_url", "payload_json"}
        payload = {k: v for k, v in request.form.items() if k not in known}
        payload_json = json.dumps(payload, ensure_ascii=False)

    trade_no = gen_merchant_trade_no()

    order = Order(
        merchant_trade_no=trade_no,
        app_code=app_code,
        item_name=item_name,
        amount=amount,
        status="created",
        resume_url=resume_url,
        payload_json=payload_json,
    )
    db.session.add(order)
    db.session.commit()

    # 綠界必填參數（導頁）
    # MerchantTradeDate 格式：yyyy/MM/dd HH:mm:ss（用伺服器當地時間即可）
    from datetime import datetime as _dt
    trade_date = _dt.now().strftime("%Y/%m/%d %H:%M:%S")

    params: Dict[str, Any] = {
        "MerchantID": merchant_id,
        "MerchantTradeNo": trade_no,
        "MerchantTradeDate": trade_date,
        "PaymentType": "aio",
        "TotalAmount": amount,
        "TradeDesc": "One-time payment",
        "ItemName": item_name,
        "ReturnURL": return_url,
        "OrderResultURL": order_result_url,
        "ClientBackURL": client_back_url,
        "ChoosePayment": choose_payment,
        "EncryptType": 1,
    }

    params["CheckMacValue"] = compute_checkmac(params)

    html = _auto_post_html(service_url, params)
    return Response(html, mimetype="text/html")


# ----------------------------
# POST /ecpay/return  (ReturnURL)  - source of truth
# ----------------------------
@ecpay_bp.post("/return")
def notify_return():
    form = request.form.to_dict(flat=True)
    merchant_trade_no = (form.get("MerchantTradeNo") or "").strip()

    if not merchant_trade_no:
        return Response("0|Missing MerchantTradeNo", mimetype="text/plain")

    if not verify_checkmac(form):
        current_app.logger.warning(
            "ECPay ReturnURL CheckMacValue invalid. trade_no=%s form=%s",
            merchant_trade_no,
            form,
        )
        return Response("0|CheckMacValue Error", mimetype="text/plain")

    order = Order.query.filter_by(merchant_trade_no=merchant_trade_no).first()
    if not order:
        current_app.logger.warning("ECPay ReturnURL: order not found. trade_no=%s", merchant_trade_no)
        return Response("0|Order Not Found", mimetype="text/plain")

    # 更新回調資訊
    rtn_code = int((form.get("RtnCode") or "0").strip() or 0)
    order.rtn_code = rtn_code
    order.rtn_msg = (form.get("RtnMsg") or "").strip() or None
    order.payment_type = (form.get("PaymentType") or "").strip() or None
    order.ecpay_trade_no = (form.get("TradeNo") or "").strip() or None
    order.is_simulated = ((form.get("SimulatePaid") or "0").strip() == "1")
    order.checkmac_valid = True

    if rtn_code == 1:
        order.status = "paid"
        order.paid_at = utcnow()
    else:
        order.status = "failed"

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("ECPay ReturnURL: DB commit failed. trade_no=%s", merchant_trade_no)
        return Response("0|DB Error", mimetype="text/plain")

    return Response("1|OK", mimetype="text/plain")


# ----------------------------
# GET|POST /ecpay/order_result  (OrderResultURL) - for consumer display
# ----------------------------
@ecpay_bp.route("/order_result", methods=["GET", "POST"])
def order_result():
    merchant_trade_no = (request.values.get("MerchantTradeNo") or "").strip()

    # 回到付款資訊頁（預設用你 env 提供的 ClientBackURL）
    template_form_url = _require_cfg("ECPAY_CLIENT_BACK_URL")

    if not merchant_trade_no:
        return render_template("order_result.html", status="missing", template_form_url=template_form_url)

    order = Order.query.filter_by(merchant_trade_no=merchant_trade_no).first()
    if not order:
        return render_template(
            "order_result.html",
            status="not_found",
            merchant_trade_no=merchant_trade_no,
            template_form_url=template_form_url,
        )

    if order.resume_url:
        template_form_url = order.resume_url

    if not order.is_paid:
        status = "pending" if order.status == "created" else "failed"
        return render_template(
            "order_result.html",
            status=status,
            merchant_trade_no=order.merchant_trade_no,
            amount=order.amount,
            payment_type=order.payment_type,
            rtn_code=order.rtn_code,
            rtn_msg=order.rtn_msg,
            template_form_url=template_form_url,
        )

    # 付款已成功（以 ReturnURL + CheckMacValue 為準）
    # ---------------------------------------------------------
    # # TODO: 交付動作（依你的 app 而定）
    # 1) 若你的 app 需要產檔（例如 DOCX），請在這裡產出檔案到 GENERATED_FILES_PATH
    #    建議檔名用：<merchant_trade_no>.docx
    # 2) 若你的 app 不需要檔案下載（例如解鎖權限/寄信/顯示結果），也可在此更新 delivered_at
    # ---------------------------------------------------------

    download_url = None

    gen_dir = Path(_cfg("GENERATED_FILES_PATH", "/opt/app/generated"))
    file_path = gen_dir / f"{order.merchant_trade_no}.docx"

    if file_path.exists() and file_path.is_file():
        dt = _create_or_get_token(order, file_path=str(file_path), ttl_hours=24)
        download_url = url_for("ecpay.download", token=dt.token)

    # 若你的交付不是檔案下載，建議也可把 delivered_at 記錄下來（可選）
    if order.delivered_at is None:
        order.delivered_at = utcnow()
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    return render_template(
        "order_result.html",
        status="paid",
        merchant_trade_no=order.merchant_trade_no,
        amount=order.amount,
        payment_type=order.payment_type,
        rtn_code=order.rtn_code,
        rtn_msg=order.rtn_msg,
        download_url=download_url,
        template_form_url=template_form_url,
    )


# ----------------------------
# GET /ecpay/download/<token>
# ----------------------------
@ecpay_bp.get("/download/<token>")
def download(token: str):
    dt = DownloadToken.query.filter_by(token=token).first()
    if not dt:
        abort(404)

    now = utcnow()
    if dt.expires_at <= now:
        abort(410)

    order = Order.query.get(dt.order_id)
    if not order or not order.is_paid:
        abort(403)

    p = Path(dt.file_path)
    if not p.exists() or not p.is_file():
        abort(404)

    # 下載檔名：你可以依 app 需求調整
    filename = f"{order.merchant_trade_no}.docx"
    return send_file(p, as_attachment=True, download_name=filename)
