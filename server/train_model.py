
import os
import sys

# Add the current directory to sys.path to allow relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ml.data_loader import load_and_clean_data
from app.ml.generators import build_dataset
from app.ml.model import ArchetypeModel
from app.core.config import settings

def main():
    print("--- PokeSync Model Training ---")
    
    # Ensure models directory exists
    os.makedirs(settings.MODELS_DIR, exist_ok=True)
    
    print(f"Loading data from {settings.POKEMON_CSV}...")
    df_pokemon, _ = load_and_clean_data(settings.POKEMON_CSV, settings.TYPES_CSV)
    
    print("Generating training dataset (this may take a minute)...")
    X, y = build_dataset(df_pokemon, samples_per_class=500)
    
    print("Training model...")
    model = ArchetypeModel()
    model.train(X, y)
    
    print(f"Saving model to {settings.MODELS_DIR}...")
    model.save(settings.MODEL_PATH, settings.ENCODER_PATH)
    
    print("Training complete!")

if __name__ == "__main__":
    main()
