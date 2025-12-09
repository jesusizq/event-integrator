import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from app import create_app, db as _db
from app.tasks.sync import sync_provider_events
from app.models.event import Event
from app.models.repository import EventRepository
from tests.fixtures.sample_provider_responses import (
    SAMPLE_XML_RESPONSE_1,
    EMPTY_XML_RESPONSE,
    SAMPLE_XML_RESPONSE_2_SUBSET,
)
from datetime import datetime, timezone, timedelta
from app.services.provider_client import ProviderClient

# Default provider name, matches the one in config.py
DEFAULT_PROVIDER_NAME = "primary_provider"


@pytest.fixture(scope="session")
def app():
    """Session-wide test `Flask` application."""
    _app = create_app(config_name="testing")
    # Push an app context here to ensure current_app in tests refers to this app
    # This context will be active for the duration of the test session unless popped.
    # For function-scoped fixtures or tests, app_context is typically managed per-function.
    # However, since current_app is used to get config for the mock setup,
    # ensuring a context is active when that happens is important.
    # The `with app.app_context()` in each test function also serves this for the test body.
    ctx = _app.app_context()
    ctx.push()
    yield _app
    ctx.pop()


@pytest.fixture(scope="session")
def db(app: Flask):
    """Session-wide test database."""
    with app.app_context():
        _db.create_all()

    yield _db

    with app.app_context():
        _db.drop_all()


@pytest.fixture(scope="function")
def session(app: Flask, db: _db):
    """Creates a new database session for a test, ensuring rollback via nested transaction."""
    with app.app_context():
        # The default db.session is a scoped_session managed by Flask-SQLAlchemy.
        # We begin a nested transaction (SAVEPOINT) on this session.
        nested_transaction = _db.session.begin_nested()

        yield _db.session

        # Rollback the nested transaction after the test.
        nested_transaction.rollback()


@pytest.fixture(scope="function")
def mocked_task_app_context(app: Flask) -> MagicMock:
    """
    Provides a MagicMock instance pre-configured to simulate `current_app`
    for Celery tasks. Its config is a copy of the main test app's config
    and can be modified by the test function before patching.
    The `extensions` attribute is also copied.
    """
    mock_app = MagicMock(spec=Flask)

    if hasattr(app, "extensions"):
        mock_app.extensions = app.extensions
    else:
        mock_app.extensions = {}

    # Provide a base config copied from the main test app.
    # Tests can then modify this instance's config as needed.
    mock_app.config = app.config.copy()

    yield mock_app


def test_sync_successful_first_run(
    app: Flask, session, mocked_task_app_context: MagicMock
):
    """
    Test the sync_provider_events task with a successful first run.
    Ensures events, plans, and zones are created correctly.
    """
    with app.app_context():
        expected_provider_configs = app.config.get("PROVIDERS")
        assert (
            expected_provider_configs and len(expected_provider_configs) > 0
        ), "Providers must be configured in test config"
        provider_to_assert = expected_provider_configs[0]

        with (
            patch("app.tasks.sync.logger.info") as mock_logger_info,
            patch("app.tasks.sync.ProviderClient") as MockProviderClientClass,
            patch(
                "app.tasks.sync.current_app",
                new=mocked_task_app_context,
            ),
        ):
            mock_provider_instance = MockProviderClientClass.return_value
            mock_provider_instance.get_events_xml.return_value = SAMPLE_XML_RESPONSE_1

            sync_provider_events()

            mock_logger_info.assert_any_call(
                "Starting provider events synchronization task for all providers."
            )
            MockProviderClientClass.assert_called_once_with(provider_to_assert)
            mock_provider_instance.get_events_xml.assert_called_once()

            repo = EventRepository(session)

            # Verify Event 1: Camela en concierto (base_event_id="291")
            event1 = (
                repo.db_session.query(Event)
                .filter_by(base_event_id="291", provider_name=DEFAULT_PROVIDER_NAME)
                .first()
            )
            assert event1 is not None
            assert event1.title == "Camela en concierto"
            assert event1.sell_mode == "online"
            assert event1.ever_online is True
            assert len(event1.event_plans) == 1

            plan1_event1 = event1.event_plans[0]
            assert plan1_event1.base_plan_id == "291"
            assert plan1_event1.provider_name == DEFAULT_PROVIDER_NAME
            assert plan1_event1.start_date == datetime(
                2021, 6, 30, 21, 0, 0, tzinfo=timezone.utc
            )
            assert len(plan1_event1.zones) == 3

            # Check one zone for details
            zone1_plan1_event1 = next(
                z for z in plan1_event1.zones if z.zone_id == "40"
            )
            assert zone1_plan1_event1.name == "Platea"
            assert zone1_plan1_event1.price == 20.00
            assert zone1_plan1_event1.capacity == 243
            assert zone1_plan1_event1.is_numbered is True

            # Verify Event 2: Pantomima Full (base_event_id="322")
            event2 = (
                repo.db_session.query(Event)
                .filter_by(base_event_id="322", provider_name=DEFAULT_PROVIDER_NAME)
                .first()
            )
            assert event2 is not None
            assert event2.title == "Pantomima Full"
            assert event2.organizer_company_id == "2"
            assert event2.sell_mode == "online"
            assert event2.ever_online is True
            assert len(event2.event_plans) == 2

            plan1_event2 = next(
                p for p in event2.event_plans if p.base_plan_id == "1642"
            )
            assert plan1_event2.start_date == datetime(
                2021, 2, 10, 20, 0, 0, tzinfo=timezone.utc
            )
            assert len(plan1_event2.zones) == 1
            zone1_plan1_event2 = plan1_event2.zones[0]
            assert zone1_plan1_event2.zone_id == "311"
            assert zone1_plan1_event2.price == 55.00

            plan2_event2 = next(
                p for p in event2.event_plans if p.base_plan_id == "1643"
            )
            assert plan2_event2.start_date == datetime(
                2021, 2, 11, 20, 0, 0, tzinfo=timezone.utc
            )
            assert len(plan2_event2.zones) == 1
            zone1_plan2_event2 = plan2_event2.zones[0]
            assert zone1_plan2_event2.zone_id == "311"
            assert zone1_plan2_event2.price == 55.00

            # Verify Event 3: Los Morancos (base_event_id="1591")
            event3 = (
                repo.db_session.query(Event)
                .filter_by(base_event_id="1591", provider_name=DEFAULT_PROVIDER_NAME)
                .first()
            )
            assert event3 is not None, "Event 1591 not found"
            assert event3.title == "Los Morancos"
            assert event3.sell_mode == "online"
            assert event3.ever_online is True
            assert len(event3.event_plans) == 1
            assert len(event3.event_plans[0].zones) == 1


def test_sync_provider_error(app: Flask, session, mocked_task_app_context: MagicMock):
    """
    Test the sync_provider_events task when the provider client returns None (simulating an error).
    Ensures the task handles it gracefully and no data is incorrectly processed.
    """
    with app.app_context():
        initial_event_count = session.query(Event).count()

        assert app.config.get("PROVIDERS"), "PROVIDERS must be set in test config"
        provider_config_to_check = app.config["PROVIDERS"][0]

        with (
            patch("app.tasks.sync.logger.info") as mock_logger_info,
            patch("app.tasks.sync.logger.warning") as mock_logger_warning,
            patch("app.tasks.sync.logger.error") as mock_logger_error,
            patch("app.tasks.sync.ProviderClient") as MockProviderClientClass,
            patch("app.tasks.sync.current_app", new=mocked_task_app_context),
        ):
            mock_instance = MockProviderClientClass.return_value
            mock_instance.get_events_xml.return_value = None  # Simulate provider error

            sync_provider_events()

            mock_logger_info.assert_any_call(
                "Starting provider events synchronization task for all providers."
            )
            MockProviderClientClass.assert_called_once_with(provider_config_to_check)
            mock_instance.get_events_xml.assert_called_once()
            mock_logger_warning.assert_any_call(
                f"No XML data received from provider: {provider_config_to_check['name']}. Skipping this provider."
            )
            mock_logger_error.assert_not_called()

        assert session.query(Event).count() == initial_event_count


def test_sync_empty_response(app: Flask, session, mocked_task_app_context: MagicMock):
    """
    Test the sync_provider_events task with an empty XML response from the provider.
    Ensures existing events (if any) are marked as stale and no new events are added.
    """
    with app.app_context():
        repo = EventRepository(session)
        current_time = datetime.now(timezone.utc)
        stale_event_base_id = "999_empty_resp"

        existing_event = Event(
            base_event_id=stale_event_base_id,
            provider_name=DEFAULT_PROVIDER_NAME,
            title="Event to be Stale by Empty Resp",
            sell_mode="online",
            ever_online=True,
            first_seen_at=current_time - timedelta(days=1),
            last_seen_at=current_time - timedelta(days=1),
        )
        session.add(existing_event)
        session.commit()
        initial_event_count = session.query(Event).count()

        assert mocked_task_app_context.config.get(
            "PROVIDERS"
        ), "PROVIDERS must be in mocked app config"
        provider_config_to_check = mocked_task_app_context.config["PROVIDERS"][0]
        assert (
            provider_config_to_check["name"] == DEFAULT_PROVIDER_NAME
        ), "Test expects to run against the DEFAULT_PROVIDER_NAME for stale marking via empty response."

        with (
            patch("app.tasks.sync.logger.info") as mock_logger_info,
            patch("app.tasks.sync.ProviderClient") as MockProviderClientClass,
            patch("app.tasks.sync.current_app", new=mocked_task_app_context),
        ):
            mock_instance = MockProviderClientClass.return_value
            mock_instance.get_events_xml.return_value = EMPTY_XML_RESPONSE

            sync_provider_events()

            mock_logger_info.assert_any_call(
                "Starting provider events synchronization task for all providers."
            )
            MockProviderClientClass.assert_called_once_with(provider_config_to_check)
            mock_instance.get_events_xml.assert_called_once()

        assert session.query(Event).count() == initial_event_count
        stale_event_check = (
            session.query(Event)
            .filter_by(
                base_event_id=stale_event_base_id, provider_name=DEFAULT_PROVIDER_NAME
            )
            .first()
        )
        assert stale_event_check is not None
        assert stale_event_check.last_seen_at < current_time


def test_sync_stale_data_handling(
    app: Flask, session, mocked_task_app_context: MagicMock
):
    """
    Tests that events no longer in the feed are marked as stale (last_seen_at updated),
    and existing events are updated if their data changes.
    """
    with app.app_context():
        repo = EventRepository(session)
        provider_config_to_use = app.config["PROVIDERS"][0]
        assert (
            provider_config_to_use["name"] == DEFAULT_PROVIDER_NAME
        ), "Test expects default provider for stale handling"

        # --- First Sync: Populate with initial data ---
        # Use a fresh mock app context for the first sync, configured for default providers
        # The `mocked_task_app_context` fixture provides a fresh copy of app.config
        with (
            patch("app.tasks.sync.logger.info"),
            patch("app.tasks.sync.ProviderClient") as MockProviderClientClass_Sync1,
            patch("app.tasks.sync.current_app", new=mocked_task_app_context),
        ):

            mock_instance_sync1 = MockProviderClientClass_Sync1.return_value
            mock_instance_sync1.get_events_xml.return_value = SAMPLE_XML_RESPONSE_1
            sync_provider_events()
            MockProviderClientClass_Sync1.assert_called_once_with(
                provider_config_to_use
            )

        event_pantomima_after_sync1 = (
            repo.db_session.query(Event)
            .filter_by(base_event_id="322", provider_name=DEFAULT_PROVIDER_NAME)
            .first()
        )
        assert event_pantomima_after_sync1 is not None
        last_seen_pantomima_sync1 = event_pantomima_after_sync1.last_seen_at

        # --- Second Sync: Subset of data ---
        simulated_second_sync_time = datetime.now(timezone.utc) + timedelta(minutes=5)

        # For the second sync, we use the SAME mocked_task_app_context instance.
        # Its config still points to the default PROVIDERS list.
        with (
            patch("app.tasks.sync.logger.info"),
            patch("app.tasks.sync.ProviderClient") as MockProviderClientClass_Sync2,
            patch("app.tasks.sync.current_app", new=mocked_task_app_context),
            patch("app.models.repository.datetime") as mock_repo_datetime_module,
        ):

            mock_instance_sync2 = MockProviderClientClass_Sync2.return_value
            mock_instance_sync2.get_events_xml.return_value = (
                SAMPLE_XML_RESPONSE_2_SUBSET
            )
            mock_repo_datetime_module.now.return_value = simulated_second_sync_time
            mock_repo_datetime_module.side_effect = lambda *args, **kwargs: (
                datetime(*args, **kwargs)
                if args or kwargs
                else simulated_second_sync_time
            )
            sync_provider_events()
            MockProviderClientClass_Sync2.assert_called_once_with(
                provider_config_to_use
            )

        # Assertions for stale and updated data...
        event_camela_after_sync2 = (
            repo.db_session.query(Event)
            .filter_by(base_event_id="291", provider_name=DEFAULT_PROVIDER_NAME)
            .first()
        )
        assert event_camela_after_sync2 is not None
        assert event_camela_after_sync2.last_seen_at == simulated_second_sync_time

        event_pantomima_after_sync2 = (
            repo.db_session.query(Event)
            .filter_by(base_event_id="322", provider_name=DEFAULT_PROVIDER_NAME)
            .first()
        )
        assert event_pantomima_after_sync2 is not None
        expected_stale_time_pantomima = simulated_second_sync_time - timedelta(
            seconds=1
        )
        assert event_pantomima_after_sync2.last_seen_at == expected_stale_time_pantomima
        assert event_pantomima_after_sync2.last_seen_at != last_seen_pantomima_sync1


def test_sync_multiple_providers(
    app: Flask, session, mocked_task_app_context: MagicMock
):
    """
    Test the sync_provider_events task with multiple configured providers.
    Ensures events from each provider are fetched and stored correctly with their provider_name.
    """
    with app.app_context():
        provider1_name = "provider_one_multi"
        provider2_name = "provider_two_multi"
        mock_provider_configs = [
            {
                "name": provider1_name,
                "url": "http://provider1-multi.com/api",
                "timeout": 10,
            },
            {
                "name": provider2_name,
                "url": "http://provider2-multi.com/api",
                "timeout": 10,
            },
        ]
        xml_provider1 = f"""<planList version=\"1.0\">
    <output>
        <base_plan base_plan_id=\"multi_291\" title=\"Event Alpha by {provider1_name}\" sell_mode=\"online\" organizer_company_id=\"P1_Org1\">
            <plan plan_id=\"{provider1_name}_plan_for_multi_291\" plan_start_date=\"2021-06-30T21:00:00Z\" plan_end_date=\"2021-06-30T23:00:00Z\" sell_from=\"2021-01-01T00:00:00Z\" sell_to=\"2021-06-30T20:00:00Z\" sold_out=\"false\">
                <zone zone_id=\"z40\" name=\"Zone X\" price=\"25.00\" capacity=\"100\" numbered=\"true\"/>
            </plan>
        </base_plan>
    </output>
</planList>"""
        xml_provider2 = f"""<planList version=\"1.0\">
    <output>
        <base_plan base_plan_id=\"multi_322\" title=\"Event Beta by {provider2_name}\" sell_mode=\"online\" organizer_company_id=\"P2_Org1\">
            <plan plan_id=\"{provider2_name}_plan_for_multi_322\" plan_start_date=\"2021-02-10T20:00:00Z\" plan_end_date=\"2021-02-10T22:00:00Z\" sell_from=\"2021-01-01T00:00:00Z\" sell_to=\"2021-02-10T19:00:00Z\" sold_out=\"false\">
                <zone zone_id=\"z311\" name=\"Zone Y\" price=\"50.00\" capacity=\"50\" numbered=\"false\"/>
            </plan>
        </base_plan>
    </output>
</planList>"""

        # Override the config on the mocked_task_app_context for this specific test
        mocked_task_app_context.config = {"PROVIDERS": mock_provider_configs}

        def mock_provider_client_class_side_effect(provider_config_arg):
            mock_instance = MagicMock(spec=ProviderClient)
            mock_instance.provider_config_for_this_instance = provider_config_arg
            if provider_config_arg["name"] == provider1_name:
                mock_instance.get_events_xml.return_value = xml_provider1
            elif provider_config_arg["name"] == provider2_name:
                mock_instance.get_events_xml.return_value = xml_provider2
            else:
                mock_instance.get_events_xml.return_value = None
            return mock_instance

        with (
            patch("app.tasks.sync.logger.info") as mock_sync_logger_info,
            patch(
                "app.tasks.sync.ProviderClient",
                side_effect=mock_provider_client_class_side_effect,
            ) as MockProviderClientClass,
            patch("app.tasks.sync.current_app", new=mocked_task_app_context),
        ):
            sync_provider_events()
            mock_sync_logger_info.assert_any_call(
                "Starting provider events synchronization task for all providers."
            )
            assert MockProviderClientClass.call_count == len(mock_provider_configs)
            MockProviderClientClass.assert_any_call(mock_provider_configs[0])
            MockProviderClientClass.assert_any_call(mock_provider_configs[1])

            repo = EventRepository(session)
            event1 = (
                repo.db_session.query(Event)
                .filter_by(base_event_id="multi_291", provider_name=provider1_name)
                .first()
            )
            assert (
                event1 is not None
            ), f"Event multi_291 from {provider1_name} not found."
            assert event1.title == f"Event Alpha by {provider1_name}"
            event2 = (
                repo.db_session.query(Event)
                .filter_by(base_event_id="multi_322", provider_name=provider2_name)
                .first()
            )
            assert (
                event2 is not None
            ), f"Event multi_322 from {provider2_name} not found."
            assert event2.title == f"Event Beta by {provider2_name}"


def test_sync_malformed_xml_parsing_error(
    app: Flask, session, mocked_task_app_context: MagicMock
):
    """
    Test the sync_provider_events task when the provider returns malformed XML.
    Ensures the error is logged by the task and no data is saved.
    """
    with app.app_context():
        provider_name = "malformed_xml_provider"
        mock_provider_config_list = [
            {
                "name": provider_name,
                "url": "http://malformedprovider.com/api",
                "timeout": 10,
            }
        ]
        with open("tests/fixtures/malformed_sample.xml", "r") as f:
            malformed_xml_content = f.read()

        # Override the config on the mocked_task_app_context for this specific test
        mocked_task_app_context.config = {"PROVIDERS": mock_provider_config_list}

        initial_event_count = session.query(Event).count()

        with (
            patch("app.tasks.sync.logger.info") as mock_sync_logger_info,
            patch("app.tasks.sync.logger.warning") as mock_sync_logger_warning,
            patch("app.tasks.sync.logger.error") as mock_sync_logger_error,
            patch("app.core.parser.logger.error") as mock_parser_logger_error,
            patch("app.tasks.sync.ProviderClient") as MockProviderClientClass,
            patch("app.tasks.sync.current_app", new=mocked_task_app_context),
        ):
            mock_provider_instance = MockProviderClientClass.return_value
            mock_provider_instance.get_events_xml.return_value = malformed_xml_content
            sync_provider_events()

            mock_sync_logger_info.assert_any_call(
                "Starting provider events synchronization task for all providers."
            )
            MockProviderClientClass.assert_called_once_with(
                mock_provider_config_list[0]
            )
            mock_provider_instance.get_events_xml.assert_called_once()

            # Parser should log the XMLSyntaxError
            parser_error_logged = any(
                "XML Syntax Error"
                in call.args[0]  # XMLSyntaxError is logged by app.core.parser.logger
                for call in mock_parser_logger_error.mock_calls
            )
            assert (
                parser_error_logged
            ), f"Parser did not log an XMLSyntaxError. Calls: {mock_parser_logger_error.mock_calls}"

            # The task should NOT log an error itself for XMLSyntaxError, as the parser handles it and returns None.
            mock_sync_logger_error.assert_not_called()

            # The task should log a warning because parse_event_xml returned None.
            sync_task_none_warning_logged = any(
                f"XML parsing from provider {provider_name} resulted in None. Skipping."
                in call.args[0]
                for call in mock_sync_logger_warning.mock_calls
            )
            assert (
                sync_task_none_warning_logged
            ), f"Sync task did not warn about 'resulted in None' for {provider_name} after syntax error. Warning calls: {mock_sync_logger_warning.mock_calls}"

            assert session.query(Event).count() == initial_event_count
            broken_event_in_db = (
                session.query(Event)
                .filter_by(base_event_id="999", provider_name=provider_name)
                .first()
            )
            assert (
                broken_event_in_db is None
            ), "Event from malformed XML was incorrectly saved."
