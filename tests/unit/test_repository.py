import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from app import create_app
from app.models.repository import EventRepository
from app.models.event import (
    Event as ActualEvent,
    EventPlan as ActualEventPlan,
    Zone as ActualZone,
)
from app.core.parsing_schemas import ParsedEvent, ParsedEventPlan, ParsedZone
from sqlalchemy.exc import SQLAlchemyError


def create_parsed_zone(
    zone_id: str = "zone1",
    name: str = "Test Zone",
    price: float = 10.0,
    capacity: int = 100,
    numbered: bool = True,
) -> ParsedZone:
    return ParsedZone(
        id=zone_id, name=name, price=price, capacity=capacity, numbered=numbered
    )


def create_parsed_plan(
    plan_id: str = "plan1",
    start_date: datetime = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
    end_date: datetime = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    sell_from: datetime = datetime(2023, 12, 1, 0, 0, 0, tzinfo=timezone.utc),
    sell_to: datetime = datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
    sold_out: bool = False,
    zones: list[ParsedZone] = None,
) -> ParsedEventPlan:
    if zones is None:
        zones = [create_parsed_zone()]
    return ParsedEventPlan(
        id=plan_id,
        start_date=start_date,
        end_date=end_date,
        sell_from=sell_from,
        sell_to=sell_to,
        sold_out=sold_out,
        zones=zones,
    )


def create_parsed_event(
    event_id: str = "event1",
    title: str = "Test Event",
    sell_mode: str = "online",
    organizer_company_id: str = "org1",
    event_plans: list[ParsedEventPlan] = None,
    provider_name: str = "test_provider",
) -> ParsedEvent:
    if event_plans is None:
        event_plans = [create_parsed_plan()]
    return ParsedEvent(
        id=event_id,
        title=title,
        sell_mode=sell_mode,
        organizer_company_id=organizer_company_id,
        event_plans=event_plans,
        provider_name=provider_name,
    )


@pytest.fixture(scope="session")
def test_app():
    app = create_app(config_name="testing")
    return app


@pytest.fixture
def app_context(test_app):
    with test_app.app_context():
        yield


@pytest.fixture
def mock_db_session():
    session = MagicMock(spec=["query", "add", "commit", "rollback", "flush"])

    # --- Query chain mocks ---
    query_mock_event_chain = MagicMock(name="query_mock_event_chain")
    query_mock_event_plan_chain = MagicMock(name="query_mock_event_plan_chain")
    query_mock_zone_chain = MagicMock(name="query_mock_zone_chain")
    default_query_chain = MagicMock(name="default_query_chain")

    # This map routes a model class (actual or a mock passed to query) to its query chain mock
    # It's initialized with actual model classes. Tests will add mappings for mocked classes.
    session.query_route_map = {
        ActualEvent: query_mock_event_chain,
        ActualEventPlan: query_mock_event_plan_chain,
        ActualZone: query_mock_zone_chain,
    }

    def query_side_effect(model_class_passed_to_query, **kwargs):
        return session.query_route_map.get(
            model_class_passed_to_query, default_query_chain
        )

    session.query.side_effect = query_side_effect

    # Store these specific query chain mocks on the session for tests to access them
    # for configuring filter_by, first, all, etc. related to *actual* types.
    session.query_chain_mocks_for_actual_types = {
        ActualEvent: query_mock_event_chain,
        ActualEventPlan: query_mock_event_plan_chain,
        ActualZone: query_mock_zone_chain,
        "default": default_query_chain,
    }

    # --- Setup default behaviors for common chains ---
    # For .first() returning None by default (item not found)
    query_mock_event_chain.filter_by.return_value.first.return_value = None
    query_mock_event_plan_chain.filter_by.return_value.first.return_value = None
    query_mock_zone_chain.filter_by.return_value.first.return_value = None
    default_query_chain.filter_by.return_value.first.return_value = None

    # For .all() returning [] by default
    query_mock_event_chain.filter.return_value.all.return_value = []
    query_mock_event_plan_chain.filter.return_value.all.return_value = []
    query_mock_zone_chain.filter.return_value.all.return_value = []

    # For the get_events_by_date chain specifically on query_mock_event_chain
    # (assuming get_events_by_date queries Event primarily)
    options_mock = query_mock_event_chain.options.return_value
    join_mock = options_mock.join.return_value
    filter_mock = join_mock.filter.return_value
    distinct_mock = filter_mock.distinct.return_value
    distinct_mock.all.return_value = []

    return session


@pytest.fixture
def event_repository(mock_db_session):
    return EventRepository(mock_db_session)


@pytest.fixture
def mock_upsert_dependencies(mock_db_session):
    with patch("app.models.repository.datetime") as mock_datetime, patch(
        "app.models.repository.Event"
    ) as mock_event_class, patch(
        "app.models.repository.EventPlan"
    ) as mock_plan_class, patch(
        "app.models.repository.Zone"
    ) as mock_zone_class:

        mock_datetime.now.return_value = FIXED_TIME

        # Ensure that when the repository uses the patched model classes (e.g., Event, EventPlan, Zone)
        # in db_session.query(ModelFromRepositoryModule), these queries are routed to the
        # mock query chains that were set up for their ActualModel counterparts.
        mock_db_session.query_route_map[mock_event_class] = (
            mock_db_session.query_chain_mocks_for_actual_types[ActualEvent]
        )
        mock_db_session.query_route_map[mock_plan_class] = (
            mock_db_session.query_chain_mocks_for_actual_types[ActualEventPlan]
        )
        mock_db_session.query_route_map[mock_zone_class] = (
            mock_db_session.query_chain_mocks_for_actual_types[ActualZone]
        )

        yield mock_datetime, mock_event_class, mock_plan_class, mock_zone_class


@pytest.fixture
def mock_func_timedelta():
    with patch("app.models.repository.func") as mock_sql_func:
        mock_sql_func.timedelta.return_value = timedelta(seconds=1)
        yield mock_sql_func


FIXED_TIME = datetime(2025, 7, 26, 10, 0, 0, tzinfo=timezone.utc)


class TestEventRepositoryUpsertEvents:
    def test_upsert_single_new_event_online(
        self,
        mock_upsert_dependencies,
        event_repository,
        mock_db_session,
        app_context,
    ):
        mock_datetime, mock_event_class, mock_plan_class, mock_zone_class = (
            mock_upsert_dependencies
        )

        # Prepare mock model instances
        mock_event_instance = MagicMock(spec=ActualEvent)
        mock_event_instance.id = uuid4()
        mock_event_instance.provider_name = "test_provider"
        mock_event_class.return_value = mock_event_instance

        mock_plan_instance = MagicMock(spec=ActualEventPlan)
        mock_plan_instance.id = uuid4()
        mock_plan_class.return_value = mock_plan_instance

        mock_zone_instance = MagicMock(spec=ActualZone)
        mock_zone_class.return_value = mock_zone_instance

        parsed_zone = create_parsed_zone(
            zone_id="z1", name="Zone A", price=25.0, capacity=50
        )
        parsed_plan = create_parsed_plan(plan_id="p1", zones=[parsed_zone])
        parsed_event_data = create_parsed_event(
            event_id="e1",
            title="New Event",
            sell_mode="online",
            event_plans=[parsed_plan],
            provider_name="test_provider",
        )

        event_repository.upsert_events(
            [parsed_event_data], provider_name_filter="test_provider"
        )

        # Assert Event creation
        mock_event_class.assert_called_once_with(
            base_event_id="e1",
            provider_name="test_provider",
            title="New Event",
            sell_mode="online",
            organizer_company_id="org1",
            first_seen_at=FIXED_TIME,
            ever_online=False,
        )
        assert mock_event_instance.ever_online is True
        assert mock_event_instance.last_seen_at == FIXED_TIME

        # Assert EventPlan creation
        mock_plan_class.assert_called_once_with(
            event_id=mock_event_instance.id,
            base_plan_id="p1",
            provider_name="test_provider",
            start_date=parsed_plan.start_date,
            end_date=parsed_plan.end_date,
            sell_from=parsed_plan.sell_from,
            sell_to=parsed_plan.sell_to,
            sold_out=parsed_plan.sold_out,
            first_seen_at=FIXED_TIME,
        )
        assert mock_plan_instance.last_seen_at == FIXED_TIME

        # Assert Zone creation
        mock_zone_class.assert_called_once_with(
            event_plan_id=mock_plan_instance.id,
            zone_id="z1",
            name="Zone A",
            price=25.0,
            capacity=50,
            is_numbered=parsed_zone.numbered,
            first_seen_at=FIXED_TIME,
        )
        assert mock_zone_instance.last_seen_at == FIXED_TIME

        # Assert DB session calls
        mock_db_session.add.assert_any_call(mock_event_instance)
        mock_db_session.add.assert_any_call(mock_plan_instance)
        mock_db_session.add.assert_any_call(mock_zone_instance)
        assert (
            mock_db_session.commit.call_count == 2
        )  # Batch commit + Stale marking commit
        mock_db_session.rollback.assert_not_called()

    def _setup_existing_db_entities_and_mocks(
        self, mock_db_session, event_details, plan_details, zone_details
    ):
        event_uuid, original_first_seen_at = (
            event_details["id"],
            event_details["first_seen_at"],
        )
        plan_uuid = plan_details["id"]

        existing_event = MagicMock(
            spec=ActualEvent,
            id=event_uuid,
            base_event_id=event_details["base_event_id"],
            provider_name=event_details["provider_name"],
            title=event_details["title"],
            sell_mode=event_details["sell_mode"],
            organizer_company_id=event_details["organizer_company_id"],
            first_seen_at=original_first_seen_at,
            last_seen_at=original_first_seen_at,
            ever_online=event_details["ever_online"],
        )

        existing_plan = MagicMock(
            spec=ActualEventPlan,
            id=plan_uuid,
            event_id=event_uuid,
            base_plan_id=plan_details["base_plan_id"],
            provider_name=plan_details["provider_name"],
            start_date=plan_details["start_date"],
            end_date=plan_details["end_date"],
            sell_from=plan_details["sell_from"],
            sell_to=plan_details["sell_to"],
            sold_out=plan_details["sold_out"],
            first_seen_at=original_first_seen_at,
            last_seen_at=original_first_seen_at,
        )

        existing_zone = MagicMock(
            spec=ActualZone,
            id=zone_details["id"],
            event_plan_id=plan_uuid,
            zone_id=zone_details["zone_id"],
            name=zone_details["name"],
            capacity=zone_details["capacity"],
            price=zone_details["price"],
            is_numbered=zone_details["is_numbered"],
            first_seen_at=original_first_seen_at,
            last_seen_at=original_first_seen_at,
        )

        query_mock_event = mock_db_session.query_chain_mocks_for_actual_types[
            ActualEvent
        ]
        query_mock_plan = mock_db_session.query_chain_mocks_for_actual_types[
            ActualEventPlan
        ]
        query_mock_zone = mock_db_session.query_chain_mocks_for_actual_types[ActualZone]

        query_mock_event.filter_by(
            base_event_id=event_details["base_event_id"],
            provider_name=event_details["provider_name"],
        ).first.return_value = existing_event

        query_mock_plan.filter_by(
            event_id=existing_event.id,
            base_plan_id=plan_details["base_plan_id"],
            provider_name=plan_details["provider_name"],
        ).first.return_value = existing_plan

        query_mock_zone.filter_by(
            event_plan_id=existing_plan.id, zone_id=zone_details["zone_id"]
        ).first.return_value = existing_zone

        return existing_event, existing_plan, existing_zone

    @patch("app.models.repository.datetime")
    def test_upsert_existing_event(
        self, mock_datetime, event_repository, mock_db_session, app_context
    ):
        mock_datetime.now.return_value = FIXED_TIME
        original_first_seen_at = FIXED_TIME - timedelta(days=1)

        event_details = {
            "id": uuid4(),
            "base_event_id": "e1",
            "provider_name": "test_provider",
            "title": "Old Event Title",
            "sell_mode": "offline",
            "organizer_company_id": "org1",
            "first_seen_at": original_first_seen_at,
            "ever_online": False,
        }
        plan_details = {
            "id": uuid4(),
            "base_plan_id": "p1",
            "provider_name": "test_provider",
            "start_date": datetime(2024, 12, 31, 10, 0, 0, tzinfo=timezone.utc),
            "end_date": datetime(2024, 12, 31, 12, 0, 0, tzinfo=timezone.utc),
            "sell_from": datetime(2023, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            "sell_to": datetime(2024, 12, 31, 9, 0, 0, tzinfo=timezone.utc),
            "sold_out": True,
        }
        zone_details = {
            "id": uuid4(),
            "zone_id": "z1",
            "name": "Old Zone Name",
            "capacity": 50,
            "price": 20.0,
            "is_numbered": True,
        }

        existing_event, existing_plan, existing_zone = (
            self._setup_existing_db_entities_and_mocks(
                mock_db_session, event_details, plan_details, zone_details
            )
        )

        # New data for update
        updated_parsed_zone = create_parsed_zone(
            zone_id="z1", name="New Zone Name", price=22.0, capacity=60
        )
        updated_parsed_plan = create_parsed_plan(
            plan_id="p1", zones=[updated_parsed_zone]
        )
        parsed_event_data = create_parsed_event(
            event_id="e1",
            title="New Event Title",
            sell_mode="online",
            event_plans=[updated_parsed_plan],
            provider_name="test_provider",
        )

        event_repository.upsert_events(
            [parsed_event_data], provider_name_filter="test_provider"
        )

        # Assert Event update
        assert existing_event.title == "New Event Title"
        assert existing_event.sell_mode == "online"
        assert existing_event.ever_online is True
        assert existing_event.first_seen_at == original_first_seen_at
        assert existing_event.last_seen_at == FIXED_TIME

        # Assert EventPlan update
        assert existing_plan.last_seen_at == FIXED_TIME
        assert existing_plan.start_date == updated_parsed_plan.start_date

        # Assert Zone update
        assert existing_zone.name == "New Zone Name"
        assert existing_zone.price == 22.0
        assert existing_zone.capacity == 60
        assert existing_zone.first_seen_at == original_first_seen_at
        assert existing_zone.last_seen_at == FIXED_TIME

        # Assert DB session calls
        mock_db_session.add.assert_not_called()
        assert (
            mock_db_session.commit.call_count == 2
        )  # Batch commit + Stale marking commit
        mock_db_session.rollback.assert_not_called()

    @patch("app.models.repository.datetime")
    @patch("app.models.repository.func")  # For timedelta
    def test_upsert_event_not_in_feed_updates_last_seen(
        self,
        mock_sql_func,
        mock_datetime,
        event_repository,
        mock_db_session,
        app_context,
    ):
        mock_datetime.now.return_value = FIXED_TIME
        mock_sql_func.timedelta.return_value = timedelta(seconds=1)

        provider_name = "test_provider"

        # For this test, since events_data is empty, _upsert_event and its children are not called.
        event_repository.upsert_events([], provider_name_filter=provider_name)

        # Assert that an update was attempted on Event table for the given provider
        # to mark events not seen in the (empty) feed.
        # The Event class used by repository for .last_seen_at is ActualEvent
        mock_db_session.query(ActualEvent).filter(
            ActualEvent.provider_name == provider_name,
            ActualEvent.base_event_id.notin_([]),
        ).update.assert_called_once_with(
            {ActualEvent.last_seen_at: FIXED_TIME - timedelta(seconds=1)},
            synchronize_session=False,
        )

        mock_db_session.commit.assert_called()
        mock_db_session.rollback.assert_not_called()

    def test_upsert_plan_marks_old_zones(
        self,
        mock_upsert_dependencies,
        event_repository,
        mock_db_session,
        app_context,
    ):
        _, _, _, mock_zone_class = mock_upsert_dependencies

        provider_name = "test_provider"
        event_id_uuid = uuid4()
        plan_id_uuid = uuid4()

        existing_event = MagicMock(
            spec=ActualEvent, id=event_id_uuid, provider_name=provider_name
        )
        existing_plan = MagicMock(
            spec=ActualEventPlan,
            id=plan_id_uuid,
            event_id=event_id_uuid,
            provider_name=provider_name,
        )

        mock_db_session.query(ActualEvent).filter_by(
            base_event_id="e1", provider_name=provider_name
        ).first.return_value = existing_event
        mock_db_session.query(ActualEventPlan).filter_by(
            event_id=existing_event.id, base_plan_id="p1", provider_name=provider_name
        ).first.return_value = existing_plan

        # No zones in the new data for the plan
        parsed_plan_data = create_parsed_plan(plan_id="p1", zones=[])
        parsed_event_data = create_parsed_event(
            event_id="e1", event_plans=[parsed_plan_data], provider_name=provider_name
        )

        # Call _upsert_event directly to test its internal plan/zone logic isolatedly
        # This requires mocking the event model directly
        with patch.object(
            event_repository, "_upsert_zone"
        ) as _unused_mock_upsert_zone:  # prevent deeper calls
            query_mock_zone = mock_db_session.query_chain_mocks_for_actual_types[
                ActualZone
            ]
            event_repository._upsert_event(parsed_event_data, FIXED_TIME)

        # Assert that an update was attempted on Zone table for the given plan
        # to mark zones not seen in the (empty) zones list for that plan.
        # The repository code uses mock_zone_class.last_seen_at for the update key after patching.
        query_mock_zone.filter(
            ActualZone.event_plan_id == existing_plan.id,
            ActualZone.zone_id.notin_([]),  # seen_zone_ids_in_provider_feed is empty
        ).update.assert_called_once_with(
            {mock_zone_class.last_seen_at: FIXED_TIME - timedelta(seconds=1)},
            synchronize_session=False,
        )

    def test_upsert_event_marks_old_plans(
        self,
        mock_upsert_dependencies,
        event_repository,
        mock_db_session,
        app_context,
    ):
        _, _, mock_plan_class, _ = mock_upsert_dependencies

        provider_name = "test_provider"
        event_id_uuid = uuid4()

        existing_event = MagicMock(
            spec=ActualEvent, id=event_id_uuid, provider_name=provider_name
        )
        mock_db_session.query(ActualEvent).filter_by(
            base_event_id="e1", provider_name=provider_name
        ).first.return_value = existing_event

        parsed_event_data = create_parsed_event(
            event_id="e1", event_plans=[], provider_name=provider_name
        )

        query_mock_event_plan = mock_db_session.query_chain_mocks_for_actual_types[
            ActualEventPlan
        ]
        event_repository._upsert_event(parsed_event_data, FIXED_TIME)

        # Assert that an update was attempted on EventPlan table for the given event
        # to mark plans not seen in the (empty) plans list for that event.
        # The repository code uses mock_plan_class.last_seen_at for the update key after patching.
        query_mock_event_plan.filter(
            ActualEventPlan.event_id == existing_event.id,
            ActualEventPlan.provider_name == provider_name,
            ActualEventPlan.base_plan_id.notin_([]),
        ).update.assert_called_once_with(
            {mock_plan_class.last_seen_at: FIXED_TIME - timedelta(seconds=1)},
            synchronize_session=False,
        )

    def test_upsert_events_sqlalchemy_error_on_commit(
        self, event_repository, mock_db_session, app_context
    ):
        parsed_event_data = create_parsed_event(
            event_id="e1", provider_name="test_provider"
        )

        mock_db_session.commit.side_effect = SQLAlchemyError("DB commit failed")

        mock_db_session.query.return_value.filter_by.return_value.first.return_value = (
            None
        )

        with pytest.raises(SQLAlchemyError, match="DB commit failed"):
            event_repository.upsert_events(
                [parsed_event_data], provider_name_filter="test_provider"
            )

        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_called_once()

    def test_upsert_events_skips_event_with_missing_provider_name_in_parsed_data(
        self,
        mock_upsert_dependencies,
        event_repository,
        mock_db_session,
        app_context,
    ):
        _, mock_event_class, mock_plan_class, mock_zone_class = mock_upsert_dependencies

        valid_parsed_event = create_parsed_event(
            event_id="e_valid", provider_name="test_provider", title="Valid Event"
        )

        # Create mock for event with missing provider_name
        invalid_parsed_event_provider = MagicMock(spec=ParsedEvent)
        invalid_parsed_event_provider.id = "e_invalid_prov"
        invalid_parsed_event_provider.provider_name = None
        invalid_parsed_event_provider.title = "Invalid Event ProviderName"
        invalid_parsed_event_provider.sell_mode = "online"
        invalid_parsed_event_provider.organizer_company_id = "org1"
        # Ensure event_plans is a list to avoid errors if the event isn't skipped early enough
        # It should be skipped before event_plans is deeply accessed.
        invalid_parsed_event_provider.event_plans = []

        # Create mock for event with missing id
        invalid_parsed_event_id = MagicMock(spec=ParsedEvent)
        invalid_parsed_event_id.id = None
        invalid_parsed_event_id.provider_name = "test_provider"
        invalid_parsed_event_id.title = "Invalid Event ID"
        invalid_parsed_event_id.sell_mode = "online"
        invalid_parsed_event_id.organizer_company_id = "org1"
        invalid_parsed_event_id.event_plans = []

        # Mock query.filter_by.first to return None for new items
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = (
            None
        )
        # For the valid event, mock its creation to simplify tracking
        mock_event_instance = MagicMock(spec=ActualEvent)
        mock_event_instance.id = uuid4()
        mock_event_instance.provider_name = valid_parsed_event.provider_name

        def mock_event_constructor_side_effect(*args, **kwargs):
            if kwargs.get("base_event_id") == "e_valid":
                return mock_event_instance
            m = MagicMock(spec=ActualEvent)
            m.id = uuid4()
            m.provider_name = kwargs.get("provider_name")
            return m

        mock_event_class.side_effect = mock_event_constructor_side_effect
        mock_plan_class.return_value = MagicMock(spec=ActualEventPlan, id=uuid4())
        mock_zone_class.return_value = MagicMock(spec=ActualZone, id=uuid4())

        event_repository.upsert_events(
            [
                valid_parsed_event,
                invalid_parsed_event_provider,
                invalid_parsed_event_id,
            ],
            provider_name_filter="test_provider",
        )

        # Assert that add was called for the valid event's objects
        # This assumes _upsert_event for the valid event proceeds to add event, plan, zone
        # At least Event, EventPlan, Zone for the valid_parsed_event
        assert mock_db_session.add.call_count >= 3

        assert (
            mock_db_session.commit.call_count == 2
        )  # Batch commit + Stale marking commit
        mock_db_session.rollback.assert_not_called()  # No rollback if only skipping

    def test_upsert_event_value_error_in_upsert_event_internal(
        self, mock_upsert_dependencies, event_repository, mock_db_session, app_context
    ):
        parsed_event = create_parsed_event(event_id="e1", provider_name="test_provider")

        # Make the internal _upsert_event raise a ValueError (e.g. if provider_name was None on ParsedEvent, which it checks).
        with patch.object(
            event_repository,
            "_upsert_event",
            side_effect=ValueError("Internal validation failed"),
        ) as mock_internal_upsert:
            event_repository.upsert_events(
                [parsed_event], provider_name_filter="test_provider"
            )

        mock_internal_upsert.assert_called_once_with(parsed_event, FIXED_TIME)
        assert (
            mock_db_session.commit.call_count == 2
        )  # Batch commit + Stale marking commit
        mock_db_session.rollback.assert_not_called()

    @patch("app.models.repository.EVENT_UPSERT_BATCH_SIZE", 2)
    def test_upsert_events_processes_in_batches(
        self, mock_upsert_dependencies, event_repository, mock_db_session, app_context
    ):
        # Create 3 events to test batching (batch size is 2)
        parsed_event1 = create_parsed_event(event_id="e1", provider_name="p1")
        parsed_event2 = create_parsed_event(event_id="e2", provider_name="p1")
        parsed_event3 = create_parsed_event(event_id="e3", provider_name="p1")
        events_data = [parsed_event1, parsed_event2, parsed_event3]

        with patch.object(event_repository, "_upsert_event") as mock_internal_upsert:
            event_repository.upsert_events(events_data, provider_name_filter="p1")

        # Assert _upsert_event was called for each event
        assert mock_internal_upsert.call_count == 3
        mock_internal_upsert.assert_any_call(parsed_event1, FIXED_TIME)
        mock_internal_upsert.assert_any_call(parsed_event2, FIXED_TIME)
        mock_internal_upsert.assert_any_call(parsed_event3, FIXED_TIME)

        # Assert commit was called twice (once for each batch)
        # First batch (e1, e2), Second batch (e3)
        # Plus one more commit for stale marking if provider_name_filter is active
        assert mock_db_session.commit.call_count == 3  # 2 for batches + 1 for stale
        mock_db_session.rollback.assert_not_called()

    def test_upsert_event_handles_invalid_sell_mode(
        self,
        mock_upsert_dependencies,
        event_repository,
        mock_db_session,
        app_context,
    ):
        _, mock_event_class, _, _ = mock_upsert_dependencies
        parsed_event_data = create_parsed_event(
            event_id="e_invalid_sell",
            sell_mode="non_existent_mode",  # Invalid sell_mode
            provider_name="test_provider",
        )

        # Simulate new event
        mock_db_session.query(ActualEvent).filter_by(
            base_event_id="e_invalid_sell", provider_name="test_provider"
        ).first.return_value = None

        # Mock the event instance that would be created
        created_event_instance = MagicMock(spec=ActualEvent)
        created_event_instance.id = uuid4()
        created_event_instance.ever_online = False
        mock_event_class.return_value = created_event_instance

        event_repository.upsert_events(
            [parsed_event_data], provider_name_filter="test_provider"
        )

        # Assert Event creation with sell_mode being None (or not set to invalid value)
        mock_event_class.assert_called_once_with(
            base_event_id="e_invalid_sell",
            provider_name="test_provider",
            title=parsed_event_data.title,
            sell_mode=None,  # Due to invalid input
            organizer_company_id=parsed_event_data.organizer_company_id,
            first_seen_at=FIXED_TIME,
            ever_online=False,
        )
        assert created_event_instance.ever_online is False
        assert created_event_instance.last_seen_at == FIXED_TIME
        mock_db_session.add.assert_any_call(created_event_instance)
        assert (
            mock_db_session.commit.call_count == 2
        )  # Batch commit + Stale marking commit

    def test_upsert_event_handles_valid_sell_mode(
        self,
        mock_upsert_dependencies,
        event_repository,
        mock_db_session,
        app_context,
    ):
        _, mock_event_class, _, _ = mock_upsert_dependencies
        parsed_event_data = create_parsed_event(
            event_id="e_offline_sell",
            sell_mode="offline",
            provider_name="test_provider",
        )

        mock_db_session.query(ActualEvent).filter_by(
            base_event_id="e_offline_sell", provider_name="test_provider"
        ).first.return_value = None
        created_event_instance = MagicMock(spec=ActualEvent)
        created_event_instance.id = uuid4()
        created_event_instance.ever_online = False
        mock_event_class.return_value = created_event_instance

        event_repository.upsert_events(
            [parsed_event_data], provider_name_filter="test_provider"
        )

        mock_event_class.assert_called_once_with(
            base_event_id="e_offline_sell",
            provider_name="test_provider",
            title=parsed_event_data.title,
            sell_mode="offline",
            organizer_company_id=parsed_event_data.organizer_company_id,
            first_seen_at=FIXED_TIME,
            ever_online=False,
        )
        assert created_event_instance.ever_online is False
        assert created_event_instance.last_seen_at == FIXED_TIME
        mock_db_session.add.assert_any_call(created_event_instance)
        assert (
            mock_db_session.commit.call_count == 2
        )  # Batch commit + Stale marking commit

    def test_upsert_events_skips_mismatched_provider_filter(
        self,
        mock_upsert_dependencies,
        event_repository,
        mock_db_session,
        app_context,
    ):
        _, mock_event_class, mock_plan_class, mock_zone_class = mock_upsert_dependencies
        target_provider = "target_provider"
        other_provider = "other_provider"

        event_matching_filter = create_parsed_event(
            event_id="e_match", provider_name=target_provider
        )
        event_mismatch_filter = create_parsed_event(
            event_id="e_mismatch", provider_name=other_provider
        )

        # Mock for event with no provider, to be skipped by internal check
        event_no_provider = MagicMock(spec=ParsedEvent)
        event_no_provider.id = "e_no_prov"
        event_no_provider.provider_name = None
        event_no_provider.title = "Event with No Provider"
        event_no_provider.sell_mode = "online"
        event_no_provider.organizer_company_id = "org1"
        event_no_provider.event_plans = []

        # Mock for event with no ID, to be skipped by internal check
        event_no_id = MagicMock(spec=ParsedEvent)
        event_no_id.id = None
        event_no_id.provider_name = target_provider
        event_no_id.title = "Event with No ID"
        event_no_id.sell_mode = "online"
        event_no_id.organizer_company_id = "org1"
        event_no_id.event_plans = []

        events_data = [
            event_matching_filter,
            event_mismatch_filter,
            event_no_provider,
            event_no_id,
        ]

        # Simulate new event for the matching one
        query_mock_event = mock_db_session.query_chain_mocks_for_actual_types[
            ActualEvent
        ]
        query_mock_event.filter_by(
            base_event_id="e_match", provider_name=target_provider
        ).first.return_value = None

        # Mock the event instance that would be created for the matching event
        created_event_instance = MagicMock(spec=ActualEvent)
        created_event_instance.id = uuid4()
        created_event_instance.provider_name = target_provider
        created_event_instance.base_event_id = "e_match"

        # We need to control the return value of Event() constructor
        def event_constructor_side_effect(*args, **kwargs):
            if kwargs.get("base_event_id") == "e_match":
                # For the event that should be processed, return our specific mock
                return created_event_instance
            generic_mock = MagicMock(spec=ActualEvent)
            generic_mock.id = uuid4()
            generic_mock.provider_name = kwargs.get("provider_name")
            return generic_mock

        mock_event_class.side_effect = event_constructor_side_effect
        mock_plan_class.return_value = MagicMock(spec=ActualEventPlan, id=uuid4())
        mock_zone_class.return_value = MagicMock(spec=ActualZone, id=uuid4())

        with patch.object(
            event_repository, "_upsert_event", wraps=event_repository._upsert_event
        ) as spy_upsert_event:
            event_repository.upsert_events(
                events_data, provider_name_filter=target_provider
            )

        spy_upsert_event.assert_called_once_with(event_matching_filter, FIXED_TIME)

        # Check calls to the constructor of Event model
        call_kwargs_list = [kwargs for _, kwargs in mock_event_class.call_args_list]
        assert (
            len(
                [
                    ckw
                    for ckw in call_kwargs_list
                    if ckw.get("base_event_id") == "e_match"
                ]
            )
            == 1
        )

        # Verify that the database add operations are only for the matching event's objects
        # At a minimum, the Event, one EventPlan, and one Zone for 'e_match'
        assert mock_db_session.add.call_count >= 3

        # Check that the added event was indeed the one for 'e_match'
        added_event_is_correct = False
        for call in mock_db_session.add.call_args_list:
            added_item = call[0][0]
            if (
                isinstance(added_item, MagicMock)
                and hasattr(added_item, "provider_name")
                and added_item.provider_name == target_provider
            ):
                if (
                    hasattr(added_item, "base_event_id")
                    and added_item.base_event_id == "e_match"
                ):
                    added_event_is_correct = True
                    break
        assert added_event_is_correct

        # Stale marking commit + batch commit for the one processed event
        assert mock_db_session.commit.call_count == 2
        mock_db_session.rollback.assert_not_called()

        # This assertion is on the specific query_mock_event's filter().update()
        query_chain_for_actual_event = (
            mock_db_session.query_chain_mocks_for_actual_types[ActualEvent]
        )

        # The Event object used for attribute access in the repository's filter/update
        # for stale marking is app.models.repository.Event, which is patched to mock_event_class.
        event_attr_source_for_stale_logic = mock_event_class

        stale_time_expected = FIXED_TIME - timedelta(seconds=1)

        # Check the filter and update call for stale marking
        # 1. Assert that filter was called with the correct arguments
        query_chain_for_actual_event.filter.assert_called_once()

        # 2. Assert that update was called on the result of filter, with correct arguments
        query_chain_for_actual_event.filter.return_value.update.assert_called_once_with(
            {event_attr_source_for_stale_logic.last_seen_at: stale_time_expected},
            synchronize_session=False,
        )


@pytest.fixture
def mock_get_events_query_chain(mock_db_session):
    query_mock_event_chain = mock_db_session.query_chain_mocks_for_actual_types[
        ActualEvent
    ]

    options_mock = query_mock_event_chain.options.return_value
    join_mock = options_mock.join.return_value
    filter_mock = join_mock.filter.return_value
    distinct_mock = filter_mock.distinct.return_value

    yield query_mock_event_chain, options_mock, join_mock, filter_mock, distinct_mock


class TestEventRepositoryGetEventsByDate:
    def test_get_events_by_date_returns_matching_events(
        self, event_repository, mock_get_events_query_chain, app_context
    ):
        query_mock_event_chain, options_mock, join_mock, filter_mock, distinct_mock = (
            mock_get_events_query_chain
        )
        starts_at = datetime(2025, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
        ends_at = datetime(2025, 1, 20, 0, 0, 0, tzinfo=timezone.utc)

        mock_zone1 = MagicMock(spec=ActualZone)
        mock_plan1 = MagicMock(spec=ActualEventPlan)
        mock_plan1.start_date = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        mock_plan1.zones = [mock_zone1]

        mock_event1 = MagicMock(spec=ActualEvent)
        mock_event1.id = uuid4()
        mock_event1.ever_online = True
        mock_event1.event_plans = [mock_plan1]

        # Configure the mock session query result
        distinct_mock.all.return_value = [mock_event1]

        result = event_repository.get_events_by_date(starts_at, ends_at)

        assert result == [mock_event1]

        # Assert the call chain on query_mock_event
        query_mock_event_chain.options.assert_called_once()
        options_mock.join.assert_called_once()
        join_call_args = options_mock.join.call_args
        assert join_call_args[0][0] == ActualEventPlan
        assert str(join_call_args[0][1]) == str(
            ActualEvent.id == ActualEventPlan.event_id
        )

        join_mock.filter.assert_called_once()
        filter_mock.distinct.assert_called_once()
        distinct_mock.all.assert_called_once()

        # Check filter arguments
        filter_conditions_tuple = join_mock.filter.call_args[0]
        assert any(
            str(ActualEvent.ever_online.is_(True)) == str(arg)
            for arg in filter_conditions_tuple
        )
        assert any(
            str(ActualEventPlan.start_date >= starts_at) == str(arg)
            for arg in filter_conditions_tuple
        )
        assert any(
            str(ActualEventPlan.start_date <= ends_at) == str(arg)
            for arg in filter_conditions_tuple
        )

    def test_get_events_by_date_returns_empty_if_no_match(
        self, event_repository, mock_get_events_query_chain, app_context
    ):
        _, _, join_mock, _, distinct_mock = mock_get_events_query_chain
        starts_at = datetime(2025, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
        ends_at = datetime(2025, 1, 20, 0, 0, 0, tzinfo=timezone.utc)

        # Configure mock_db_session...all() to return an empty list
        distinct_mock.all.return_value = []

        result = event_repository.get_events_by_date(starts_at, ends_at)

        assert result == []

        # Check that the filter was called and included Event.ever_online == True
        filter_conditions_tuple = join_mock.filter.call_args[0]
        assert any(
            str(ActualEvent.ever_online.is_(True)) == str(arg)
            for arg in filter_conditions_tuple
        )
        distinct_mock.all.assert_called_once()

    def test_get_events_by_date_filters_not_ever_online(
        self, event_repository, mock_get_events_query_chain, app_context
    ):
        _, _, join_mock, _, distinct_mock = mock_get_events_query_chain
        starts_at = datetime(2025, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
        ends_at = datetime(2025, 1, 20, 0, 0, 0, tzinfo=timezone.utc)

        distinct_mock.all.return_value = []

        result = event_repository.get_events_by_date(starts_at, ends_at)
        assert result == []

        # Check that the filter was called and included Event.ever_online == True
        filter_conditions_tuple = join_mock.filter.call_args[0]
        assert any(
            str(ActualEvent.ever_online.is_(True)) == str(arg)
            for arg in filter_conditions_tuple
        )
        distinct_mock.all.assert_called_once()

    def test_get_events_by_date_filters_plan_date_range(
        self, event_repository, mock_get_events_query_chain, app_context
    ):
        _, _, join_mock, _, distinct_mock = mock_get_events_query_chain
        starts_at = datetime(2025, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
        ends_at = datetime(2025, 1, 20, 0, 0, 0, tzinfo=timezone.utc)

        distinct_mock.all.return_value = []

        result = event_repository.get_events_by_date(starts_at, ends_at)
        assert result == []

        # Check that the filter included the date range conditions
        filter_conditions_tuple = join_mock.filter.call_args[0]
        assert any(
            str(ActualEventPlan.start_date >= starts_at) == str(arg)
            for arg in filter_conditions_tuple
        )
        assert any(
            str(ActualEventPlan.start_date <= ends_at) == str(arg)
            for arg in filter_conditions_tuple
        )
        distinct_mock.all.assert_called_once()
