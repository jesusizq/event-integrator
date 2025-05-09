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


@pytest.fixture
def search_query_args_schema():
    return SearchQueryArgsSchema()


@pytest.fixture
def zone_schema():
    return ZoneSchema()


@pytest.fixture
def event_schema():
    return EventSchema()


@pytest.fixture
def event_summary_schema():
    return EventSummarySchema()


@pytest.fixture
def event_list_schema():
    return EventListSchema()


@pytest.fixture
def error_detail_schema():
    return ErrorDetailSchema()


@pytest.fixture
def success_response_schema():
    return SuccessResponseSchema()


@pytest.fixture
def error_response_schema():
    return ErrorResponseSchema()


@pytest.fixture
def now_utc():
    return datetime.now(timezone.utc)


@pytest.fixture
def new_uuid():
    return uuid.uuid4()


@pytest.fixture
def zone_data_factory():
    def _factory(zone_id=None, name="Sample Zone", price=50.0, capacity=20):
        actual_zone_id = zone_id if zone_id else uuid.uuid4()
        return {
            "id": str(actual_zone_id),
            "name": name,
            "price": price,
            "capacity": capacity,
        }, actual_zone_id

    return _factory


@pytest.fixture
def packaged_event_summary_data(new_uuid):
    event_id = new_uuid
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
    return data, event_id


class TestSearchQueryArgsSchema:
    def test_search_query_args_valid(self, search_query_args_schema):
        data = {"starts_at": "2023-01-01T10:00:00Z", "ends_at": "2023-01-02T10:00:00Z"}
        result = search_query_args_schema.load(data)
        assert isinstance(result["starts_at"], datetime)
        assert isinstance(result["ends_at"], datetime)
        assert result["starts_at"].year == 2023
        assert result["ends_at"].day == 2

    def test_search_query_args_invalid_ends_at_before_starts_at(
        self, search_query_args_schema
    ):
        data = {"starts_at": "2023-01-02T10:00:00Z", "ends_at": "2023-01-01T10:00:00Z"}
        with pytest.raises(ValidationError) as excinfo:
            search_query_args_schema.load(data)
        assert "'ends_at' must be after 'starts_at'" in str(excinfo.value)

    @pytest.mark.parametrize(
        "data, missing_field",
        [
            ({"ends_at": "2023-01-01T10:00:00Z"}, "starts_at"),
            ({"starts_at": "2023-01-01T10:00:00Z"}, "ends_at"),
        ],
    )
    def test_search_query_args_missing_required_field(
        self, search_query_args_schema, data, missing_field
    ):
        with pytest.raises(ValidationError) as excinfo:
            search_query_args_schema.load(data)
        assert missing_field in excinfo.value.messages
        assert "Missing data for required field." in str(
            excinfo.value.messages[missing_field]
        )

    @pytest.mark.parametrize(
        "data, invalid_field, error_message",
        [
            (
                {"starts_at": "not-a-date", "ends_at": "2023-01-01T10:00:00Z"},
                "starts_at",
                "Not a valid datetime.",
            ),
            (
                {"starts_at": "2023-01-01T10:00:00Z", "ends_at": "2023/01/02"},
                "ends_at",
                "Not a valid datetime.",
            ),
        ],
    )
    def test_search_query_args_invalid_date_format(
        self, search_query_args_schema, data, invalid_field, error_message
    ):
        with pytest.raises(ValidationError) as excinfo:
            search_query_args_schema.load(data)
        assert invalid_field in excinfo.value.messages
        assert error_message in str(excinfo.value.messages[invalid_field])


class TestZoneSchema:
    def test_zone_schema_valid_load_dump(
        self, zone_schema, zone_data_factory, new_uuid
    ):
        zone_id_for_test = new_uuid  # Control the UUID for this specific test
        data, returned_uuid = zone_data_factory(
            zone_id=zone_id_for_test, name="VIP Area", price=100.50, capacity=50
        )
        assert (
            zone_id_for_test == returned_uuid
        )  # Ensure factory used the one we passed

        loaded_zone = zone_schema.load(data)
        assert loaded_zone["id"] == zone_id_for_test
        assert loaded_zone["name"] == data["name"]
        assert loaded_zone["price"] == data["price"]
        assert loaded_zone["capacity"] == data["capacity"]

        dumped_zone = zone_schema.dump(loaded_zone)
        assert dumped_zone["id"] == str(zone_id_for_test)
        assert dumped_zone["name"] == data["name"]
        assert dumped_zone["price"] == data["price"]
        assert dumped_zone["capacity"] == data["capacity"]

    @pytest.mark.parametrize(
        "invalid_data_builder, error_field, error_message_part",
        [
            (
                lambda u_id: {"id": str(u_id), "price": 10.0, "capacity": 10},
                "name",
                "Missing data for required field.",
            ),  # Missing name
            (
                lambda u_id: {
                    "id": str(u_id),
                    "name": "Test",
                    "price": "not-a-float",
                    "capacity": 10,
                },
                "price",
                "Not a valid number.",
            ),  # Invalid price type
        ],
    )
    def test_zone_schema_invalid_data(
        self,
        zone_schema,
        invalid_data_builder,
        error_field,
        error_message_part,
        new_uuid,
    ):
        invalid_data = invalid_data_builder(new_uuid)
        with pytest.raises(ValidationError) as excinfo:
            zone_schema.load(invalid_data)
        assert error_field in excinfo.value.messages
        assert error_message_part in str(excinfo.value.messages[error_field])


class TestEventSchema:
    @pytest.fixture
    def full_valid_event_data_package(self, new_uuid, now_utc, zone_data_factory):
        event_id = new_uuid
        current_time = now_utc

        zone1_raw_data, zone1_id = zone_data_factory(
            name="Front Row", price=200.0, capacity=100
        )
        zone2_raw_data, zone2_id = zone_data_factory(
            name="Balcony", price=150.0, capacity=200
        )

        event_data = {
            "id": str(event_id),
            "title": "Fever Candlelight",
            "starts_at": current_time.isoformat(),
            "ends_at": (current_time + timedelta(hours=2)).isoformat(),
            "zones": [zone1_raw_data, zone2_raw_data],
        }
        return event_data, event_id, current_time, zone1_id, zone2_id

    def test_event_schema_valid_load_dump(
        self, event_schema, full_valid_event_data_package
    ):
        data, event_id, now, zone1_id, zone2_id = full_valid_event_data_package

        loaded_event = event_schema.load(data)
        assert loaded_event["id"] == event_id
        assert loaded_event["title"] == data["title"]
        assert loaded_event["starts_at"] == now
        assert loaded_event["ends_at"] == (now + timedelta(hours=2))
        assert len(loaded_event["zones"]) == 2
        assert loaded_event["zones"][0]["id"] == zone1_id
        assert (
            loaded_event["zones"][0]["name"] == "Front Row"
        )  # Example assertion for zone content
        assert loaded_event["zones"][1]["id"] == zone2_id
        assert loaded_event["zones"][1]["name"] == "Balcony"

        dumped_event = event_schema.dump(loaded_event)
        assert dumped_event["id"] == str(event_id)
        assert dumped_event["title"] == data["title"]
        assert isinstance(dumped_event["starts_at"], str)
        assert isinstance(dumped_event["ends_at"], str)
        assert len(dumped_event["zones"]) == 2
        assert dumped_event["zones"][0]["id"] == str(zone1_id)
        assert dumped_event["zones"][1]["id"] == str(zone2_id)

    @pytest.mark.parametrize("zones_value", [[], None])
    def test_event_schema_empty_or_null_zones(
        self, event_schema, new_uuid, now_utc, zones_value
    ):
        event_id = new_uuid
        data = {
            "id": str(event_id),
            "title": f"Event with {'empty list' if isinstance(zones_value, list) else 'null'} zones",
            "starts_at": now_utc.isoformat(),
            "ends_at": (now_utc + timedelta(hours=1)).isoformat(),
            "zones": zones_value,
        }
        loaded_event = event_schema.load(data)
        assert loaded_event["id"] == event_id
        if isinstance(zones_value, list):
            assert loaded_event["zones"] == []
        else:
            assert loaded_event["zones"] is None

        dumped_event = event_schema.dump(loaded_event)
        if isinstance(zones_value, list):
            assert dumped_event["zones"] == []
        else:
            assert dumped_event["zones"] is None

    def test_event_schema_invalid_nested_zone(
        self, event_schema, new_uuid, now_utc, zone_data_factory
    ):
        event_id = new_uuid
        valid_zone_data, _ = zone_data_factory(
            name="Valid Zone", price=50.0, capacity=10
        )

        data = {
            "id": str(event_id),
            "title": "Event with invalid zone",
            "starts_at": now_utc.isoformat(),
            "ends_at": (now_utc + timedelta(hours=2)).isoformat(),
            "zones": [
                valid_zone_data,
                {  # Manually define invalid zone data
                    "id": str(uuid.uuid4()),
                    "name": "Invalid Zone",
                    "price": "not-a-price",  # Invalid price type
                    "capacity": 5,
                },
            ],
        }
        with pytest.raises(ValidationError) as excinfo:
            event_schema.load(data)
        assert "zones" in excinfo.value.messages
        assert (
            1 in excinfo.value.messages["zones"]
        )  # Error is in the second zone (index 1)
        assert "price" in excinfo.value.messages["zones"][1]
        assert "Not a valid number." in str(excinfo.value.messages["zones"][1]["price"])

    def test_event_schema_missing_required_field(self, event_schema, now_utc):
        # Missing id
        data = {
            "title": "Incomplete Event",
            "starts_at": now_utc.isoformat(),
            "ends_at": (now_utc + timedelta(hours=1)).isoformat(),
            "zones": [],
        }
        with pytest.raises(ValidationError) as excinfo:
            event_schema.load(data)
        assert "id" in excinfo.value.messages
        assert "Missing data for required field." in str(excinfo.value.messages["id"])


class TestEventSummarySchema:
    def test_event_summary_schema_valid_load_dump(
        self, event_summary_schema, packaged_event_summary_data
    ):
        data, event_id = packaged_event_summary_data

        loaded_summary = event_summary_schema.load(data)
        assert loaded_summary["id"] == event_id
        assert loaded_summary["title"] == data["title"]
        assert str(loaded_summary["start_date"]) == data["start_date"]
        assert str(loaded_summary["start_time"]) == data["start_time"]
        assert loaded_summary["min_price"] == data["min_price"]

        dumped_summary = event_summary_schema.dump(loaded_summary)
        assert dumped_summary["id"] == str(event_id)
        assert dumped_summary["start_date"] == data["start_date"]
        assert dumped_summary["title"] == data["title"]

    def test_event_summary_schema_optional_fields_null(
        self, event_summary_schema, new_uuid
    ):
        event_id = new_uuid
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
        loaded_summary = event_summary_schema.load(data)
        assert loaded_summary["id"] == event_id
        assert loaded_summary["start_time"] is None
        assert loaded_summary["end_date"] is None
        assert loaded_summary["min_price"] is None

        dumped_summary = event_summary_schema.dump(loaded_summary)
        assert dumped_summary["start_time"] is None
        assert dumped_summary["min_price"] is None


class TestEventListSchema:
    def test_event_list_schema(
        self, event_list_schema, packaged_event_summary_data, new_uuid
    ):
        event_data1, event_id1 = packaged_event_summary_data

        event_id2 = new_uuid  # For the second event
        event_data2 = {  # Create a distinct second event summary
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
            "events": [event_data1, event_data2],
        }
        loaded_list = event_list_schema.load(data_for_list_schema)
        assert len(loaded_list["events"]) == 2
        assert loaded_list["events"][0]["id"] == event_id1
        assert loaded_list["events"][0]["title"] == event_data1["title"]
        assert loaded_list["events"][1]["id"] == event_id2
        assert loaded_list["events"][1]["title"] == event_data2["title"]

        dumped_list = event_list_schema.dump(loaded_list)
        assert len(dumped_list["events"]) == 2
        assert dumped_list["events"][0]["id"] == str(event_id1)
        assert dumped_list["events"][1]["id"] == str(event_id2)


class TestErrorDetailSchema:
    def test_error_detail_schema(self, error_detail_schema):
        data = {"code": "E404", "message": "Resource not found"}
        loaded = error_detail_schema.load(data)
        assert loaded["code"] == data["code"]
        assert loaded["message"] == data["message"]
        dumped = error_detail_schema.dump(loaded)
        assert dumped == data


class TestSuccessResponseSchema:
    def test_success_response_schema(
        self, success_response_schema, packaged_event_summary_data
    ):
        event_summary_d, event_id = packaged_event_summary_data

        event_list_content = {"events": [event_summary_d]}
        data_to_load = {
            "data": event_list_content,
            "error": None,
        }
        loaded_response = success_response_schema.load(data_to_load)
        assert loaded_response["error"] is None
        assert loaded_response["data"] is not None
        assert len(loaded_response["data"]["events"]) == 1
        assert loaded_response["data"]["events"][0]["id"] == event_id
        assert loaded_response["data"]["events"][0]["title"] == event_summary_d["title"]

        dumped_response = success_response_schema.dump(loaded_response)
        assert dumped_response["error"] is None
        assert dumped_response["data"] is not None
        assert len(dumped_response["data"]["events"]) == 1
        assert dumped_response["data"]["events"][0]["id"] == str(event_id)


class TestErrorResponseSchema:
    @pytest.fixture
    def sample_error_detail_data(self):
        return {"code": "E500", "message": "Internal Server Error"}

    def test_error_response_schema(
        self, error_response_schema, sample_error_detail_data
    ):
        data_to_load = {"data": None, "error": sample_error_detail_data}

        loaded_response = error_response_schema.load(data_to_load)
        assert loaded_response["data"] is None
        assert loaded_response["error"] is not None
        assert loaded_response["error"]["code"] == sample_error_detail_data["code"]
        assert (
            loaded_response["error"]["message"] == sample_error_detail_data["message"]
        )

        dumped_response = error_response_schema.dump(loaded_response)
        assert dumped_response["data"] is None
        assert dumped_response["error"] is not None
        assert dumped_response["error"]["code"] == sample_error_detail_data["code"]
