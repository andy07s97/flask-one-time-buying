# /opt/form/app/routes/ecpay.py
from __future__ import annotations

from flask import Blueprint, Response, current_app

ecpay_bp = Blueprint("ecpay", __name__, url_prefix="/ecpay")


@ecpay_bp.get("/health")
def health():
    # 讓你可以用 curl 測試 blueprint 是否可用（即使暫時不 register）
    return {"ok": True, "service": "ecpay", "registered": False}


@ecpay_bp.route("/create", methods=["GET", "POST"])
def create():
    # 最小佔位：先不要動金流邏輯，確保 migration/啟動不會因 import 而失敗
    current_app.logger.info("ECPay create endpoint called (stub).")
    return Response("ECPay stub: not implemented yet", mimetype="text/plain", status=501)


@ecpay_bp.route("/return", methods=["POST"])
def notify_return():
    # 最小佔位：回呼先回 501，之後再接 CheckMacValue / DB 更新
    current_app.logger.info("ECPay return endpoint called (stub).")
    return Response("0|Not Implemented", mimetype="text/plain", status=501)


@ecpay_bp.route("/order_result", methods=["GET", "POST"])
def order_result():
    current_app.logger.info("ECPay order_result endpoint called (stub).")
    return Response("ECPay stub: not implemented yet", mimetype="text/plain", status=501)
