from lxml import etree
from typing import List, Optional
import logging
from app.core.parsing_schemas import ParsedEvent, ParsedEventPlan, ParsedZone
from pydantic import ValidationError

logger = logging.getLogger(__name__)


def _to_bool(value: Optional[str]) -> bool:
    return value is not None and value.lower() == "true"


def parse_event_xml(xml_string: str, provider_name: str) -> Optional[List[ParsedEvent]]:
    """
    Parses an XML string containing event data from the provider.

    Args:
        xml_string: The XML content as a string.
        provider_name: The name of the provider for this XML data.

    Returns:
        A list of ParsedEvent objects, or None if parsing fails.
    """
    if not xml_string:
        logger.warning("XML string is empty, cannot parse.")
        return None

    try:
        root = etree.fromstring(xml_string.encode("utf-8"))
        all_parsed_events: List[ParsedEvent] = []

        for base_plan_elem in root.xpath("/planList/output/base_plan"):
            event_plans_data: List[ParsedEventPlan] = []
            for plan_elem in base_plan_elem.xpath("./plan"):
                zones_data: List[ParsedZone] = []
                for zone_elem in plan_elem.xpath("./zone"):
                    try:
                        zone_data = {
                            "id": zone_elem.get("zone_id"),
                            "price": zone_elem.get("price"),
                            "name": zone_elem.get("name"),
                            "capacity": zone_elem.get("capacity"),
                            "numbered": _to_bool(zone_elem.get("numbered")),
                        }
                        zones_data.append(ParsedZone(**zone_data))
                    except (ValidationError, ValueError, TypeError) as e:
                        logger.error(
                            f"Error parsing zone data for base_plan_id {base_plan_elem.get('base_plan_id')}, "
                            f"plan_id {plan_elem.get('plan_id')}, zone_id {zone_elem.get('zone_id')}: {e}. Skipping zone."
                        )

                try:
                    plan_data = {
                        "id": plan_elem.get("plan_id"),
                        "plan_start_date": plan_elem.get("plan_start_date"),
                        "plan_end_date": plan_elem.get("plan_end_date"),
                        "sell_from": plan_elem.get("sell_from"),
                        "sell_to": plan_elem.get("sell_to"),
                        "sold_out": _to_bool(plan_elem.get("sold_out")),
                        "zones": zones_data,
                    }
                    plan_data_for_model = {
                        "id": plan_data["id"],
                        "start_date": plan_data["plan_start_date"],
                        "end_date": plan_data["plan_end_date"],
                        "sell_from": plan_data["sell_from"],
                        "sell_to": plan_data["sell_to"],
                        "sold_out": plan_data["sold_out"],
                        "zones": plan_data["zones"],
                    }
                    event_plans_data.append(ParsedEventPlan(**plan_data_for_model))
                except (ValidationError, ValueError, TypeError) as e:
                    logger.error(
                        f"Error parsing plan data for base_plan_id {base_plan_elem.get('base_plan_id')}, "
                        f"plan_id {plan_elem.get('plan_id')}: {e}. Skipping plan."
                    )

            try:
                base_event_data = {
                    "id": base_plan_elem.get("base_plan_id"),
                    "title": base_plan_elem.get("title"),
                    "sell_mode": base_plan_elem.get("sell_mode"),
                    "organizer_company_id": base_plan_elem.get("organizer_company_id"),
                    "event_plans": event_plans_data,
                    "provider_name": provider_name,
                }
                all_parsed_events.append(ParsedEvent(**base_event_data))
            except (ValidationError, ValueError, TypeError) as e:
                logger.error(
                    f"Error parsing base_plan data for base_plan_id {base_plan_elem.get('base_plan_id')}: {e}. Skipping base_plan."
                )

        return all_parsed_events

    except etree.XMLSyntaxError as e:
        logger.error(f"XML Syntax Error: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during XML parsing: {e}")
        return None
