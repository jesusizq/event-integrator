import pytest
from pathlib import Path
from app.core.parser import parse_event_xml
from datetime import datetime


def load_fixture(name: str) -> str:
    fixture_path = Path(__file__).parent.parent / "fixtures" / name
    with open(fixture_path, "r", encoding="utf-8") as f:
        return f.read()


class TestParseEventXML:
    def test_parse_valid_xml(self):
        xml_string = load_fixture("valid_sample.xml")
        provider_name = "test_provider"
        parsed_events = parse_event_xml(xml_string, provider_name)

        assert parsed_events is not None
        assert len(parsed_events) == 3

        # assertions for the first event (Camela en concierto)
        event1 = parsed_events[0]
        assert event1.id == "291"
        assert event1.title == "Camela en concierto"
        assert event1.sell_mode == "online"
        assert event1.organizer_company_id is None
        assert event1.provider_name == provider_name
        assert len(event1.event_plans) == 1

        plan1_event1 = event1.event_plans[0]
        assert plan1_event1.id == "291"
        assert plan1_event1.start_date == datetime(2021, 6, 30, 21, 0, 0)
        assert plan1_event1.end_date == datetime(2021, 6, 30, 22, 0, 0)
        assert plan1_event1.sell_from == datetime(2020, 7, 1, 0, 0, 0)
        assert plan1_event1.sell_to == datetime(2021, 6, 30, 20, 0, 0)
        assert not plan1_event1.sold_out
        assert len(plan1_event1.zones) == 3

        zone1_plan1_event1 = plan1_event1.zones[0]
        assert zone1_plan1_event1.id == "40"
        assert zone1_plan1_event1.name == "Platea"
        assert zone1_plan1_event1.price == 20.00
        assert zone1_plan1_event1.capacity == 243
        assert zone1_plan1_event1.numbered is True

        zone2_plan1_event1 = plan1_event1.zones[1]
        assert zone2_plan1_event1.id == "38"
        assert zone2_plan1_event1.name == "Grada 2"
        assert zone2_plan1_event1.price == 15.00
        assert zone2_plan1_event1.capacity == 100
        assert zone2_plan1_event1.numbered is False

        zone3_plan1_event1 = plan1_event1.zones[2]
        assert zone3_plan1_event1.id == "30"
        assert zone3_plan1_event1.name == "A28"
        assert zone3_plan1_event1.price == 30.00
        assert zone3_plan1_event1.capacity == 90
        assert zone3_plan1_event1.numbered is True

        # assertions for the second event (Pantomima Full)
        event2 = parsed_events[1]
        assert event2.id == "322"
        assert event2.title == "Pantomima Full"
        assert event2.sell_mode == "online"
        assert event2.organizer_company_id == "2"
        assert event2.provider_name == provider_name
        assert len(event2.event_plans) == 2

        plan1_event2 = event2.event_plans[0]
        assert plan1_event2.id == "1642"
        assert plan1_event2.start_date == datetime(2021, 2, 10, 20, 0, 0)
        assert len(plan1_event2.zones) == 1
        assert plan1_event2.zones[0].id == "311"
        assert plan1_event2.zones[0].capacity == 2

        plan2_event2 = event2.event_plans[1]
        assert plan2_event2.id == "1643"
        assert plan2_event2.start_date == datetime(2021, 2, 11, 20, 0, 0)
        assert len(plan2_event2.zones) == 1
        assert plan2_event2.zones[0].id == "311"
        assert plan2_event2.zones[0].capacity == 2

        # assertions for the third event (Los Morancos)
        event3 = parsed_events[2]
        assert event3.id == "1591"
        assert event3.title == "Los Morancos"
        assert event3.sell_mode == "online"
        assert event3.organizer_company_id == "1"
        assert event3.provider_name == provider_name
        assert len(event3.event_plans) == 1

        plan1_event3 = event3.event_plans[0]
        assert plan1_event3.id == "1642"
        assert plan1_event3.start_date == datetime(2021, 7, 31, 20, 0, 0)
        assert len(plan1_event3.zones) == 2
        assert plan1_event3.zones[0].id == "186"
        assert plan1_event3.zones[0].capacity == 2
        assert plan1_event3.zones[0].numbered is True
        assert plan1_event3.zones[1].id == "186"
        assert plan1_event3.zones[1].capacity == 16
        assert plan1_event3.zones[1].numbered is False

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
        event1 = next((e for e in parsed_events if e.id == "100"), None)
        assert event1 is not None
        assert event1.title == "Event With Missing Optional Fields"
        assert event1.sell_mode is None
        assert event1.organizer_company_id is None
        assert event1.provider_name == provider_name
        assert len(event1.event_plans) == 1
        assert event1.event_plans[0].id == "101"
        assert len(event1.event_plans[0].zones) == 1
        assert event1.event_plans[0].zones[0].id == "Z1"

        # Event 2 (base_plan_id="200") - contains some invalid zones within a plan
        event2 = next((e for e in parsed_events if e.id == "200"), None)
        assert event2 is not None
        assert event2.title == "Event With Invalid Zone"
        assert event2.sell_mode == "online"
        assert event2.provider_name == provider_name
        assert len(event2.event_plans) == 1

        plan_event2 = event2.event_plans[0]
        assert plan_event2.id == "201"
        # Should only contain the one valid zone ("Z2A")
        # "Z2B" (invalid capacity) and "Z2C" (invalid price) should be skipped
        assert len(plan_event2.zones) == 1
        assert plan_event2.zones[0].id == "Z2A"
        assert plan_event2.zones[0].name == "Good Zone"
        assert plan_event2.zones[0].capacity == 100

        # Event 3 (base_plan_id="300") - valid base_plan, but its plan is invalid and skipped
        event3 = next((e for e in parsed_events if e.id == "300"), None)
        assert event3 is not None
        assert event3.title == "Event With Invalid Plan"
        assert event3.sell_mode == "online"
        assert event3.provider_name == provider_name
        assert len(event3.event_plans) == 0  # Its plan was invalid and skipped

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
