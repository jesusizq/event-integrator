import os
from flask import Flask
import logging
from .extensions import db, migrate, cache, cors, apifairy, ma


def create_app(config_name=None):
    """Application factory pattern"""

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if config_name is None:
        config_name = os.getenv("FLASK_CONFIG", "development")

    app = Flask(__name__)
    app.config.from_object(config_name)

    logging.getLogger(__name__).info(f"Flask app created with config: {config_name}")

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    cors.init_app(app)
    ma.init_app(app)  # Marshmallow before apifairy
    apifairy.init_app(app)

    # Register blueprints
    from .api import health_bp

    app.register_blueprint(health_bp, url_prefix="/v1/health")
    return app
