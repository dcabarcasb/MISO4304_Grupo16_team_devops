import os

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.config import Config
from app.extensions import db

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/blacklist_test",
)
STATIC_API_TOKEN = "test-static-token"


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = TEST_DATABASE_URL
    JWT_SECRET_KEY = "test-jwt-secret-key-with-enough-length-32"
    STATIC_API_TOKEN = STATIC_API_TOKEN


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.drop_all()
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_headers(app):
    with app.app_context():
        token = create_access_token(identity=STATIC_API_TOKEN, expires_delta=False)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def bad_token_headers(app):
    with app.app_context():
        token = create_access_token(identity="someone-else", expires_delta=False)
    return {"Authorization": f"Bearer {token}"}
