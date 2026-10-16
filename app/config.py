import os


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/blacklist",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    STATIC_API_TOKEN = os.getenv("STATIC_API_TOKEN", "static-blacklist-token")
    JSON_SORT_KEYS = False
    # Let Flask-JWT-Extended errors (401/422) reach their handlers instead of
    # being turned into 500 by Flask-RESTful.
    PROPAGATE_EXCEPTIONS = True
    AUTO_CREATE_TABLES = os.getenv("AUTO_CREATE_TABLES", "0") == "1"
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
