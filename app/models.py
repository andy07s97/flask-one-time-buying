# /app/models.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .extensions import db


def utcnow() -> datetime:
    """
    一律使用 naive UTC，避免 SQLite/SQLAlchemy 常見的 aware/naive datetime 比較錯誤。
    """
    return datetime.utcnow()


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)

    # 綠界規格：MerchantTradeNo 建議 <= 20（實務上請務必遵守）
    merchant_trade_no = db.Column(db.String(20), unique=True, nullable=False, index=True)

    # 用來標記是哪個 app 建的單（共用 DB 時會很有用；即便每 app 一個 DB 保留也無妨）
    app_code = db.Column(db.String(64), nullable=True, default="")

    # 業務欄位（MVP）
    item_name = db.Column(db.String(200), nullable=False, default="One-time purchase")
    amount = db.Column(db.Integer, nullable=False, default=50)

    # 狀態：created / paid / failed
    status = db.Column(db.String(16), nullable=False, default="created")

    # 用來讓使用者付款 pending/failed 時回到你指定的位置（例如 /templates/<slug>/form?resume=price）
    resume_url = db.Column(db.Text, nullable=True)

    # （可選）把使用者填表資料存 DB，讓你之後「交付」時可用
    payload_json = db.Column(db.Text, nullable=True)

    # 回傳驗證與回調資訊（方便你用 DB + log 迅速定位）
    checkmac_valid = db.Column(db.Boolean, nullable=False, default=False)
    rtn_code = db.Column(db.Integer, nullable=True)
    rtn_msg = db.Column(db.String(200), nullable=True)
    payment_type = db.Column(db.String(50), nullable=True)
    ecpay_trade_no = db.Column(db.String(32), nullable=True)
    is_simulated = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)

    @property
    def is_paid(self) -> bool:
        # 以 ReturnURL 背景通知為主 + CheckMacValue 通過
        return self.status == "paid" and bool(self.checkmac_valid)


class DownloadToken(db.Model):
    __tablename__ = "download_tokens"

    token = db.Column(db.String(128), primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)

    # 若你的 app 有產出檔案（例如 DOCX），放絕對路徑在這裡
    file_path = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    order = db.relationship("Order", backref=db.backref("download_tokens", lazy=True))
