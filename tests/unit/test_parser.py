from pathlib import Path
from app.core.parser import parse_event_xml
from datetime import datetime


def load_fixture(name: str) -> str:
    fixture_path = Path(__file__).parent.parent / "fixtures" / name
    with open(fixture_path, "r", encoding="utf-8") as f:
        return f.read()


def _assert_event_data(event_actual, event_expected_data, provider_name_to_check):
    """
    Assert that the event data structure is correct.
    """
    assert event_actual.id == event_expected_data["id"]
    assert event_actual.title == event_expected_data["title"]
    assert event_actual.sell_mode == event_expected_data["sell_mode"]
    assert (
        event_actual.organizer_company_id == event_expected_data["organizer_company_id"]
    )
    assert event_actual.provider_name == provider_name_to_check

    expected_plans = event_expected_data.get("plans", [])
    assert len(event_actual.event_plans) == len(expected_plans)

    for i, plan_expected in enumerate(expected_plans):
        plan_actual = event_actual.event_plans[i]
        assert plan_actual.id == plan_expected["id"]

        if "start_date" in plan_expected:
            assert plan_actual.start_date == plan_expected["start_date"]
        if "end_date" in plan_expected:
            assert plan_actual.end_date == plan_expected["end_date"]
        if "sell_from" in plan_expected:
            assert plan_actual.sell_from == plan_expected["sell_from"]
        if "sell_to" in plan_expected:
            assert plan_actual.sell_to == plan_expected["sell_to"]
        if "sold_out" in plan_expected:
            assert plan_actual.sold_out == plan_expected["sold_out"]

        expected_zones = plan_expected.get("zones", [])
        assert len(plan_actual.zones) == len(expected_zones)
        for j, zone_expected in enumerate(expected_zones):
            zone_actual = plan_actual.zones[j]
            assert zone_actual.id == zone_expected["id"]

            if "name" in zone_expected:
                assert zone_actual.name == zone_expected["name"]
            if "price" in zone_expected:
                assert zone_actual.price == zone_expected["price"]
            if "capacity" in zone_expected:
                assert zone_actual.capacity == zone_expected["capacity"]
            if "numbered" in zone_expected:
                assert zone_actual.numbered is zone_expected["numbered"]


class TestParseEventXML:
    def test_parse_valid_xml(self):
        xml_string = load_fixture("valid_sample.xml")
        provider_name = "test_provider"
        parsed_events = parse_event_xml(xml_string, provider_name)

        assert parsed_events is not None
        assert len(parsed_events) == 3

        # Expected data for the first event (Camela en concierto)
        event1_expected = {
            "id": "291",
            "title": "Camela en concierto",
            "sell_mode": "online",
            "organizer_company_id": None,
            "plans": [
                {
                    "id": "291",
                    "start_date": datetime(2021, 6, 30, 21, 0, 0),
                    "end_date": datetime(2021, 6, 30, 22, 0, 0),
                    "sell_from": datetime(2020, 7, 1, 0, 0, 0),
                    "sell_to": datetime(2021, 6, 30, 20, 0, 0),
                    "sold_out": False,
                    "zones": [
                        {
                            "id": "40",
                            "name": "Platea",
                            "price": 20.00,
                            "capacity": 243,
                            "numbered": True,
                        },
                        {
                            "id": "38",
                            "name": "Grada 2",
                            "price": 15.00,
                            "capacity": 100,
                            "numbered": False,
                        },
                        {
                            "id": "30",
                            "name": "A28",
                            "price": 30.00,
                            "capacity": 90,
                            "numbered": True,
                        },
                    ],
                }
            ],
        }
        _assert_event_data(parsed_events[0], event1_expected, provider_name)

        # Expected data for the second event (Pantomima Full)
        event2_expected = {
            "id": "322",
            "title": "Pantomima Full",
            "sell_mode": "online",
            "organizer_company_id": "2",
            "plans": [
                {
                    "id": "1642",
                    "start_date": datetime(2021, 2, 10, 20, 0, 0),
                    "zones": [{"id": "311", "capacity": 2}],
                },
                {
                    "id": "1643",
                    "start_date": datetime(2021, 2, 11, 20, 0, 0),
                    "zones": [{"id": "311", "capacity": 2}],
                },
            ],
        }
        _assert_event_data(parsed_events[1], event2_expected, provider_name)

        # Expected data for the third event (Los Morancos)
        event3_expected = {
            "id": "1591",
            "title": "Los Morancos",
            "sell_mode": "online",
            "organizer_company_id": "1",
            "plans": [
                {
                    "id": "1642",
                    "start_date": datetime(2021, 7, 31, 20, 0, 0),
                    "zones": [
                        {"id": "186", "capacity": 2, "numbered": True},
                        {"id": "186", "capacity": 16, "numbered": False},
                    ],
                }
            ],
        }
        _assert_event_data(parsed_events[2], event3_expected, provider_name)

    def test_parse_empty_xml_string(self):
        parsed_events = parse_event_xml("", "test_provider")
        assert parsed_events is None

    def test_parse_malformed_xml(self):
        malformed_xml = "<planList><output><base_plan></output></planList>"  # Missing closing base_plan
        parsed_events = parse_event_xml(malformed_xml, "test_provider")
        assert parsed_events is None

        parsed_events_not_xml = parse_event_xml("this is not xml", "test_provider")
        assert parsed_events_not_xml is None

    def test_parse_xml_with_no_events(self):
        xml_string = """<?xml version="1.0" encoding="UTF-8"?>
<planList version="1.0">
   <output>
   </output>
</planList>"""
        parsed_events = parse_event_xml(xml_string, "test_provider")
        assert parsed_events is not None
        assert len(parsed_events) == 0

    def test_parse_partially_valid_xml(self, caplog):
        xml_string = load_fixture("partially_valid_sample.xml")
        provider_name = "partial_test_provider"
        parsed_events = parse_event_xml(xml_string, provider_name)

        assert parsed_events is not None
        # We expect 3 events to be parsed successfully.
        # Event with base_plan_id="100" is valid and parsed.
        # Event with base_plan_id="200" is valid and parsed; it will have one valid plan and one valid zone (others skipped).
        # Event with base_plan_id="300" is valid and parsed, but its plan is invalid (missing plan_id) and will be skipped, resulting in empty event_plans for this event.
        # Event with base_plan_id="400" (invalid base_plan - missing title) will be skipped entirely.
        assert len(parsed_events) == 3

        # Event 1 (base_plan_id="100") - missing optional fields
        event1_actual = next((e for e in parsed_events if e.id == "100"), None)
        assert event1_actual is not None
        event1_expected = {
            "id": "100",
            "title": "Event With Missing Optional Fields",
            "sell_mode": None,
            "organizer_company_id": None,
            "plans": [
                {
                    "id": "101",
                    "zones": [{"id": "Z1"}],
                }
            ],
        }
        _assert_event_data(event1_actual, event1_expected, provider_name)

        # Event 2 (base_plan_id="200") - contains some invalid zones within a plan
        event2_actual = next((e for e in parsed_events if e.id == "200"), None)
        assert event2_actual is not None
        event2_expected = {
            "id": "200",
            "title": "Event With Invalid Zone",
            "sell_mode": "online",
            "organizer_company_id": None,
            "plans": [
                {
                    "id": "201",
                    "zones": [{"id": "Z2A", "name": "Good Zone", "capacity": 100}],
                }
            ],
        }
        _assert_event_data(event2_actual, event2_expected, provider_name)

        # Event 3 (base_plan_id="300") - valid base_plan, but its plan is invalid and skipped
        event3_actual = next((e for e in parsed_events if e.id == "300"), None)
        assert event3_actual is not None
        event3_expected = {
            "id": "300",
            "title": "Event With Invalid Plan",
            "sell_mode": "online",
            "organizer_company_id": None,
            "plans": [],
        }
        _assert_event_data(event3_actual, event3_expected, provider_name)

        # Check logs for skipped elements
        assert (
            "Error parsing zone data for base_plan_id 200, plan_id 201, zone_id Z2B"
            in caplog.text
        )
        assert "Skipping zone." in caplog.text
        assert (
            "Error parsing zone data for base_plan_id 200, plan_id 201, zone_id Z2C"
            in caplog.text
        )
        assert (
            "Error parsing plan data for base_plan_id 300, plan_id None: 1 validation error for ParsedEventPlan"
            in caplog.text
        )
        assert "id\n  Input should be a valid string" in caplog.text
        assert "Skipping plan." in caplog.text
        assert (
            "Error parsing base_plan data for base_plan_id 400: 1 validation error for ParsedEvent"
            in caplog.text
        )
        assert "title\n  Input should be a valid string" in caplog.text
        assert "Skipping base_plan." in caplog.text
