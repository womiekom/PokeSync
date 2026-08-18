from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class TeamRequest(BaseModel):
    team: List[str]

class PokemonInfo(BaseModel):
    name: str
    pokedex_number: int
    image_url: str
    types: List[str]

class PredictionResponse(BaseModel):
    success: bool
    prediction: Optional[str] = None
    probabilities: Optional[Dict[str, float]] = None
    explanations: Optional[List[str]] = None
    team_data: Optional[List[PokemonInfo]] = None
    error: Optional[str] = None

class SynergyScoreInfo(BaseModel):
    score: int
    rating: str
    rating_color: str
    summary: str
    defensive_score: int
    offensive_score: int
    strategic_score: int

class SynergyStrength(BaseModel):
    title: str
    description: str
    tag: str

class SynergyGap(BaseModel):
    title: str
    description: str
    severity: str
    tag: str

class OffensiveProfile(BaseModel):
    physical_attackers: int
    special_attackers: int
    mixed_attackers: int
    fast_count: int
    mid_count: int
    slow_count: int
    coverage_count: int
    covered_types: List[str]

class BeginnerGuide(BaseModel):
    summary: str
    key_takeaways: List[str]

class SynergyResponse(BaseModel):
    success: bool
    overall: Optional[SynergyScoreInfo] = None
    strengths: Optional[List[SynergyStrength]] = None
    gaps: Optional[List[SynergyGap]] = None
    offensive_profile: Optional[OffensiveProfile] = None
    type_matchups: Optional[Dict[str, Any]] = None
    strategic_insights: Optional[List[Dict[str, Any]]] = None
    beginner_guide: Optional[BeginnerGuide] = None
    team_data: Optional[List[PokemonInfo]] = None
    error: Optional[str] = None
