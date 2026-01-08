
# /app/models.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .extensions import db


def utcnow() -> datetime:
    # timezone-aware UTC (避免 naive/aware datetime 比較錯誤)
    return datetime.now(timezone.utc)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)

    # ECPay 規格 MerchantTradeNo：建議 <= 20
    merchant_trade_no = db.Column(db.String(20), unique=True, nullable=False, index=True)

    app_code = db.Column(db.String(32), nullable=False, default="app")  # 用來區分是哪個 App 產生的訂單
    product_code = db.Column(db.String(64), nullable=True)             # 你的模板/商品識別，例如 "aoa"
    item_name = db.Column(db.String(200), nullable=False, default="One-time purchase")
    amount = db.Column(db.Integer, nullable=False, default=50)

    # created / paid / failed
    status = db.Column(db.String(16), nullable=False, default="created")

    # 你前端要回去的 URL（付款 pending/failed 時用）
    resume_url = db.Column(db.Text, nullable=True)

    # 把使用者填表資料存 DB（每個 App 都能共用 DB，不用依賴本機 draft 檔案）
    payload_json = db.Column(db.Text, nullable=True)

    # 回傳診斷欄位（方便你用 DB + log 快速定位）
    checkmac_valid = db.Column(db.Boolean, nullable=False, default=False)
    rtn_code = db.Column(db.Integer, nullable=True)
    rtn_msg = db.Column(db.String(200), nullable=True)
    payment_type = db.Column(db.String(50), nullable=True)
    ecpay_trade_no = db.Column(db.String(32), nullable=True)
    is_simulated = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)
    delivered_at = db.Column(db.DateTime(timezone=True), nullable=True)

    @property
    def is_paid(self) -> bool:
        # 以 ReturnURL 背景通知為主 + CheckMacValue 通過
        return self.status == "paid" and bool(self.checkmac_valid)


class DownloadToken(db.Model):
    __tablename__ = "download_tokens"

    token = db.Column(db.String(128), primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)

    file_path = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)

    order = db.relationship("Order", backref=db.backref("download_tokens", lazy=True))
