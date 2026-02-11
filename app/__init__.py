from flask import Flask
from .config import load_config
from .extensions import db, migrate

from .routes.main import main_bp
from .routes.auth import auth_bp
from .routes.api import api_bp
from .routes.ecpay import ecpay_bp


def create_app():
    app = Flask(__name__)
    load_config(app)

    # 初始化 extensions（單一 db 實例）
    db.init_app(app)
    migrate.init_app(app, db)

    # Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(api_bp)
    # 寫好ecpay.py再加回來
    # app.register_blueprint(ecpay_bp)

    return app
