#!/usr/bin/env python
import logging
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from app.core.parser import parse_event_xml

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    sample_xml_provider_data = """<?xml version="1.0" encoding="UTF-8"?>
<planList xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0" xsi:noNamespaceSchemaLocation="planList.xsd">
   <output>
      <base_plan base_plan_id="291" sell_mode="online" title="Camela en concierto">
         <plan plan_start_date="2021-06-30T21:00:00" plan_end_date="2021-06-30T22:00:00" plan_id="291" sell_from="2020-07-01T00:00:00" sell_to="2021-06-30T20:00:00" sold_out="false">
            <zone zone_id="40" capacity="243" price="20.00" name="Platea" numbered="true" />
            <zone zone_id="38" capacity="100" price="15.00" name="Grada 2" numbered="false" />
         </plan>
      </base_plan>
      <base_plan base_plan_id="322" sell_mode="online" organizer_company_id="2" title="Pantomima Full">
         <plan plan_start_date="2021-02-10T20:00:00" plan_end_date="2021-02-10T21:30:00" plan_id="1642" sell_from="2021-01-01T00:00:00" sell_to="2021-02-09T19:50:00" sold_out="false">
            <zone zone_id="311" capacity="2" price="55.00" name="A42" numbered="true" />
         </plan>
         <plan plan_start_date="2021-02-11T20:00:00" plan_end_date="2021-02-11T21:30:00" plan_id="1643" sell_from="2021-01-01T00:00:00" sell_to="2021-02-10T19:50:00" sold_out="false">
            <zone zone_id="311" capacity="2" price="55.00" name="A42" numbered="true" />
         </plan>
      </base_plan>
      <base_plan base_plan_id="CORRUPT" title="Corrupt Data Test">
          <plan plan_id="C1" sold_out="false">
              <zone zone_id="Z1" capacity="NOT_AN_INT" price="10.0" name="Bad Capacity" numbered="true"/>
              <zone zone_id="Z2" capacity="10" price="NOT_A_FLOAT" name="Bad Price" numbered="false"/>
          </plan>
      </base_plan>
   </output>
</planList>
    """

    logger.info("Attempting to parse sample provider XML...")
    parsed_events_list = parse_event_xml(sample_xml_provider_data)

    if parsed_events_list:
        logger.info(f"Successfully parsed {len(parsed_events_list)} base events.")
        for event_obj in parsed_events_list:
            logger.info(
                f"Base Event: {event_obj.title} (ID: {event_obj.id}), "
                f"SellMode: {event_obj.sell_mode}, OrgID: {event_obj.organizer_company_id}, "
                f"Plans: {len(event_obj.event_plans)}"
            )
            for plan_obj in event_obj.event_plans:
                logger.info(
                    f"  Plan: (ID: {plan_obj.id}), Start: {plan_obj.start_date}, End: {plan_obj.end_date}, "
                    f"SellFrom: {plan_obj.sell_from}, SellTo: {plan_obj.sell_to}, SoldOut: {plan_obj.sold_out}, "
                    f"Zones: {len(plan_obj.zones)}"
                )
                for zone_obj in plan_obj.zones:
                    logger.info(
                        f"    Zone: {zone_obj.name} (ID: {zone_obj.id}), Price: {zone_obj.price}, "
                        f"Capacity: {zone_obj.capacity}, Numbered: {zone_obj.numbered}"
                    )

        # Check for correct handling of corrupt zone/plan data
        corrupt_base_event = next(
            (e for e in parsed_events_list if e.id == "CORRUPT"), None
        )
        if corrupt_base_event:
            logger.info(
                f"Found base_event with ID 'CORRUPT': Title '{corrupt_base_event.title}'"
            )
            if corrupt_base_event.event_plans:
                corrupt_plan = next(
                    (p for p in corrupt_base_event.event_plans if p.id == "C1"), None
                )
                if corrupt_plan:
                    if not corrupt_plan.zones:
                        logger.info(
                            "Corrupt data test: Plan 'C1' in Event 'CORRUPT' has no zones, as expected (all its zones had errors)."
                        )
                    else:
                        logger.warning(
                            f"Corrupt data test: Plan 'C1' in Event 'CORRUPT' has {len(corrupt_plan.zones)} zones, expected 0."
                        )
                else:
                    logger.info(
                        "Corrupt data test: Plan 'C1' was not parsed under 'CORRUPT' event as expected (if plan itself had critical error, or no valid zones). Note: current parser skips bad zones but keeps the plan."
                    )
            else:
                logger.info(
                    "Corrupt data test: Event 'CORRUPT' has no plans, which might be expected if the plan itself had errors or no valid zones led to plan omission."
                )
        else:
            logger.warning(
                "Corrupt data test: Base event 'CORRUPT' was not found in parsed results."
            )

    else:
        logger.warning(
            "Failed to parse sample provider XML or an empty list was returned."
        )

    logger.info("\nAttempting to parse empty XML...")
    parsed_empty = parse_event_xml("")
    if parsed_empty is None:
        logger.info("Parsing empty XML handled correctly (returned None).")
    else:
        logger.error(
            f"Parsing empty XML returned {type(parsed_empty)} instead of None."
        )

    logger.info("\nAttempting to parse malformed XML (syntax error)...")
    malformed_xml = (
        "<planList><output><base_plan></plan></base_plan></output></planListNONSENSE>"
    )
    parsed_malformed = parse_event_xml(malformed_xml)
    if parsed_malformed is None:
        logger.info("Parsing malformed XML handled correctly (returned None).")
    else:
        logger.error(
            f"Parsing malformed XML returned {type(parsed_malformed)} instead of None."
        )
