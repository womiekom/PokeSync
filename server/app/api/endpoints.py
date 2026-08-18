from fastapi import APIRouter, HTTPException, Depends
from app.api.schemas import TeamRequest, PredictionResponse, SynergyResponse
from app.ml.model import ArchetypeModel, explain_prediction
from app.ml.data_loader import load_and_clean_data
from app.ml.synergy import analyze_team_synergy
from app.core.config import settings
from app.core.utils import get_pokemon_data
import os

router = APIRouter()

# Global variables for model and data
model = None
df_pokemon = None
df_types = None

def get_model_and_data():
    global model, df_pokemon, df_types
    if model is None or df_pokemon is None or df_types is None:
        if not os.path.exists(settings.MODEL_PATH):
            raise HTTPException(status_code=500, detail="Model files not found. Please train the model first.")
        
        df_pokemon, df_types = load_and_clean_data(settings.POKEMON_CSV, settings.TYPES_CSV)
        model = ArchetypeModel(settings.MODEL_PATH, settings.ENCODER_PATH)
    return model, df_pokemon, df_types

@router.post("/predict", response_model=PredictionResponse)
async def predict(request: TeamRequest):
    current_model, current_df, _ = get_model_and_data()
    
    team = request.team
    if len(team) != 6:
        return PredictionResponse(success=False, error="Team must contain exactly 6 Pokémon.")
    
    # Basic validation
    valid_names = set(current_df["name"])
    normalized_team = [p.lower().replace(" ", "-") for p in team]
    invalid = [p for p in normalized_team if p not in valid_names]
    
    if invalid:
        return PredictionResponse(success=False, error=f"Invalid Pokémon: {invalid}")
    
    if len(set(normalized_team)) != 6:
        return PredictionResponse(success=False, error="Duplicate Pokémon detected.")

    # Prediction
    result = current_model.predict(normalized_team, current_df)
    if result is None:
        return PredictionResponse(success=False, error="Feature extraction failed.")
    
    explanations = explain_prediction(normalized_team, result["features"])
    team_data = get_pokemon_data(normalized_team, current_df)
    
    return PredictionResponse(
        success=True,
        prediction=result["prediction"],
        probabilities=result["probabilities"],
        explanations=explanations,
        team_data=team_data
    )

@router.post("/synergy", response_model=SynergyResponse)
async def synergy(request: TeamRequest):
    _, current_df, current_types = get_model_and_data()
    
    team = request.team
    if len(team) != 6:
        return SynergyResponse(success=False, error="Team must contain exactly 6 Pokémon.")
        
    valid_names = set(current_df["name"])
    normalized_team = [p.lower().replace(" ", "-") for p in team]
    invalid = [p for p in normalized_team if p not in valid_names]
    
    if invalid:
        return SynergyResponse(success=False, error=f"Invalid Pokémon: {invalid}")
        
    if len(set(normalized_team)) != 6:
        return SynergyResponse(success=False, error="Duplicate Pokémon detected.")
        
    synergy_data = analyze_team_synergy(normalized_team, current_df, current_types)
    if synergy_data is None:
        return SynergyResponse(success=False, error="Synergy calculation failed.")
        
    team_data = get_pokemon_data(normalized_team, current_df)
    synergy_data["team_data"] = team_data
    
    return SynergyResponse(**synergy_data)

@router.get("/pokemon")
async def list_pokemon():
    _, current_df, _ = get_model_and_data()
    return {"pokemon": sorted(current_df["name"].tolist())}
