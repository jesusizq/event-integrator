import logging
from flask import current_app
from app.extensions import celery, db
from app.services.provider_client import ProviderClient
from app.core.parser import parse_event_xml
from app.models.repository import EventRepository
from app.core.parsing_schemas import ParsedEvent
from typing import List, Optional

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.sync.sync_provider_events")
def sync_provider_events():
    """
    Celery task to fetch event data from each configured provider, parse it,
    and update the database.
    """
    logger.info("Starting provider events synchronization task for all providers.")

    providers = current_app.config.get("PROVIDERS")
    if not providers:
        logger.warning("No providers configured. Skipping sync task.")
        return

    event_repository = EventRepository(db.session)

    for provider_config in providers:
        provider_name = provider_config.get("name")
        if not provider_name:
            logger.error(
                "Provider config missing 'name'. Skipping this provider.",
                extra={"provider_config": provider_config},
            )
            continue

        logger.info(f"Processing provider: {provider_name}")

        try:
            provider_client = ProviderClient(provider_config)
            xml_data: Optional[str] = None

            logger.info(f"Fetching events XML from provider: {provider_name}.")
            xml_data = provider_client.get_events_xml()

            if not xml_data:
                logger.warning(
                    f"No XML data received from provider: {provider_name}. Skipping this provider."
                )
                continue

            logger.info(
                f"Successfully fetched XML data from {provider_name}. Parsing events..."
            )
            parsed_events_from_provider: Optional[List[ParsedEvent]] = None
            try:
                parsed_events_from_provider = parse_event_xml(xml_data, provider_name)
            except Exception as e:
                logger.error(
                    f"Error parsing event XML data from provider {provider_name}: {e}",
                    exc_info=True,
                )
                continue  # Skip to the next provider

            if parsed_events_from_provider is None:
                logger.warning(
                    f"XML parsing from provider {provider_name} resulted in None. Skipping."
                )
                continue

            events_to_upsert: List[ParsedEvent] = []
            if parsed_events_from_provider:
                events_to_upsert.extend(parsed_events_from_provider)

            if not events_to_upsert:
                logger.info(
                    f"No valid events to upsert after parsing/validation for provider: {provider_name}."
                )
                event_repository.upsert_events(
                    events_to_upsert, provider_name_filter=provider_name
                )
                logger.info(
                    f"Synchronization for provider {provider_name} completed successfully."
                )
                continue

            logger.info(
                f"Successfully processed {len(events_to_upsert)} events from {provider_name}. Upserting into database..."
            )

            event_repository.upsert_events(
                events_to_upsert, provider_name_filter=provider_name
            )
            logger.info(
                f"Synchronization for provider {provider_name} completed successfully."
            )

        except ValueError as ve:
            logger.error(
                f"Configuration or value error for provider {provider_name}: {ve}",
                exc_info=True,
            )
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while processing provider {provider_name}: {e}",
                exc_info=True,
            )
            # Continue to the next provider even if one fails

    logger.info("Provider events synchronization task finished for all providers.")
