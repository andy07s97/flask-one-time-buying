import os
from dotenv import load_dotenv

def load_config(app):
    load_dotenv("/opt/<app>/.env")

    # Project paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
    INSTANCE_DIR = os.path.join(PROJECT_ROOT, "instance")

    # Ensure instance folder exists
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    # Security
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me")
    app.config["ADMIN_TOKEN"] = os.getenv("ADMIN_TOKEN", "")
    app.config["APP_CODE"] = os.getenv("APP_CODE")
    app.config["APP_TRADE_NO_PREFIX"] = os.getenv("APP_TRADE_NO_PREFIX", "CT")

    # === ECpay variables ===
    app.config["ECPAY_MERCHANT_ID"] = os.getenv("ECPAY_MERCHANT_ID")
    app.config["ECPAY_HASH_KEY"] = os.getenv("ECPAY_HASH_KEY")
    app.config["ECPAY_HASH_IV"] = os.getenv("ECPAY_HASH_IV")
    app.config["ECPAY_SERVICE_URL"] = os.getenv("ECPAY_SERVICE_URL")

    app.config["ECPAY_CLIENT_BACK_URL"] = os.getenv("ECPAY_CLIENT_BACK_URL")
    app.config["ECPAY_ORDER_RESULT_URL"] = os.getenv("ECPAY_ORDER_RESULT_URL")
    app.config["ECPAY_NOTIFY_URL"] = os.getenv("ECPAY_NOTIFY_URL")

    app.config["ECPAY_SDK_PATH"] = os.getenv("ECPAY_SDK_PATH")
    app.config["ECPAY_CHOOSE_PAYMENT"] = os.getenv("ECPAY_CHOOSE_PAYMENT")
    
    # Database (absolute path, production-safe)
    app.config["DATABASE_URL"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
