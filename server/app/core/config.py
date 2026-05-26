
import os

class Settings:
    PROJECT_NAME: str = "PokeSync API"
    PROJECT_VERSION: str = "1.0.0"
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATASETS_DIR = os.path.join(BASE_DIR, "..", "datasets")
    MODELS_DIR = os.path.join(BASE_DIR, "models")
    
    POKEMON_CSV = os.path.join(DATASETS_DIR, "pokemon_complete.csv")
    TYPES_CSV = os.path.join(DATASETS_DIR, "pokemon_types.csv")
    
    MODEL_PATH = os.path.join(MODELS_DIR, "archetype_model.joblib")
    ENCODER_PATH = os.path.join(MODELS_DIR, "model_meta.joblib")

settings = Settings()
