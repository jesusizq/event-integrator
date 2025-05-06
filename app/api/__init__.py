from flask import Blueprint

health_bp = Blueprint("Health", __name__, description="Health check endpoint.")
events_bp = Blueprint(
    "Events", __name__, description="API for searching and retrieving events."
)

from . import health
from . import events
