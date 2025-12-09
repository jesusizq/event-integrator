import os


class Config:
    # Base config shared by all environments
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY") or "my-secret-key"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    # We will use a list with environment variables for now.
    # In the future, providers will need to be added via the API.
    PROVIDERS = [
        {
            "name": "primary_provider",
            "url": os.environ.get("PROVIDER_API_URL"),
            "timeout": int(os.environ.get("PROVIDER_API_TIMEOUT") or 10),
        }
        # Add here future providers:
        # {
        #     "name": "another_provider",
        #     "url": os.environ.get("ANOTHER_PROVIDER_API_URL"),
        #     "timeout": 15
        # },
    ]

    # Cache settings
    CACHE_TYPE = os.environ.get("CACHE_TYPE") or "RedisCache"
    CACHE_REDIS_URL = (
        os.environ.get("CACHE_REDIS_URL") or "redis://localhost:6379/1"
    )  # Use DB 1 for cache (db 0 is typically used by Celery)
    CACHE_DEFAULT_TIMEOUT = int(
        os.environ.get("CACHE_DEFAULT_TIMEOUT") or 300
    )  # 5 minutes default

    CELERY_BROKER_URL = (
        os.environ.get("CELERY_BROKER_URL") or "redis://localhost:6379/0"
    )
    CELERY_RESULT_BACKEND = (
        os.environ.get("CELERY_RESULT_BACKEND") or "redis://localhost:6379/0"
    )
    TIMEZONE = "UTC"

    BEAT_SCHEDULE = {
        "sync-provider-events-schedule": {
            "task": "app.tasks.sync.sync_provider_events",
            "schedule": 15.0,  # Every 15 seconds to test the sync. In real scenarios, it should be every hour.
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
    CELERY_TASK_ALWAYS_EAGER = True  # Ensure tasks are executed immediately
    CELERY_TASK_EAGER_PROPAGATES = True  # Ensure task results are propagated

    CACHE_TYPE = "NullCache"


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
