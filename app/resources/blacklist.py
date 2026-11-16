from flask import current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from marshmallow import ValidationError

from app.extensions import db
from app.models import BlacklistEmail
from app.schemas import BlacklistLookupSchema, BlacklistSchema

blacklist_schema = BlacklistSchema()
lookup_schema = BlacklistLookupSchema()


def _client_ip():
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr


def _require_static_token():
    return get_jwt_identity() == current_app.config["STATIC_API_TOKEN"]


class BlacklistResource(Resource):
    @jwt_required()
    def post(self):
        if not _require_static_token():
            return {"message": "Invalid authorization token."}, 403

        payload = request.get_json(silent=True) or {}

        try:
            data = blacklist_schema.load(payload)
        except ValidationError as err:
            return {"message": "Invalid request.", "errors": err.messages}, 400

        email = str(data["email"]).strip().lower()

        existing = BlacklistEmail.query.filter_by(email=email).first()
        if existing is not None:
            return {
                "message": f"Email {email} is already in the global blacklist.",
                "created": False,
            }, 409

        entry = BlacklistEmail(
            email=email,
            app_uuid=str(data["app_uuid"]),
            blocked_reason=data.get("blocked_reason"),
            request_ip=_client_ip(),
        )
        db.session.add(entry)
        db.session.commit()

        return {
            "message": f"Email {email} was added to the global blacklist.",
            "created": True,
        }, 201


class BlacklistLookupResource(Resource):
    @jwt_required()
    def get(self, email):
        if not _require_static_token():
            return {"message": "Invalid authorization token."}, 403

        normalized = email.strip().lower()
        entry = BlacklistEmail.query.filter_by(email=normalized).first()

        result = {
            "is_blacklisted": entry is not None,
            "blocked_reason": entry.blocked_reason if entry is not None else None,
        }
        return lookup_schema.dump(result), 200
