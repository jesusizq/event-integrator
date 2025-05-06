from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ParsedZone(BaseModel):
    id: str
    name: str
    price: float
    capacity: int
    numbered: bool


class ParsedEventPlan(BaseModel):
    id: str
    start_date: datetime
    end_date: datetime
    sell_from: datetime
    sell_to: datetime
    sold_out: bool = False
    zones: List[ParsedZone] = Field(default_factory=list)


class ParsedEvent(BaseModel):
    id: str
    title: str
    sell_mode: Optional[str] = None
    organizer_company_id: Optional[str] = None
    event_plans: List[ParsedEventPlan] = Field(default_factory=list)
    provider_name: str
