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

# ==========================================
# PHASE 3 SCHEMAS: RECOMMENDER & OPTIMIZER
# ==========================================

class MovesetRequest(BaseModel):
    pokemon: str
    ability: Optional[str] = ""
    item: Optional[str] = ""
    team: Optional[List[str]] = None
    archetype: Optional[str] = "balance"
    format: Optional[str] = "gen9ou"

class RecommendedMove(BaseModel):
    id: str
    name: str
    type: str
    category: str
    power: int
    accuracy: Any
    priority: int
    score: float
    role_tag: str
    rationale: str

class MovesetResponse(BaseModel):
    success: bool
    pokemon: Optional[str] = None
    types: Optional[List[str]] = None
    format: Optional[str] = None
    archetype: Optional[str] = None
    recommended_moves: Optional[List[RecommendedMove]] = None
    recommended_tera_types: Optional[List[str]] = None
    recommended_items: Optional[List[str]] = None
    archetype_fit_summary: Optional[str] = None
    error: Optional[str] = None

class OptimizeRequest(BaseModel):
    team: List[str]
    format: Optional[str] = "gen9ou"
    target_archetype: Optional[str] = None

class TeamReplacementSuggestion(BaseModel):
    remove_pokemon: str
    remove_pokemon_raw: str
    add_pokemon: str
    add_pokemon_raw: str
    add_pokemon_data: Optional[PokemonInfo] = None
    score_delta: int
    new_score: int
    improved_matchups: List[str]
    rationale: str

class OptimizeResponse(BaseModel):
    success: bool
    format: Optional[str] = None
    baseline_score: Optional[int] = None
    baseline_synergy: Optional[Dict[str, Any]] = None
    gaps_detected: Optional[List[Dict[str, Any]]] = None
    suggestions: Optional[List[TeamReplacementSuggestion]] = None
    team_data: Optional[List[PokemonInfo]] = None
    error: Optional[str] = None
