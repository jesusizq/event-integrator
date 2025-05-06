import os
from flask import Flask
import logging
from config import config
from .extensions import db, migrate, cache, cors, apifairy, ma


def create_app(config_name: str | None = None):
    """Application factory."""

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if config_name is None:
        config_name = os.getenv("FLASK_CONFIG", "default")

    if config_name not in config:
        logging.warning(
            f"Configuration '{config_name}' not found. "
            f"Falling back to 'default' configuration."
        )
        config_name = "default"

    current_config_object = config[config_name]

    app = Flask(__name__)
    app.config.from_object(current_config_object)

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
