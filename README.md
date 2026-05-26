# PokeSync 🐾

PokeSync is a Pokémon competitive team archetype prediction web app. It uses Machine Learning (Random Forest) to analyze Pokémon team compositions and predict their strategic archetypes (e.g., Rain, Sun, Stall, Hyper Offense, etc.).

## Features

- **Archetype Prediction**: Predicts the strategic archetype of a 6-Pokémon team.
- **Detailed Explanations**: Provides reasoning for why a specific archetype was predicted based on team synergy and stats.
- **Probability Breakdown**: Shows the confidence level for all supported archetypes.
- **Official Artwork Integration**: Returns high-quality Sugimori-style artwork URLs directly from PokeAPI.
- **Modular Backend**: Production-ready FastAPI architecture with separate modules for ML, API, and core logic.

## Tech Stack

- **Backend**: Python, FastAPI
- **ML Model**: Scikit-learn (RandomForestClassifier)
- **Data Processing**: Pandas
- **Serialization**: Joblib
- **Frontend**: Next.js (Planned)

## Project Structure

```text
PokeSync/
├── datasets/           # Raw Pokémon datasets (CSV)
├── notebook/           # Original research and ML prototyping
├── server/             # FastAPI Backend
│   ├── app/
│   │   ├── api/        # API Routes and Schemas
│   │   ├── core/       # Config and Utilities
│   │   ├── ml/         # ML Logic (Loading, Feature Engineering, Prediction)
│   │   └── main.py     # Application Entry Point
│   ├── models/         # Saved model and metadata (.joblib)
│   ├── train_model.py  # Script to retrain the model
│   └── requirements.txt
└── README.md
```

## Installation & Setup

### Prerequisites

- Python 3.9+
- Node.js (for future frontend)

### Backend Setup

1. **Navigate to the server directory**:

   ```bash
   cd server
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Train the model** (Optional - a pre-trained model is included):

   ```bash
   python train_model.py
   ```

4. **Run the API server**:
   ```bash
   python -m app.main
   ```
   The API will be available at `http://localhost:8000`.

## API Endpoints

### `POST /api/predict`

Predicts the archetype of a Pokémon team.

**Request Body:**

```json
{
  "team": [
    "Toxapex",
    "Blissey",
    "Corviknight",
    "Clodsire",
    "Dondozo",
    "Alomomola"
  ]
}
```

**Response:**

```json
{
  "success": true,
  "prediction": "stall",
  "probabilities": { ... },
  "explanations": ["High defensive/stall presence detected."],
  "team_data": [ ... ]
}
```

### `GET /api/pokemon`

Returns a list of all valid Pokémon names for the prediction system.

---

## Design Vision

PokeSync aims for a modern, clean aesthetic inspired by official Pokémon Sugimori-style artwork. The UI will prioritize visual feedback, showing team synergy scores and archetype probabilities in a polished, interactive interface.
