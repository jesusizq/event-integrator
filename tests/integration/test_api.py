import pytest
import json
from app import create_app
from app.extensions import db as _db
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from app.models.event import Event, EventPlan, Zone


@pytest.fixture(scope="session")
def app():
    """Session-wide test `Flask` application."""
    app = create_app(config_name="testing")
    return app


@pytest.fixture(scope="session")
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope="session")
def db(app):
    """Session-wide test database."""
    with app.app_context():
        # If you have Flask-Migrate, you might use:
        # from flask_migrate import upgrade
        # upgrade()
        # For simple SQLAlchemy:
        _db.create_all()

    yield _db

    # Teardown: drop all tables to ensure a clean state for subsequent test runs
    with app.app_context():
        _db.drop_all()


@pytest.fixture(scope="function")
def session(db, app):
    """Creates a new database session for a test, ensuring rollback."""
    with app.app_context():
        # The default db.session is a scoped_session.
        # We can start a nested transaction on it for test isolation.
        nested_transaction = db.session.begin_nested()

        yield db.session

        # Rollback the nested transaction after the test.
        # This will revert any changes made during the test.
        nested_transaction.rollback()


class TestEventsEndpoint:
    SEARCH_EVENTS_ENDPOINT = "/v1/events/search"
    API_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

    def _assert_bad_request_response(self, response):
        assert response.status_code == 400
        assert response.content_type == "application/json"

    def _get_search_events_response_data(
        self, client, starts_at_dt=None, ends_at_dt=None, raw_params=None
    ):
        """Helper to make GET request to search events and return parsed JSON data."""
        query_params = {}
        if raw_params:
            query_params.update(raw_params)
        else:
            if starts_at_dt:
                query_params["starts_at"] = starts_at_dt.strftime(
                    self.API_DATETIME_FORMAT
                )
            if ends_at_dt:
                query_params["ends_at"] = ends_at_dt.strftime(self.API_DATETIME_FORMAT)

        response = client.get(self.SEARCH_EVENTS_ENDPOINT, query_string=query_params)
        return response, json.loads(response.data)

    def _assert_successful_search_response(
        self, response, data, expected_event_count=None
    ):
        assert response.status_code == 200
        assert response.content_type == "application/json"
        assert isinstance(data, dict)
        assert "data" in data
        assert "events" in data["data"]
        assert isinstance(data["data"]["events"], list)
        if expected_event_count is not None:
            assert len(data["data"]["events"]) == expected_event_count
        assert "error" in data
        assert data["error"] is None

    def _assert_event_data(
        self,
        event_data_dict,
        expected_id,
        expected_title,
        expected_start_datetime,
        expected_end_datetime,
        expected_min_price,
        expected_max_price,
    ):
        """Helper to assert common fields of an event data dictionary."""
        assert event_data_dict["id"] == str(expected_id)
        assert event_data_dict["title"] == expected_title
        assert event_data_dict["start_date"] == expected_start_datetime.strftime(
            "%Y-%m-%d"
        )
        assert event_data_dict["start_time"] == expected_start_datetime.strftime(
            "%H:%M:%S"
        )
        assert event_data_dict["end_date"] == expected_end_datetime.strftime("%Y-%m-%d")
        assert event_data_dict["end_time"] == expected_end_datetime.strftime("%H:%M:%S")
        assert event_data_dict["min_price"] == expected_min_price
        assert event_data_dict["max_price"] == expected_max_price

    def test_search_events_no_params_error(self, client, session):
        """
        Test GET /v1/events/search without parameters returns 400 BAD REQUEST.
        """
        response = client.get(self.SEARCH_EVENTS_ENDPOINT)
        self._assert_bad_request_response(response)

    def test_search_events_with_valid_date_params_empty_db(self, client, session):
        """
        Test GET /v1/events/search with valid date parameters and an empty database.
        """
        starts_at = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        ends_at = datetime(2025, 1, 31, 23, 59, 59, tzinfo=timezone.utc)

        response, data = self._get_search_events_response_data(
            client, starts_at_dt=starts_at, ends_at_dt=ends_at
        )
        self._assert_successful_search_response(response, data, expected_event_count=0)

    def test_search_events_missing_ends_at_param_bad_request(self, client, session):
        """
        Test GET /v1/events/search with missing 'ends_at' parameter returns 400.
        """
        starts_at_str = "2025-01-01T00:00:00Z"
        response, _ = self._get_search_events_response_data(
            client, raw_params={"starts_at": starts_at_str}
        )
        self._assert_bad_request_response(response)

    def test_search_events_missing_starts_at_param_bad_request(self, client, session):
        """
        Test GET /v1/events/search with missing 'starts_at' parameter returns 400.
        """
        ends_at_str = "2025-01-31T23:59:59Z"
        response, _ = self._get_search_events_response_data(
            client, raw_params={"ends_at": ends_at_str}
        )
        self._assert_bad_request_response(response)

    def test_search_events_invalid_date_format_bad_request(self, client, session):
        """
        Test GET /v1/events/search with invalid date format returns 400.
        """
        valid_date_str = "2025-01-31T23:59:59Z"
        invalid_date_str = "invalid-date"

        response, _ = self._get_search_events_response_data(
            client,
            raw_params={"starts_at": invalid_date_str, "ends_at": valid_date_str},
        )
        self._assert_bad_request_response(response)

        response, _ = self._get_search_events_response_data(
            client,
            raw_params={"starts_at": valid_date_str, "ends_at": invalid_date_str},
        )
        self._assert_bad_request_response(response)

    def test_search_events_returns_event_within_date_range(self, client, session):
        """
        Test that an event within the date range and ever_online=True is returned.
        """
        event_time = datetime(2025, 7, 15, 10, 0, 0, tzinfo=timezone.utc)
        db_event, _, _ = _create_db_event_with_plan_and_zones(
            session=session,
            base_event_id="event_in_range",
            provider_name="test_prov",
            title="Event In Range",
            ever_online=True,
            plan_start_date=event_time,
            plan_end_date=event_time + timedelta(hours=2),
            zones=[
                {
                    "zone_id": "zone1",
                    "name": "Test Zone",
                    "price": 50.0,
                    "capacity": 100,
                    "is_numbered": True,
                }
            ],
        )

        starts_at_query_dt = event_time - timedelta(days=1)
        ends_at_query_dt = event_time + timedelta(days=1)

        response, data = self._get_search_events_response_data(
            client, starts_at_dt=starts_at_query_dt, ends_at_dt=ends_at_query_dt
        )
        self._assert_successful_search_response(response, data, expected_event_count=1)

        returned_event = data["data"]["events"][0]
        self._assert_event_data(
            returned_event,
            expected_id=db_event.id,
            expected_title="Event In Range",
            expected_start_datetime=event_time,
            expected_end_datetime=event_time + timedelta(hours=2),
            expected_min_price=50.0,
            expected_max_price=50.0,
        )

    def test_search_events_returns_no_event_before_date_range(self, client, session):
        """
        Test that an event starting before the query date range is not returned.
        """
        event_time = datetime(2025, 7, 10, 10, 0, 0, tzinfo=timezone.utc)
        _create_db_event_with_plan_and_zones(
            session=session,
            base_event_id="event_before_range",
            provider_name="test_prov",
            title="Event Before Range",
            ever_online=True,
            plan_start_date=event_time,  # Event is on July 10th
            plan_end_date=event_time + timedelta(hours=2),
            zones=[
                {
                    "zone_id": "zone1",
                    "name": "Test Zone",
                    "price": 10.0,
                    "capacity": 100,
                    "is_numbered": True,
                }
            ],
        )

        # Query range starts July 15th
        starts_at_query_dt = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        ends_at_query_dt = datetime(2025, 7, 20, 0, 0, 0, tzinfo=timezone.utc)

        response, data = self._get_search_events_response_data(
            client, starts_at_dt=starts_at_query_dt, ends_at_dt=ends_at_query_dt
        )
        self._assert_successful_search_response(response, data, expected_event_count=0)

    def test_search_events_returns_no_event_after_date_range(self, client, session):
        """
        Test that an event starting after the query date range is not returned.
        """
        event_time = datetime(2025, 7, 25, 10, 0, 0, tzinfo=timezone.utc)
        _create_db_event_with_plan_and_zones(
            session=session,
            base_event_id="event_after_range",
            provider_name="test_prov",
            title="Event After Range",
            ever_online=True,
            plan_start_date=event_time,  # Event is on July 25th
            plan_end_date=event_time + timedelta(hours=2),
            zones=[
                {
                    "zone_id": "zone1",
                    "name": "Test Zone",
                    "price": 10.0,
                    "capacity": 100,
                    "is_numbered": True,
                }
            ],
        )

        # Query range ends July 20th
        starts_at_query_dt = datetime(2025, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        ends_at_query_dt = datetime(2025, 7, 20, 0, 0, 0, tzinfo=timezone.utc)

        response, data = self._get_search_events_response_data(
            client, starts_at_dt=starts_at_query_dt, ends_at_dt=ends_at_query_dt
        )
        self._assert_successful_search_response(response, data, expected_event_count=0)

    def test_search_events_returns_no_event_if_not_ever_online(self, client, session):
        """
        Test that an event within the date range but ever_online=False is not returned.
        """
        event_time = datetime(2025, 7, 15, 10, 0, 0, tzinfo=timezone.utc)
        _create_db_event_with_plan_and_zones(
            session=session,
            base_event_id="event_not_online",
            provider_name="test_prov",
            title="Event Not Online",
            ever_online=False,
            plan_start_date=event_time,
            plan_end_date=event_time + timedelta(hours=2),
            zones=[
                {
                    "zone_id": "zone1",
                    "name": "Test Zone",
                    "price": 10.0,
                    "capacity": 100,
                    "is_numbered": True,
                }
            ],
        )

        starts_at_query_dt = event_time - timedelta(days=1)
        ends_at_query_dt = event_time + timedelta(days=1)

        response, data = self._get_search_events_response_data(
            client, starts_at_dt=starts_at_query_dt, ends_at_dt=ends_at_query_dt
        )
        self._assert_successful_search_response(response, data, expected_event_count=0)

    def test_search_events_returns_event_on_starts_at_boundary(self, client, session):
        """
        Test that an event starting exactly on the starts_at query boundary is returned.
        """
        event_time = datetime(2025, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
        _create_db_event_with_plan_and_zones(
            session=session,
            base_event_id="event_on_start_boundary",
            provider_name="test_prov",
            title="Event on Start Boundary",
            ever_online=True,
            plan_start_date=event_time,  # Event starts at 2025-08-01 12:00:00 UTC
            plan_end_date=event_time + timedelta(hours=2),
            zones=[
                {
                    "zone_id": "zone1",
                    "name": "Test Zone",
                    "price": 25.0,
                    "capacity": 100,
                    "is_numbered": True,
                }
            ],
        )

        # Query starts exactly at event time
        starts_at_query_dt = event_time
        ends_at_query_dt = event_time + timedelta(days=1)

        response, data = self._get_search_events_response_data(
            client, starts_at_dt=starts_at_query_dt, ends_at_dt=ends_at_query_dt
        )
        self._assert_successful_search_response(response, data, expected_event_count=1)
        returned_event = data["data"]["events"][0]
        assert returned_event["title"] == "Event on Start Boundary"

    def test_search_events_returns_event_on_ends_at_boundary(self, client, session):
        """
        Test that an event starting exactly on the ends_at query boundary is returned.
        """
        event_time = datetime(2025, 8, 5, 18, 0, 0, tzinfo=timezone.utc)
        _create_db_event_with_plan_and_zones(
            session=session,
            base_event_id="event_on_end_boundary",
            provider_name="test_prov",
            title="Event on End Boundary",
            ever_online=True,
            plan_start_date=event_time,  # Event starts at 2025-08-05 18:00:00 UTC
            plan_end_date=event_time + timedelta(hours=2),
            zones=[
                {
                    "zone_id": "zone1",
                    "name": "Test Zone",
                    "price": 35.0,
                    "capacity": 100,
                    "is_numbered": True,
                }
            ],
        )

        # Query ends exactly at event time
        starts_at_query_dt = event_time - timedelta(days=1)
        ends_at_query_dt = event_time

        response, data = self._get_search_events_response_data(
            client, starts_at_dt=starts_at_query_dt, ends_at_dt=ends_at_query_dt
        )
        self._assert_successful_search_response(response, data, expected_event_count=1)
        returned_event = data["data"]["events"][0]
        assert returned_event["title"] == "Event on End Boundary"

    def test_event_summary_multiple_zones_single_plan(self, client, session):
        """
        Test min_price and max_price aggregation for an event with one plan and multiple zones.
        """
        event_time = datetime(2025, 9, 1, 14, 0, 0, tzinfo=timezone.utc)
        plan_end_time = event_time + timedelta(hours=3)

        db_event, _, _ = _create_db_event_with_plan_and_zones(
            session=session,
            base_event_id="event_multi_zone",
            provider_name="test_prov",
            title="Event Multi Zone",
            ever_online=True,
            plan_start_date=event_time,
            plan_end_date=plan_end_time,
            zones=[
                {
                    "zone_id": "zone_cheap",
                    "name": "Cheap Zone",
                    "price": 20.0,
                    "capacity": 50,
                },
                {
                    "zone_id": "zone_mid",
                    "name": "Mid Zone",
                    "price": 40.0,
                    "capacity": 100,
                },
                {
                    "zone_id": "zone_exp",
                    "name": "Expensive Zone",
                    "price": 60.0,
                    "capacity": 30,
                },
            ],
        )

        starts_at_query_dt = event_time - timedelta(days=1)
        ends_at_query_dt = plan_end_time + timedelta(days=1)

        response, data = self._get_search_events_response_data(
            client, starts_at_dt=starts_at_query_dt, ends_at_dt=ends_at_query_dt
        )
        self._assert_successful_search_response(response, data, expected_event_count=1)

        returned_event = data["data"]["events"][0]
        self._assert_event_data(
            returned_event,
            expected_id=db_event.id,
            expected_title="Event Multi Zone",
            expected_start_datetime=event_time,
            expected_end_datetime=plan_end_time,
            expected_min_price=20.0,
            expected_max_price=60.0,
        )

    def test_event_summary_multiple_plans_one_event(self, client, session):
        """
        Test aggregation for an event with multiple plans within the query range.
        Expects earliest start_date, latest end_date, and aggregated min/max prices.
        """
        event_id_shared = uuid4()
        provider_name = "multi_plan_prov"

        # Shared Event details
        db_event = Event(
            id=event_id_shared,
            base_event_id="event_multi_plan",
            provider_name=provider_name,
            title="Event Multi Plan",
            sell_mode="online",
            ever_online=True,
            first_seen_at=datetime.now(timezone.utc) - timedelta(days=1),
            last_seen_at=datetime.now(timezone.utc),
        )
        session.add(db_event)
        session.flush()

        # Plan 1: Earlier, cheaper
        plan1_start = datetime(2025, 10, 5, 10, 0, 0, tzinfo=timezone.utc)
        plan1_end = plan1_start + timedelta(hours=2)
        db_plan1 = _create_plan_with_zones(
            session,
            db_event.id,
            provider_name,
            "plan1",
            plan1_start,
            plan1_end,
            zones=[
                {"zone_id": "p1z1", "name": "P1 Zone 1", "price": 30.0, "capacity": 50},
                {"zone_id": "p1z2", "name": "P1 Zone 2", "price": 50.0, "capacity": 50},
            ],
        )

        # Plan 2: Later, more expensive
        plan2_start = datetime(
            2025, 10, 5, 14, 0, 0, tzinfo=timezone.utc
        )  # Same day, later
        plan2_end = plan2_start + timedelta(hours=3)
        db_plan2 = _create_plan_with_zones(
            session,
            db_event.id,
            provider_name,
            "plan2",
            plan2_start,
            plan2_end,
            zones=[
                {"zone_id": "p2z1", "name": "P2 Zone 1", "price": 40.0, "capacity": 70},
                {"zone_id": "p2z2", "name": "P2 Zone 2", "price": 70.0, "capacity": 30},
            ],
        )

        # Query covers both plans
        starts_at_query_dt = plan1_start - timedelta(hours=1)
        ends_at_query_dt = plan2_end + timedelta(hours=1)

        response, data = self._get_search_events_response_data(
            client, starts_at_dt=starts_at_query_dt, ends_at_dt=ends_at_query_dt
        )
        self._assert_successful_search_response(response, data, expected_event_count=1)

        returned_event = data["data"]["events"][0]
        self._assert_event_data(
            returned_event,
            expected_id=db_event.id,
            expected_title="Event Multi Plan",
            expected_start_datetime=plan1_start,  # Earliest start
            expected_end_datetime=plan2_end,  # Latest end
            expected_min_price=30.0,  # Min price across plans
            expected_max_price=70.0,  # Max price across plans
        )

    def test_search_multiple_events_correct_filtering_and_data(self, client, session):
        """
        Test correct filtering and data for multiple events with varied properties.
        """
        now = datetime.now(timezone.utc)

        # Event 1: Matches, should be returned
        event1_time = datetime(2025, 11, 10, 10, 0, 0, tzinfo=timezone.utc)
        db_event1, _, _ = _create_db_event_with_plan_and_zones(
            session=session,
            base_event_id="event_match_1",
            provider_name="test_prov",
            title="Matching Event 1",
            ever_online=True,
            plan_start_date=event1_time,
            plan_end_date=event1_time + timedelta(hours=1),
            zones=[
                {
                    "zone_id": "zone1",
                    "name": "Test Zone",
                    "price": 10.0,
                    "capacity": 100,
                    "is_numbered": True,
                }
            ],
        )

        # Event 2: Outside date range (too early), should NOT be returned
        event2_time = datetime(2025, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
        _create_db_event_with_plan_and_zones(
            session=session,
            base_event_id="event_too_early",
            provider_name="test_prov",
            title="Too Early Event",
            ever_online=True,
            plan_start_date=event2_time,
            plan_end_date=event2_time + timedelta(hours=1),
            zones=[
                {
                    "zone_id": "zone1",
                    "name": "Test Zone",
                    "price": 10.0,
                    "capacity": 100,
                    "is_numbered": True,
                }
            ],
        )

        # Event 3: Within date range, but ever_online=False, should NOT be returned
        event3_time = datetime(2025, 11, 12, 10, 0, 0, tzinfo=timezone.utc)
        _create_db_event_with_plan_and_zones(
            session=session,
            base_event_id="event_not_online",
            provider_name="test_prov",
            title="Not Online Event",
            ever_online=False,
            plan_start_date=event3_time,
            plan_end_date=event3_time + timedelta(hours=1),
            zones=[
                {
                    "zone_id": "zone1",
                    "name": "Test Zone",
                    "price": 10.0,
                    "capacity": 100,
                    "is_numbered": True,
                }
            ],
        )

        # Event 4: Matches, should be returned (different data)
        event4_time = datetime(2025, 11, 15, 15, 0, 0, tzinfo=timezone.utc)
        event4_plan_end_time = event4_time + timedelta(hours=3)
        db_event4, _, _ = _create_db_event_with_plan_and_zones(
            session=session,
            base_event_id="event_match_2",
            provider_name="test_prov",
            title="Matching Event 2",
            ever_online=True,
            plan_start_date=event4_time,
            plan_end_date=event4_plan_end_time,
            zones=[
                {"zone_id": "e4z1", "name": "E4 Zone 1", "price": 25.0, "capacity": 20},
                {"zone_id": "e4z2", "name": "E4 Zone 2", "price": 35.0, "capacity": 30},
            ],
        )

        # Query range: 2025-11-05 to 2025-11-20
        query_start_dt = datetime(2025, 11, 5, 0, 0, 0, tzinfo=timezone.utc)
        query_end_dt = datetime(2025, 11, 20, 23, 59, 59, tzinfo=timezone.utc)

        response, data = self._get_search_events_response_data(
            client, starts_at_dt=query_start_dt, ends_at_dt=query_end_dt
        )
        self._assert_successful_search_response(response, data, expected_event_count=2)

        # Check returned events
        returned_titles = {e["title"] for e in data["data"]["events"]}
        assert "Matching Event 1" in returned_titles
        assert "Matching Event 2" in returned_titles

        for ev_data in data["data"]["events"]:
            if ev_data["title"] == "Matching Event 1":
                self._assert_event_data(
                    ev_data,
                    expected_id=db_event1.id,
                    expected_title="Matching Event 1",
                    expected_start_datetime=event1_time,
                    expected_end_datetime=event1_time + timedelta(hours=1),
                    expected_min_price=10.0,
                    expected_max_price=10.0,
                )
            elif ev_data["title"] == "Matching Event 2":
                self._assert_event_data(
                    ev_data,
                    expected_id=db_event4.id,
                    expected_title="Matching Event 2",
                    expected_start_datetime=event4_time,
                    expected_end_datetime=event4_plan_end_time,
                    expected_min_price=25.0,
                    expected_max_price=35.0,
                )

    def test_search_events_ends_at_not_after_starts_at(self, client, session):
        """
        Test GET /v1/events/search with 'ends_at' not strictly after 'starts_at'.
        Expects 400 BAD REQUEST due to schema validation.
        """
        # Case 1: ends_at == starts_at
        same_time_str = "2025-02-15T12:00:00Z"
        response, data = self._get_search_events_response_data(
            client, raw_params={"starts_at": same_time_str, "ends_at": same_time_str}
        )
        self._assert_bad_request_response(response)
        assert "messages" in data
        assert "query" in data["messages"]
        assert "_schema" in data["messages"]["query"]
        assert (
            "'ends_at' must be after 'starts_at'"
            in data["messages"]["query"]["_schema"][0]
        )

        # Case 2: ends_at < starts_at
        starts_at_str = "2025-02-15T13:00:00Z"
        ends_at_str = "2025-02-15T11:00:00Z"  # Ends before start
        response, data = self._get_search_events_response_data(
            client, raw_params={"starts_at": starts_at_str, "ends_at": ends_at_str}
        )
        self._assert_bad_request_response(response)
        assert "messages" in data
        assert "query" in data["messages"]
        assert "_schema" in data["messages"]["query"]
        assert (
            "'ends_at' must be after 'starts_at'"
            in data["messages"]["query"]["_schema"][0]
        )


def _create_db_event_with_plan_and_zones(
    session,
    base_event_id: str,
    provider_name: str,
    title: str,
    sell_mode: str = "online",
    organizer_company_id: str = "org1",
    ever_online: bool = True,
    first_seen_at: datetime = None,
    last_seen_at: datetime = None,
    # Plan details
    base_plan_id: str = "plan1",
    plan_start_date: datetime = None,
    plan_end_date: datetime = None,
    plan_sell_from: datetime = None,
    plan_sell_to: datetime = None,
    plan_sold_out: bool = False,
    # Zone details
    zones: list = None,  # None for single zone
):
    """Helper to create and save an event with one plan and potentially multiple zones."""
    now = datetime.now(timezone.utc)
    if first_seen_at is None:
        first_seen_at = now - timedelta(days=5)
    if last_seen_at is None:
        last_seen_at = now

    db_event = Event(
        base_event_id=base_event_id,
        provider_name=provider_name,
        title=title,
        sell_mode=sell_mode,
        organizer_company_id=organizer_company_id,
        ever_online=ever_online,
        first_seen_at=first_seen_at,
        last_seen_at=last_seen_at,
    )
    session.add(db_event)
    session.flush()  # Flush to get db_event.id

    plan_start_date = plan_start_date or (now + timedelta(days=10))
    plan_end_date = plan_end_date or (plan_start_date + timedelta(hours=2))
    plan_sell_from = plan_sell_from or (now - timedelta(days=30))
    plan_sell_to = plan_sell_to or (plan_start_date - timedelta(hours=1))

    db_plan = EventPlan(
        event_id=db_event.id,
        base_plan_id=base_plan_id,
        provider_name=provider_name,
        start_date=plan_start_date,
        end_date=plan_end_date,
        sell_from=plan_sell_from,
        sell_to=plan_sell_to,
        sold_out=plan_sold_out,
        first_seen_at=first_seen_at,
        last_seen_at=last_seen_at,
    )
    session.add(db_plan)
    session.flush()  # Flush to get db_plan.id

    if zones is None:
        # Default to a single zone if not provided
        zones = [
            {
                "zone_id": "zone_default",
                "name": "Default Test Zone",
                "price": 10.0,
                "capacity": 100,
                "is_numbered": True,
            }
        ]

    created_zones = []
    for zone_data in zones:
        db_zone = Zone(
            event_plan_id=db_plan.id,
            zone_id=zone_data.get("zone_id", f"zone_{uuid4().hex[:6]}"),
            name=zone_data.get("name", "Test Zone"),
            price=zone_data.get("price", 0.0),  # Default price to 0.0 if not specified
            capacity=zone_data.get("capacity", 0),
            is_numbered=zone_data.get("is_numbered", True),
            first_seen_at=first_seen_at,
            last_seen_at=last_seen_at,
        )
        session.add(db_zone)
        created_zones.append(db_zone)

    session.flush()
    # Return the main event, the plan, and the list of created zones
    return db_event, db_plan, created_zones


def _create_plan_with_zones(
    session,
    event_id: str,
    provider_name: str,
    base_plan_id: str,
    start_date: datetime,
    end_date: datetime,
    zones: list,
    sell_from: datetime = None,
    sell_to: datetime = None,
    sold_out: bool = False,
    first_seen_at: datetime = None,
    last_seen_at: datetime = None,
):
    """Helper to create an EventPlan with multiple zones and associate with an Event."""
    now = datetime.now(timezone.utc)
    first_seen_at = first_seen_at or now - timedelta(days=1)
    last_seen_at = last_seen_at or now
    sell_from = sell_from or now - timedelta(days=30)
    sell_to = sell_to or start_date - timedelta(hours=1)

    db_plan = EventPlan(
        event_id=event_id,
        base_plan_id=base_plan_id,
        provider_name=provider_name,
        start_date=start_date,
        end_date=end_date,
        sell_from=sell_from,
        sell_to=sell_to,
        sold_out=sold_out,
        first_seen_at=first_seen_at,
        last_seen_at=last_seen_at,
    )
    session.add(db_plan)
    session.flush()  # Get db_plan.id

    created_db_zones = []
    for zone_data in zones:
        db_zone = Zone(
            event_plan_id=db_plan.id,
            zone_id=zone_data["zone_id"],
            name=zone_data["name"],
            price=zone_data["price"],
            capacity=zone_data["capacity"],
            is_numbered=zone_data.get("is_numbered", True),
            first_seen_at=first_seen_at,
            last_seen_at=last_seen_at,
        )
        session.add(db_zone)
        created_db_zones.append(db_zone)

    session.flush()
    return db_plan, created_db_zones
