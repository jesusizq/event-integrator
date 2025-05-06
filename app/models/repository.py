from sqlalchemy.orm import Session
from app.models.event import BaseEvent as Event, EventPlan, Zone
from app.models.enums import SellModeEnum
from app.core.parsing_schemas import ParsedEvent, ParsedEventPlan, ParsedZone
from datetime import date, datetime, timezone
from typing import List


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
                event_plan_db_id=event_plan.id,
                provider_zone_id=parsed_zone.id,
                name=parsed_zone.name,
                price=parsed_zone.price,
                is_numbered=parsed_zone.numbered,
            )
            .first()
        )

        if not zone and event_plan.id:  # Check in-memory collection if plan has an ID
            zone = next(
                (
                    z
                    for z in event_plan.zones
                    if z.provider_zone_id == parsed_zone.id
                    and z.name == parsed_zone.name
                    and z.price == parsed_zone.price
                    and z.is_numbered == parsed_zone.numbered
                ),
                None,
            )

        if not zone:
            zone = Zone(
                event_plan=event_plan,
                provider_zone_id=parsed_zone.id,
                name=parsed_zone.name,
                price=parsed_zone.price,
                capacity=parsed_zone.capacity,
                is_numbered=parsed_zone.numbered,
                first_seen_at=current_time,
            )
        else:
            zone.capacity = (
                parsed_zone.capacity
            )  # Price, name and numbered are part of the key

        zone.last_seen_at = current_time
        if zone not in event_plan.zones:
            event_plan.zones.append(zone)
        return zone

    def _upsert_event_plan(
        self, base_event: Event, parsed_plan: ParsedEventPlan, current_time: datetime
    ) -> EventPlan:
        """
        Upserts an event plan in the database.
        """
        event_plan = None
        if base_event.id:
            event_plan = (
                self.db_session.query(EventPlan)
                .filter_by(
                    base_event_id=base_event.id,
                    provider_plan_id=parsed_plan.id,
                )
                .first()
            )

        if not event_plan:  # Check in-memory collection if plan has an ID
            event_plan = next(
                (
                    p
                    for p in base_event.event_plans
                    if p.provider_plan_id == parsed_plan.id
                ),
                None,
            )

        if not event_plan:
            event_plan = EventPlan(
                base_event=base_event,
                provider_plan_id=parsed_plan.id,
                start_date=parsed_plan.start_date,
                end_date=parsed_plan.end_date,
                sell_from=parsed_plan.sell_from,
                sell_to=parsed_plan.sell_to,
                sold_out=parsed_plan.sold_out,
                first_seen_at=current_time,
            )
        else:
            event_plan.start_date = parsed_plan.start_date
            event_plan.end_date = parsed_plan.end_date
            event_plan.sell_from = parsed_plan.sell_from
            event_plan.sell_to = parsed_plan.sell_to
            event_plan.sold_out = parsed_plan.sold_out

        event_plan.last_seen_at = current_time
        if event_plan not in base_event.event_plans:
            base_event.event_plans.append(event_plan)

        for parsed_zone_data in parsed_plan.zones:
            self._upsert_zone(event_plan, parsed_zone_data, current_time)

        return event_plan

    def _upsert_base_event(
        self, parsed_event: ParsedEvent, current_time: datetime
    ) -> Event:
        """
        Upserts a base event in the database.
        """
        base_event = (
            self.db_session.query(Event)
            .filter_by(base_event_provider_id=parsed_event.id)
            .first()
        )

        sell_mode_enum = SellModeEnum.OFFLINE
        if parsed_event.sell_mode:
            try:
                sell_mode_enum = SellModeEnum.from_string(parsed_event.sell_mode)
            except ValueError:
                return

        if not base_event:
            base_event = Event(
                base_event_provider_id=parsed_event.id,
                title=parsed_event.title,
                organizer_company_id=parsed_event.organizer_company_id,
                first_seen_at=current_time,
            )
            self.db_session.add(base_event)
        else:
            base_event.title = parsed_event.title
            base_event.organizer_company_id = parsed_event.organizer_company_id

        base_event.sell_mode = sell_mode_enum
        if sell_mode_enum == SellModeEnum.ONLINE:
            base_event.ever_online = True

        base_event.last_seen_at = current_time

        for parsed_plan_data in parsed_event.event_plans:
            self._upsert_event_plan(base_event, parsed_plan_data, current_time)

        return base_event

    def upsert_events(self, events_data: List[ParsedEvent]):
        """
        Inserts or updates events, their plans, and zones using ParsedEvent models.
        """
        current_time = datetime.now(timezone.utc)

        for parsed_event in events_data:
            if not parsed_event.id:
                continue
            self._upsert_base_event(parsed_event, current_time)

        self.db_session.commit()

    def get_events_by_date(self, starts_at: date, ends_at: date) -> List[Event]:
        """
        Retrieves BaseEvents that have at least one EventPlan starting within the given date range
        and have ever_online set to True.
        """
        return (
            self.db_session.query(Event)
            .join(EventPlan, Event.id == EventPlan.base_event_id)
            .filter(
                Event.ever_online == True,
                EventPlan.start_date >= starts_at,
                EventPlan.start_date <= ends_at,
            )
            .distinct()  # Avoid duplicate BaseEvents if multiple plans match
            .all()
        )
