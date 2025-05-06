import os


class Config:
    # Base config shared by all environments
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY") or "my-secret-key"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    PROVIDER_API_URL = (
        os.environ.get("PROVIDER_API_URL")
        or "https://provider.code-challenge.feverup.com/api/events"
    )
    PROVIDER_API_TIMEOUT = int(os.environ.get("PROVIDER_API_TIMEOUT") or 10)

    CELERY_BROKER_URL = (
        os.environ.get("CELERY_BROKER_URL") or "redis://localhost:6379/0"
    )
    CELERY_RESULT_BACKEND = (
        os.environ.get("CELERY_RESULT_BACKEND") or "redis://localhost:6379/0"
    )
    CELERY_TIMEZONE = "UTC"
    CELERY_BEAT_SCHEDULE = {
        "sync-provider-events-hourly": {
            "task": "app.tasks.sync.sync_provider_events",
            "schedule": 3600.0,  # Every hour
        },
    }


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DEV_DATABASE_URL") or Config.SQLALCHEMY_DATABASE_URI
    )


class ProductionConfig(Config):
    if (
        not Config.SECRET_KEY
        or Config.SECRET_KEY == "a-default-hardcoded-secret-key-change-me"
    ):
        raise ValueError(
            "SECRET_KEY must be set via environment variable in production"
        )
    pass


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("TEST_DATABASE_URL") or Config.SQLALCHEMY_DATABASE_URI
    )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
