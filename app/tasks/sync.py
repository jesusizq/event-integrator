import logging
from app.extensions import celery, db
from app.services.provider_client import ProviderClient
from app.core.parser import parse_event_xml
from app.models.repository import EventRepository
from app.core.parsing_schemas import ParsedEvent
from typing import List, Optional

logger = logging.getLogger(__name__)


@celery.task(name="tasks.sync_provider_events")
def sync_provider_events():
    """
    Celery task to fetch event data from the provider, parse it,
    and update the database.
    """
    logger.info("Starting provider events synchronization task.")

    provider_client = ProviderClient()
    xml_data: Optional[str] = None

    try:
        logger.info("Fetching events XML from provider.")
        xml_data = provider_client.get_events_xml()
    except Exception as e:
        logger.error(f"Error fetching events XML from provider: {e}", exc_info=True)
        return

    if not xml_data:
        logger.warning("No XML data received from provider. Ending sync task.")
        return

    logger.info("Successfully fetched XML data. Parsing events...")
    parsed_events: Optional[List[ParsedEvent]] = None
    try:
        parsed_events = parse_event_xml(xml_data)
    except Exception as e:
        logger.error(f"Error parsing event XML data: {e}", exc_info=True)
        return

    if parsed_events is None:
        logger.warning(
            "XML parsing resulted in no events or a failure. Ending sync task."
        )
        return

    if not parsed_events:
        logger.info("No events found in the parsed XML data. Ending sync task.")
        return

    logger.info(
        f"Successfully parsed {len(parsed_events)} events. Upserting into database..."
    )

    try:
        event_repository = EventRepository(db.session)
        event_repository.upsert_events(parsed_events)
        logger.info("Provider events synchronization task completed successfully.")
    except Exception as e:
        logger.error(f"Error upserting events into database: {e}", exc_info=True)
