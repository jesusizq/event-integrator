from flask import Blueprint

health_bp = Blueprint("Health", __name__)
events_bp = Blueprint("Events", __name__)

from . import health
from . import events
