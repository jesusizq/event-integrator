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
