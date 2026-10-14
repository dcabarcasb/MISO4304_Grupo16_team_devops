from datetime import timedelta

import click
from flask import Flask

from app.config import Config
from app.extensions import db, jwt, ma


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    ma.init_app(app)
    jwt.init_app(app)

    from app.resources import api_bp

    app.register_blueprint(api_bp)

    _register_commands(app)

    return app


def _register_commands(app):
    @app.cli.command("init-db")
    def init_db():
        """Create all database tables."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("create-token")
    def create_token():
        """Print a long-lived JWT bound to the configured static token."""
        from flask_jwt_extended import create_access_token

        with app.app_context():
            token = create_access_token(
                identity=app.config["STATIC_API_TOKEN"],
                expires_delta=timedelta(days=3650),
            )
        click.echo(token)
