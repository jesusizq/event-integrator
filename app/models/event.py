from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    Enum,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.extensions import db
from app.models.enums import SellModeEnum

MAX_ID_LENGTH = 255


class BaseEvent(db.Model):
    __tablename__ = "base_events"

    id = Column(Integer, primary_key=True)
    base_event_provider_id = Column(
        String(MAX_ID_LENGTH), unique=True, nullable=False, index=True
    )
    title = Column(String(MAX_ID_LENGTH), nullable=False)
    sell_mode = Column(Enum(SellModeEnum), nullable=False)
    organizer_company_id = Column(String(MAX_ID_LENGTH), nullable=True)

    ever_online = Column(Boolean, default=False, nullable=False, index=True)
    first_seen_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_seen_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    event_plans = relationship(
        "EventPlan", back_populates="base_event", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<BaseEvent id={self.id} base_event_provider_id='{self.base_event_provider_id}' title='{self.title}'>"


class EventPlan(db.Model):
    __tablename__ = "event_plans"

    id = Column(Integer, primary_key=True)
    base_event_id = Column(
        Integer, ForeignKey("base_events.id"), nullable=False, index=True
    )

    provider_plan_id = Column(String(MAX_ID_LENGTH), nullable=False, index=True)
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False, index=True)
    sell_from = Column(DateTime, nullable=False)
    sell_to = Column(DateTime, nullable=False)
    sold_out = Column(Boolean, nullable=False)

    first_seen_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_seen_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    base_event = relationship("BaseEvent", back_populates="event_plans")
    zones = relationship(
        "Zone", back_populates="event_plan", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "base_event_id", "provider_plan_id", name="uix_base_event_plan"
        ),
    )

    def __repr__(self):
        return f"<EventPlan id={self.id} provider_plan_id='{self.provider_plan_id}' base_provider_event_id='{self.base_event.base_event_provider_id if self.base_event else None}'>"


class Zone(db.Model):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True)
    event_plan_db_id = Column(
        Integer, ForeignKey("event_plans.id"), nullable=False, index=True
    )
    provider_zone_id = Column(String(MAX_ID_LENGTH), nullable=False)
    name = Column(String(MAX_ID_LENGTH), nullable=False)
    price = Column(Float, nullable=False)
    capacity = Column(Integer, nullable=False)
    is_numbered = Column(Boolean, nullable=False)

    first_seen_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_seen_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    event_plan = relationship("EventPlan", back_populates="zones")

    __table_args__ = (
        UniqueConstraint(
            "event_plan_db_id",
            "provider_zone_id",
            "name",
            "price",
            "is_numbered",
            name="uix_event_plan_zone_details",
        ),
    )

    def __repr__(self):
        return f"<Zone id={self.id} provider_zone_id='{self.provider_zone_id}' name='{self.name}' event_plan_id='{self.event_plan.provider_plan_id if self.event_plan else None}'>"
