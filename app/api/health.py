from flask import jsonify
from . import health_bp as api


@api.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200
