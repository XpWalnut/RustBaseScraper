from typing import List, Optional

from pydantic import BaseModel, Field


class SearchInput(BaseModel):
    footprint: Optional[str] = None
    team_size: Optional[str] = None
    notes: Optional[str] = None


class BaseTraits(BaseModel):
    footprint_guess: Optional[str] = None
    footprint_tags: List[str] = Field(default_factory=list)
    footprint_complexity: Optional[str] = None
    floors_visible: Optional[int] = None
    roof_shapes: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    stage: Optional[str] = None
    confidence: float = 0.0
    generated_queries: List[str] = Field(default_factory=list)
    reasoning_summary: str = ""


class VideoCandidate(BaseModel):
    video_id: str
    title: str
    channel_title: str
    description: str = ""
    published_at: Optional[str] = None
    thumbnail_url: Optional[str] = None
    url: str


class RankedMatch(VideoCandidate):
    score: float
    reasons: List[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    extracted_traits: BaseTraits
    matches: List[RankedMatch]