from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.extensions import db
import uuid
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class Event(db.Model):
    __tablename__ = "events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    base_event_id = Column(String, nullable=False)
    provider_name = Column(String, nullable=False)
    title = Column(String, nullable=False)
    sell_mode = Column(String, nullable=True)
    organizer_company_id = Column(String, nullable=True)

    ever_online = Column(Boolean, default=False, nullable=False, index=True)
    first_seen_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    event_plans = relationship(
        "EventPlan", back_populates="event", cascade="all, delete-orphan", lazy="select"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "base_event_id", "provider_name", name="uq_event_base_id_provider"
        ),
        Index("idx_event_last_seen_at", "last_seen_at"),
        Index("idx_event_ever_online", "ever_online"),
        Index("idx_event_provider_name", "provider_name"),
    )

    def __repr__(self):
        return f"<Event id={self.id} base_event_id='{self.base_event_id}' provider='{self.provider_name}' title='{self.title[:20]}'>"


class EventPlan(db.Model):
    __tablename__ = "event_plans"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True
    )

    base_plan_id = Column(String, nullable=False)
    provider_name = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False, index=True)
    end_date = Column(DateTime(timezone=True), nullable=False, index=True)
    sell_from = Column(DateTime(timezone=True), nullable=False)
    sell_to = Column(DateTime(timezone=True), nullable=False)
    sold_out = Column(Boolean, nullable=False, default=False)

    first_seen_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    event = relationship("Event", back_populates="event_plans", lazy="select")
    zones = relationship(
        "Zone", back_populates="event_plan", cascade="all, delete-orphan", lazy="select"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "base_plan_id",
            "provider_name",
            "event_id",
            name="uq_plan_base_id_provider_event",
        ),
        Index("idx_event_plan_last_seen_at", "last_seen_at"),
        Index("idx_event_plan_provider_name", "provider_name"),
        Index("idx_event_plan_start_end_date", "start_date", "end_date"),
    )

    def __repr__(self):
        return f"<EventPlan id={self.id} base_plan_id='{self.base_plan_id}' provider='{self.provider_name}' event_id='{self.event_id}'>"


class Zone(db.Model):
    __tablename__ = "zones"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_plan_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("event_plans.id"),
        nullable=False,
        index=True,
    )

    zone_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    capacity = Column(Integer, nullable=False)
    is_numbered = Column(Boolean, nullable=False)

    first_seen_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    event_plan = relationship("EventPlan", back_populates="zones", lazy="select")

    __table_args__ = (
        db.UniqueConstraint("zone_id", "event_plan_id", name="uq_zone_base_id_plan"),
        Index("idx_zone_price", "price"),
        Index("idx_zone_last_seen_at", "last_seen_at"),
    )

    def __repr__(self):
        return f"<Zone id={self.id} zone_id='{self.zone_id}' name='{self.name}' event_plan_id='{self.event_plan_id}'>"
