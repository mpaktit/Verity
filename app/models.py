from pydantic import BaseModel, Field
from typing import List, Optional


class OfferRecord(BaseModel):
    provider: str
    product: str
    category: str
    offer_type: str
    status: str = Field(default='active')
    reward: str
    eligibility: str
    source: str
    risk_level: str = Field(default='medium')
    official: bool = True
    verified: bool = False
    score: int = Field(default=0, ge=0, le=100)
    expires_at: Optional[str] = None
    notes: str


class SummaryResponse(BaseModel):
    total_offers: int
    active_offers: int
    high_confidence: int
    needs_review: int
    categories: List[str]
