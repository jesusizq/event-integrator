from marshmallow import fields, ValidationError, validates_schema
from app.extensions import ma


class HealthSchema(ma.Schema):
    status = fields.String(
        required=True,
        metadata={
            "description": "Indicates the health status of the service.",
            "example": "ok",
        },
    )


class EventSearchQueryArgsSchema(ma.Schema):
    starts_at = fields.DateTime(
        required=True,
        allow_none=False,
        metadata={
            "description": "Return only events that start after this date (ISO 8601 format). Example: 2017-07-21T17:32:28Z"
        },
    )
    ends_at = fields.DateTime(
        required=True,
        allow_none=False,
        metadata={
            "description": "Return only events that end before this date (ISO 8601 format). Example: 2021-07-21T17:32:28Z"
        },
    )

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data["starts_at"] >= data["ends_at"]:
            raise ValidationError("'ends_at' must be after 'starts_at'.")


class EventSummarySchema(ma.Schema):
    id = fields.UUID(
        required=True, metadata={"description": "Identifier for the event (UUID)"}
    )
    title = fields.String(required=True, metadata={"description": "Title of the event"})
    start_date = fields.Date(
        required=True,
        metadata={
            "description": "Date when the event starts in local time (YYYY-MM-DD)"
        },
    )
    start_time = fields.Time(
        required=True,
        allow_none=True,
        metadata={"description": "Time when the event starts in local time (HH:MM:SS)"},
    )
    end_date = fields.Date(
        required=True,
        allow_none=True,
        metadata={"description": "Date when the event ends in local time (YYYY-MM-DD)"},
    )
    end_time = fields.Time(
        required=True,
        allow_none=True,
        metadata={"description": "Time when the event ends in local time (HH:MM:SS)"},
    )
    min_price = fields.Float(
        required=True,
        allow_none=True,
        metadata={"description": "Min price from all the available tickets"},
    )
    max_price = fields.Float(
        required=True,
        allow_none=True,
        metadata={"description": "Max price from all the available tickets"},
    )


class EventListSchema(ma.Schema):
    events = fields.List(fields.Nested(EventSummarySchema), required=True)


class ErrorDetailSchema(ma.Schema):
    code = fields.String(required=True, metadata={"description": "Error code"})
    message = fields.String(
        required=True, metadata={"description": "Detail of the error"}
    )


class SuccessResponseSchema(ma.Schema):
    data = fields.Nested(EventListSchema, required=True)
    error = fields.Raw(
        required=True,
        allow_none=True,
        metadata={"description": "Should be null for success responses."},
    )


class ErrorResponseSchema(ma.Schema):
    data = fields.Raw(
        required=True,
        allow_none=True,
        metadata={"description": "Should be null for error responses."},
    )
    error = fields.Nested(ErrorDetailSchema, required=True)


class SearchQueryArgsSchema(ma.Schema):
    starts_at = fields.DateTime(
        required=True,
        metadata={
            "description": "Start date/time for the event search range (ISO 8601 format)."
        },
    )
    ends_at = fields.DateTime(
        required=True,
        metadata={
            "description": "End date/time for the event search range (ISO 8601 format)."
        },
    )

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data["starts_at"] >= data["ends_at"]:
            raise ValidationError("'ends_at' must be after 'starts_at'.")
        try:
            data["starts_at"].isoformat()
            data["ends_at"].isoformat()
        except (AttributeError, ValueError):
            raise ValidationError(
                "Dates must be in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)"
            )


class ZoneSchema(ma.Schema):
    id = fields.UUID(
        required=True, metadata={"description": "Unique identifier for the zone."}
    )
    name = fields.String(required=True, metadata={"description": "Name of the zone."})
    price = fields.Float(required=True, metadata={"description": "Price for the zone."})
    capacity = fields.Integer(
        required=True, metadata={"description": "Capacity of the zone."}
    )


class EventSchema(ma.Schema):
    id = fields.UUID(
        required=True,
        allow_none=False,
        metadata={"description": "Unique identifier for the event."},
    )
    title = fields.String(
        required=True, allow_none=False, metadata={"description": "Title of the event."}
    )
    starts_at = fields.DateTime(
        required=True,
        allow_none=False,
        metadata={"description": "Start date/time of the event."},
    )
    ends_at = fields.DateTime(
        required=True,
        allow_none=False,
        metadata={"description": "End date/time of the event."},
    )
    zones = fields.List(
        fields.Nested(ZoneSchema),
        required=True,
        allow_none=True,
        metadata={"description": "List of zones available for the event."},
    )
