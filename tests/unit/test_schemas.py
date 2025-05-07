import pytest
from marshmallow import ValidationError
from app.api.schemas import (
    SearchQueryArgsSchema,
    EventSchema,
    ZoneSchema,
    SuccessResponseSchema,
    ErrorResponseSchema,
    ErrorDetailSchema,
    EventListSchema,
    EventSummarySchema,
)
from datetime import datetime, timedelta, timezone
import uuid


class TestSearchQueryArgsSchema:
    def test_search_query_args_valid(self):
        schema = SearchQueryArgsSchema()
        data = {"starts_at": "2023-01-01T10:00:00Z", "ends_at": "2023-01-02T10:00:00Z"}
        result = schema.load(data)
        assert isinstance(result["starts_at"], datetime)
        assert isinstance(result["ends_at"], datetime)
        assert result["starts_at"].year == 2023
        assert result["ends_at"].day == 2

    def test_search_query_args_invalid_ends_at_before_starts_at(self):
        schema = SearchQueryArgsSchema()
        data = {"starts_at": "2023-01-02T10:00:00Z", "ends_at": "2023-01-01T10:00:00Z"}
        with pytest.raises(ValidationError) as excinfo:
            schema.load(data)
        assert "'ends_at' must be after 'starts_at'" in str(excinfo.value)

    def test_search_query_args_missing_starts_at(self):
        schema = SearchQueryArgsSchema()
        data = {"ends_at": "2023-01-01T10:00:00Z"}
        with pytest.raises(ValidationError) as excinfo:
            schema.load(data)
        assert "starts_at" in excinfo.value.messages
        assert "Missing data for required field." in str(
            excinfo.value.messages["starts_at"]
        )

    def test_search_query_args_missing_ends_at(self):
        schema = SearchQueryArgsSchema()
        data = {"starts_at": "2023-01-01T10:00:00Z"}
        with pytest.raises(ValidationError) as excinfo:
            schema.load(data)
        assert "ends_at" in excinfo.value.messages
        assert "Missing data for required field." in str(
            excinfo.value.messages["ends_at"]
        )

    def test_search_query_args_invalid_date_format(self):
        schema = SearchQueryArgsSchema()
        data = {"starts_at": "not-a-date", "ends_at": "2023-01-01T10:00:00Z"}
        with pytest.raises(ValidationError) as excinfo:
            schema.load(data)
        assert "starts_at" in excinfo.value.messages
        assert "Not a valid datetime." in str(excinfo.value.messages["starts_at"])

        data2 = {"starts_at": "2023-01-01T10:00:00Z", "ends_at": "2023/01/02"}
        with pytest.raises(ValidationError) as excinfo2:
            schema.load(data2)
        assert "ends_at" in excinfo2.value.messages
        assert "Not a valid datetime." in str(excinfo2.value.messages["ends_at"])


class TestZoneSchema:
    def test_zone_schema_valid_load_dump(self):
        schema = ZoneSchema()
        zone_id = uuid.uuid4()
        data = {"id": str(zone_id), "name": "VIP Area", "price": 100.50, "capacity": 50}

        loaded_zone = schema.load(data)
        assert loaded_zone["id"] == zone_id
        assert loaded_zone["name"] == "VIP Area"
        assert loaded_zone["price"] == 100.50
        assert loaded_zone["capacity"] == 50

        dumped_zone = schema.dump(loaded_zone)
        assert dumped_zone["id"] == str(zone_id)
        assert dumped_zone["name"] == "VIP Area"
        assert dumped_zone["price"] == 100.50
        assert dumped_zone["capacity"] == 50

    def test_zone_schema_invalid_data(self):
        schema = ZoneSchema()
        # Missing required field (name)
        data_missing = {"id": str(uuid.uuid4()), "price": 10.0, "capacity": 10}
        with pytest.raises(ValidationError) as excinfo:
            schema.load(data_missing)
        assert "name" in excinfo.value.messages

        # Invalid type (price as string)
        data_invalid_type = {
            "id": str(uuid.uuid4()),
            "name": "Test",
            "price": "not-a-float",
            "capacity": 10,
        }
        with pytest.raises(ValidationError) as excinfo:
            schema.load(data_invalid_type)
        assert "price" in excinfo.value.messages
        assert "Not a valid number." in str(excinfo.value.messages["price"])


class TestEventSchema:
    def test_event_schema_valid_load_dump(self):
        schema = EventSchema()
        event_id = uuid.uuid4()
        zone_id1 = uuid.uuid4()
        zone_id2 = uuid.uuid4()
        now = datetime.now(timezone.utc)
        data = {
            "id": str(event_id),
            "title": "Fever Candlelight",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(hours=2)).isoformat(),
            "zones": [
                {
                    "id": str(zone_id1),
                    "name": "Front Row",
                    "price": 200.0,
                    "capacity": 100,
                },
                {
                    "id": str(zone_id2),
                    "name": "Balcony",
                    "price": 150.0,
                    "capacity": 200,
                },
            ],
        }
        loaded_event = schema.load(data)
        assert loaded_event["id"] == event_id
        assert loaded_event["title"] == "Fever Candlelight"
        assert loaded_event["starts_at"] == now
        assert loaded_event["ends_at"] == (now + timedelta(hours=2))
        assert len(loaded_event["zones"]) == 2
        assert loaded_event["zones"][0]["id"] == zone_id1
        assert loaded_event["zones"][1]["name"] == "Balcony"

        dumped_event = schema.dump(loaded_event)
        assert dumped_event["id"] == str(event_id)
        assert dumped_event["title"] == "Fever Candlelight"
        assert isinstance(dumped_event["starts_at"], str)
        assert isinstance(dumped_event["ends_at"], str)
        assert len(dumped_event["zones"]) == 2
        assert dumped_event["zones"][0]["id"] == str(zone_id1)

    def test_event_schema_empty_zones_list(self):
        schema = EventSchema()
        event_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        data = {
            "id": str(event_id),
            "title": "Event with no zones",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(hours=1)).isoformat(),
            "zones": [],
        }
        loaded_event = schema.load(data)
        assert loaded_event["id"] == event_id
        assert len(loaded_event["zones"]) == 0

        dumped_event = schema.dump(loaded_event)
        assert len(dumped_event["zones"]) == 0

    def test_event_schema_null_zones_allowed(self):
        schema = EventSchema()
        event_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        data = {
            "id": str(event_id),
            "title": "Event with null zones",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(hours=1)).isoformat(),
            "zones": None,
        }
        loaded_event = schema.load(data)
        assert loaded_event["id"] == event_id
        assert loaded_event["zones"] is None

        dumped_event = schema.dump(loaded_event)
        assert dumped_event["zones"] is None

    def test_event_schema_invalid_nested_zone(self):
        schema = EventSchema()
        event_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        data = {
            "id": str(event_id),
            "title": "Event with invalid zone",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(hours=2)).isoformat(),
            "zones": [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Valid Zone",
                    "price": 50.0,
                    "capacity": 10,
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "Invalid Zone",
                    "price": "not-a-price",
                    "capacity": 5,
                },  # Invalid price
            ],
        }
        with pytest.raises(ValidationError) as excinfo:
            schema.load(data)
        assert "zones" in excinfo.value.messages
        assert 1 in excinfo.value.messages["zones"]
        assert "price" in excinfo.value.messages["zones"][1]
        assert "Not a valid number." in str(excinfo.value.messages["zones"][1]["price"])

    def test_event_schema_missing_required_field(self):
        schema = EventSchema()
        # Missing id
        data = {
            "title": "Incomplete Event",
            "starts_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "zones": [],
        }
        with pytest.raises(ValidationError) as excinfo:
            schema.load(data)
        assert "id" in excinfo.value.messages
        assert "Missing data for required field." in str(excinfo.value.messages["id"])


class TestEventSummarySchema:
    def test_event_summary_schema_valid_load_dump(self):
        schema = EventSummarySchema()
        event_id = uuid.uuid4()
        data = {
            "id": str(event_id),
            "title": "Summary Event",
            "start_date": "2023-10-26",
            "start_time": "14:30:00",
            "end_date": "2023-10-26",
            "end_time": "16:30:00",
            "min_price": 25.00,
            "max_price": 75.00,
        }
        loaded_summary = schema.load(data)
        assert loaded_summary["id"] == event_id
        assert loaded_summary["title"] == "Summary Event"
        assert str(loaded_summary["start_date"]) == "2023-10-26"
        assert str(loaded_summary["start_time"]) == "14:30:00"
        assert loaded_summary["min_price"] == 25.00

        dumped_summary = schema.dump(loaded_summary)
        assert dumped_summary["id"] == str(event_id)
        assert dumped_summary["start_date"] == "2023-10-26"

    def test_event_summary_schema_optional_fields_null(self):
        schema = EventSummarySchema()
        event_id = uuid.uuid4()
        data = {
            "id": str(event_id),
            "title": "Event with null times/prices",
            "start_date": "2023-11-01",
            "start_time": None,
            "end_date": None,
            "end_time": None,
            "min_price": None,
            "max_price": None,
        }
        loaded_summary = schema.load(data)
        assert loaded_summary["id"] == event_id
        assert loaded_summary["start_time"] is None
        assert loaded_summary["end_date"] is None
        assert loaded_summary["min_price"] is None

        dumped_summary = schema.dump(loaded_summary)
        assert dumped_summary["start_time"] is None
        assert dumped_summary["min_price"] is None


class TestEventListSchema:
    def test_event_list_schema(self):
        schema = EventListSchema()
        event_id1 = uuid.uuid4()
        event_id2 = uuid.uuid4()

        # Define event data as dictionaries
        event_data1 = {
            "id": str(event_id1),
            "title": "Event One Summary",
            "start_date": "2023-01-01",
            "start_time": "10:00:00",
            "end_date": "2023-01-01",
            "end_time": "12:00:00",
            "min_price": 10.0,
            "max_price": 20.0,
        }
        event_data2 = {
            "id": str(event_id2),
            "title": "Event Two Summary",
            "start_date": "2023-01-02",
            "start_time": "15:00:00",
            "end_date": "2023-01-02",
            "end_time": "17:00:00",
            "min_price": 15.0,
            "max_price": 25.0,
        }

        data_for_list_schema = {
            "events": [
                event_data1,
                event_data2,
            ],
        }
        loaded_list = schema.load(data_for_list_schema)
        assert len(loaded_list["events"]) == 2
        assert loaded_list["events"][0]["id"] == event_id1
        assert loaded_list["events"][1]["title"] == "Event Two Summary"

        dumped_list = schema.dump(loaded_list)
        assert len(dumped_list["events"]) == 2
        assert dumped_list["events"][0]["id"] == str(event_id1)


class TestErrorDetailSchema:
    def test_error_detail_schema(self):
        schema = ErrorDetailSchema()
        data = {"code": "E404", "message": "Resource not found"}
        loaded = schema.load(data)
        assert loaded["code"] == "E404"
        assert loaded["message"] == "Resource not found"
        dumped = schema.dump(loaded)
        assert dumped == data


class TestSuccessResponseSchema:
    def test_success_response_schema(self):
        schema = SuccessResponseSchema()
        event_id = uuid.uuid4()
        event_data = {
            "events": [
                {
                    "id": str(event_id),
                    "title": "Full Event Detail",
                    "start_date": "2023-01-01",
                    "start_time": "10:00:00",
                    "end_date": "2023-01-01",
                    "end_time": "12:00:00",
                    "min_price": 10.0,
                    "max_price": 20.0,
                }
            ]
        }
        # SuccessResponseSchema contains `data` which is EventListSchema
        # And EventListSchema contains a list of EventSummarySchema.
        data_to_load = {
            "data": event_data,
            "error": None,
        }
        loaded_response = schema.load(data_to_load)
        assert loaded_response["error"] is None
        assert len(loaded_response["data"]["events"]) == 1
        assert loaded_response["data"]["events"][0]["id"] == event_id

        dumped_response = schema.dump(loaded_response)
        assert dumped_response["error"] is None
        assert dumped_response["data"]["events"][0]["id"] == str(event_id)


class TestErrorResponseSchema:
    def test_error_response_schema(self):
        schema = ErrorResponseSchema()
        error_data = {"code": "E500", "message": "Internal Server Error"}
        data_to_load = {"data": None, "error": error_data}
        loaded_response = schema.load(data_to_load)
        assert loaded_response["data"] is None
        assert loaded_response["error"]["code"] == "E500"

        dumped_response = schema.dump(loaded_response)
        assert dumped_response["data"] is None
        assert dumped_response["error"]["code"] == "E500"
