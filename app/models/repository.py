from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError
from app.models.event import Event, EventPlan, Zone
from app.models.enums import SellModeEnum
from app.core.parsing_schemas import ParsedEvent, ParsedEventPlan, ParsedZone
from datetime import datetime, timezone
from typing import List, Set
import logging

logger = logging.getLogger(__name__)

EVENT_UPSERT_BATCH_SIZE = 100


class EventRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def _upsert_zone(
        self, event_plan: EventPlan, parsed_zone: ParsedZone, current_time: datetime
    ) -> Zone:
        """
        Upserts a zone in the database.
        """
        zone = (
            self.db_session.query(Zone)
            .filter_by(
                event_plan_id=event_plan.id,
                zone_id=parsed_zone.id,
            )
            .first()
        )

        if not zone:
            zone = Zone(
                event_plan_id=event_plan.id,
                zone_id=parsed_zone.id,
                name=parsed_zone.name,
                price=parsed_zone.price,
                capacity=parsed_zone.capacity,
                is_numbered=parsed_zone.numbered,
                first_seen_at=current_time,
            )
            self.db_session.add(zone)
        else:
            zone.name = parsed_zone.name
            zone.price = parsed_zone.price
            zone.capacity = parsed_zone.capacity
            zone.is_numbered = parsed_zone.numbered

        zone.last_seen_at = current_time
        # The relationship appending is handled by SQLAlchemy if back_populates is set
        # and the foreign key (event_plan_id) is correctly assigned.
        return zone

    def _upsert_event_plan(
        self, event: Event, parsed_plan: ParsedEventPlan, current_time: datetime
    ) -> EventPlan:
        """
        Upserts an event plan associated with an event.
        Event plan uniqueness is based on its base_plan_id, provider_name, and the event_id it belongs to.
        """
        event_plan = (
            self.db_session.query(EventPlan)
            .filter_by(
                event_id=event.id,
                base_plan_id=parsed_plan.id,
                provider_name=event.provider_name,
            )
            .first()
        )

        if not event_plan:
            event_plan = EventPlan(
                event_id=event.id,
                base_plan_id=parsed_plan.id,
                provider_name=event.provider_name,
                start_date=parsed_plan.start_date,
                end_date=parsed_plan.end_date,
                sell_from=parsed_plan.sell_from,
                sell_to=parsed_plan.sell_to,
                sold_out=parsed_plan.sold_out,
                first_seen_at=current_time,
            )
            self.db_session.add(event_plan)
        else:
            event_plan.start_date = parsed_plan.start_date
            event_plan.end_date = parsed_plan.end_date
            event_plan.sell_from = parsed_plan.sell_from
            event_plan.sell_to = parsed_plan.sell_to
            event_plan.sold_out = parsed_plan.sold_out

        event_plan.last_seen_at = current_time

        seen_zone_ids_in_provider_feed: Set[str] = set()
        for parsed_zone_data in parsed_plan.zones:
            self._upsert_zone(event_plan, parsed_zone_data, current_time)
            seen_zone_ids_in_provider_feed.add(parsed_zone_data.id)

        (
            self.db_session.query(Zone)
            .filter(
                Zone.event_plan_id == event_plan.id,
                Zone.zone_id.notin_(seen_zone_ids_in_provider_feed),
            )
            .update(
                {Zone.last_seen_at: current_time - func.timedelta(seconds=1)},
                synchronize_session=False,
            )  # Mark as slightly older
        )

        return event_plan

    def _upsert_event(self, parsed_event: ParsedEvent, current_time: datetime) -> Event:
        """
        Upserts an event.
        Event uniqueness is based on its base_event_id and provider_name.
        """
        if not parsed_event.provider_name:
            raise ValueError("ParsedEvent must have a provider_name.")

        event = (
            self.db_session.query(Event)
            .filter_by(
                base_event_id=parsed_event.id,
                provider_name=parsed_event.provider_name,
            )
            .first()
        )

        sell_mode_enum_str = None
        if parsed_event.sell_mode:
            try:
                SellModeEnum.from_string(parsed_event.sell_mode)
                sell_mode_enum_str = parsed_event.sell_mode
            except ValueError:
                pass

        if not event:
            event = Event(
                base_event_id=parsed_event.id,
                provider_name=parsed_event.provider_name,
                title=parsed_event.title,
                sell_mode=sell_mode_enum_str,
                organizer_company_id=parsed_event.organizer_company_id,
                first_seen_at=current_time,
                ever_online=False,
            )
            self.db_session.add(event)
        else:
            event.title = parsed_event.title
            event.organizer_company_id = parsed_event.organizer_company_id
            event.sell_mode = sell_mode_enum_str

        if sell_mode_enum_str == SellModeEnum.ONLINE.value:
            event.ever_online = True

        event.last_seen_at = current_time

        seen_plan_ids_in_provider_feed: Set[str] = set()
        for parsed_plan_data in parsed_event.event_plans:
            self._upsert_event_plan(event, parsed_plan_data, current_time)
            seen_plan_ids_in_provider_feed.add(parsed_plan_data.id)

        (
            self.db_session.query(EventPlan)
            .filter(
                EventPlan.event_id == event.id,
                EventPlan.provider_name == event.provider_name,
                EventPlan.base_plan_id.notin_(seen_plan_ids_in_provider_feed),
            )
            .update(
                {EventPlan.last_seen_at: current_time - func.timedelta(seconds=1)},
                synchronize_session=False,
            )
        )

        return event

    def upsert_events(
        self, events_data: List[ParsedEvent], provider_name_filter: str = None
    ):
        """
        Inserts or updates events, their plans, and zones using ParsedEvent models,
        processing them in batches. If provider_name_filter is specified, also updates
        last_seen_at for events from that provider that are not present in the current
        events_data after all batches are successfully processed.
        """
        current_time = datetime.now(timezone.utc)
        processed_event_base_ids_for_provider: Set[str] = set()

        for i in range(0, len(events_data), EVENT_UPSERT_BATCH_SIZE):
            batch_events_data = events_data[i : i + EVENT_UPSERT_BATCH_SIZE]

            for parsed_event in batch_events_data:
                if not parsed_event.id or not parsed_event.provider_name:
                    logger.warning(
                        "Skipping event due to missing id or provider_name: %s",
                        parsed_event.id or "UNKNOWN ID",
                    )
                    continue

                if (
                    provider_name_filter
                    and parsed_event.provider_name != provider_name_filter
                ):
                    logger.warning(
                        "Event with id %s and provider %s does not match filter %s. Skipping.",
                        parsed_event.id,
                        parsed_event.provider_name,
                        provider_name_filter,
                    )
                    continue

                try:
                    self._upsert_event(parsed_event, current_time)

                    if (
                        provider_name_filter
                        and parsed_event.provider_name == provider_name_filter
                    ):
                        processed_event_base_ids_for_provider.add(parsed_event.id)

                except ValueError as ve:
                    logger.error(
                        "Validation error processing event %s: %s. Skipping this event.",
                        parsed_event.id,
                        ve,
                    )
                    continue

            # After processing all events in the current batch, attempt to commit.
            try:
                self.db_session.commit()
                logger.info(
                    "Successfully committed batch of %d events. Provider filter: %s.",
                    len(batch_events_data),
                    provider_name_filter or "N/A",
                )
            except SQLAlchemyError as e:
                logger.error(
                    "Database error committing batch for provider filter %s: %s. Rolling back.",
                    provider_name_filter or "N/A",
                    e,
                )
                self.db_session.rollback()
                raise  # Re-raise the exception to halt the upsert process for subsequent batches.

        # After all batches have been successfully processed and committed:
        # If a specific provider was processed, mark events from that provider as "stale".
        if provider_name_filter:
            try:
                logger.info(
                    "Attempting to mark stale events for provider: %s. Events in current feed: %d.",
                    provider_name_filter,
                    len(processed_event_base_ids_for_provider),
                )

                # Mark events as stale slightly in the past to differentiate from genuinely new 'last_seen_at'
                stale_time = current_time - func.timedelta(seconds=1)

                update_count = (
                    self.db_session.query(Event)
                    .filter(
                        Event.provider_name == provider_name_filter,
                        Event.base_event_id.notin_(
                            processed_event_base_ids_for_provider
                        ),
                    )
                    .update(
                        {Event.last_seen_at: stale_time},
                        synchronize_session=False,
                    )
                )
                self.db_session.commit()
                logger.info(
                    "Successfully marked %d stale events for provider %s.",
                    update_count,
                    provider_name_filter,
                )
            except SQLAlchemyError as e:
                logger.error(
                    "Database error marking stale events for provider %s: %s. Rolling back.",
                    provider_name_filter,
                    e,
                )
                self.db_session.rollback()
                raise  # Re-raise to indicate failure in the overall operation.

    def get_events_by_date(self, starts_at: datetime, ends_at: datetime) -> List[Event]:
        """
        Retrieves Events that have at least one EventPlan starting within the given datetime range
        and have ever_online set to True.
        Uses joinedload to eager load event_plans and their zones to avoid N+1 queries.
        """
        return (
            self.db_session.query(Event)
            .options(joinedload(Event.event_plans).joinedload(EventPlan.zones))
            .join(EventPlan, Event.id == EventPlan.event_id)
            .filter(
                Event.ever_online == True,
                EventPlan.start_date >= starts_at,
                EventPlan.start_date <= ends_at,
            )
            .distinct()
            .all()
        )
