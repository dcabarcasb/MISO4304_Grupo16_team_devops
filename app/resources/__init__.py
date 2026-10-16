from flask import Blueprint
from flask_restful import Api

from app.resources.blacklist import BlacklistResource, BlacklistLookupResource
from app.resources.health import HealthResource

api_bp = Blueprint("api", __name__)
api = Api(api_bp)

api.add_resource(HealthResource, "/health")
api.add_resource(BlacklistResource, "/blacklists")
api.add_resource(BlacklistLookupResource, "/blacklists/<string:email>")

__all__ = ["api_bp"]
