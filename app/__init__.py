import os
from flask import Flask
import logging
from config import config
from .extensions import db, migrate, cache, cors, apifairy, ma, celery


def init_celery(app, celery_instance):
    celery_instance.conf.update(
        broker_url=app.config.get("CELERY_BROKER_URL"),
        result_backend=app.config.get("CELERY_RESULT_BACKEND"),
        task_ignore_result=app.config.get("CELERY_TASK_IGNORE_RESULT", True),
    )
    celery_instance.conf.CELERY_TIMEZONE = app.config.get("CELERY_TIMEZONE", "UTC")
    celery_instance.conf.beat_schedule = app.config.get("CELERY_BEAT_SCHEDULE")

    # Ensure tasks run within the application context
    class ContextTask(celery_instance.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_instance.Task = ContextTask
    app.extensions["celery"] = celery_instance  # Register celery with app extensions
    return celery_instance


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
    init_celery(app, celery)

    # Register blueprints
    from .api import health_bp, events_bp

    app.register_blueprint(health_bp, url_prefix="/v1/health")
    app.register_blueprint(events_bp, url_prefix="/v1/events")
    return app
