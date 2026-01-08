from flask import Flask
from .config import load_config
from .extensions import db, migrate
from .routes.main import main_bp
from .routes.auth import auth_bp

def create_app():
    app = Flask(__name__)
    load_config(app)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")

    return app
