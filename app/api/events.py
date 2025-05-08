from apifairy import arguments, response
from . import events_bp as api
from app.api.schemas import EventSearchQueryArgsSchema, SuccessResponseSchema
from app.extensions import db
from app.models.repository import EventRepository
from app.models.event import Event
from datetime import datetime


def _transform_event_to_summary(event: Event) -> dict:
    """
    Transforms an Event model instance into a dictionary conforming to EventSummarySchema.
    """
    overall_start_datetime = None
    overall_end_datetime = None
    min_overall_price = float("inf")
    max_overall_price = float("-inf")

    if event.event_plans:
        for plan in event.event_plans:
            if plan.start_date:
                current_plan_start_dt = plan.start_date
                if (
                    overall_start_datetime is None
                    or current_plan_start_dt < overall_start_datetime
                ):
                    overall_start_datetime = current_plan_start_dt
            if plan.end_date:
                current_plan_end_dt = plan.end_date
                if (
                    overall_end_datetime is None
                    or current_plan_end_dt > overall_end_datetime
                ):
                    overall_end_datetime = current_plan_end_dt

            if plan.zones:
                for zone in plan.zones:
                    if zone.price is not None:
                        min_overall_price = min(min_overall_price, zone.price)
                        max_overall_price = max(max_overall_price, zone.price)

    final_min_price = min_overall_price if min_overall_price != float("inf") else None
    final_max_price = max_overall_price if max_overall_price != float("-inf") else None

    # Pass datetime.date objects to the schema, not pre-formatted strings
    start_date_obj = overall_start_datetime.date() if overall_start_datetime else None
    start_time_obj = overall_start_datetime.time() if overall_start_datetime else None
    end_date_obj = overall_end_datetime.date() if overall_end_datetime else None
    end_time_obj = overall_end_datetime.time() if overall_end_datetime else None

    return {
        "id": event.id,
        "title": event.title,
        "start_date": start_date_obj,
        "start_time": start_time_obj,
        "end_date": end_date_obj,
        "end_time": end_time_obj,
        "min_price": final_min_price,
        "max_price": final_max_price,
    }


@api.route("/search", methods=["GET"])
@arguments(EventSearchQueryArgsSchema)
@response(SuccessResponseSchema, 200)
def search_events(args: dict):
    """
    Lists the available events within a specified time range.

    Returns only events that were ever available with "sell_mode: online".
    The endpoint relies solely on the database for quick responses.
    """
    starts_at: datetime = args.get("starts_at")
    ends_at: datetime = args.get("ends_at")

    repo = EventRepository(db.session)
    events_from_repo = repo.get_events_by_date(starts_at=starts_at, ends_at=ends_at)

    events_summary_data = [
        _transform_event_to_summary(event) for event in events_from_repo
    ]

    return {"data": {"events": events_summary_data}, "error": None}
