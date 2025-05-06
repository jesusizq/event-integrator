from flask import Blueprint

health_bp = Blueprint("Health", __name__)

from . import health
