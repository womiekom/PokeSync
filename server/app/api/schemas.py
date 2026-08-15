
from pydantic import BaseModel
from typing import List, Dict

class TeamRequest(BaseModel):
    team: List[str]

class PokemonInfo(BaseModel):
    name: str
    pokedex_number: int
    image_url: str
    types: List[str]

class PredictionResponse(BaseModel):
    success: bool
    prediction: str = None
    probabilities: Dict[str, float] = None
    explanations: List[str] = None
    team_data: List[PokemonInfo] = None
    error: str = None
