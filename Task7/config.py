import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base app configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

    WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
    RATELIMIT_STORAGE_URL = os.environ.get("REDIS_URL", "memory://")
    CORS_ORIGINS = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "*").split(",")]


class DevelopmentConfig(Config):
    """Configuration used in development."""
    DEBUG = True


class ProductionConfig(Config):
    """Configuration used in production."""
    DEBUG = False


class TestingConfig(Config):
    """Configuration used in tests."""
    TESTING = True
    DEBUG = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}