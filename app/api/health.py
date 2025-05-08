from . import health_bp as api
from app.api.schemas import HealthSchema
from apifairy import response


@api.route("/", methods=["GET"])
@response(HealthSchema, 200)
def health():
    return {"status": "ok"}
