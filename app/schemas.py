from marshmallow import fields, validate
from app.extensions import ma


class BlacklistSchema(ma.Schema):
    email = fields.Email(required=True, allow_none=False)
    app_uuid = fields.UUID(required=True, allow_none=False)
    blocked_reason = fields.String(
        required=False,
        allow_none=True,
        load_default=None,
        validate=validate.Length(max=255),
    )


class BlacklistLookupSchema(ma.Schema):
    is_blacklisted = fields.Boolean(required=True)
    blocked_reason = fields.String(required=False, allow_none=True)
