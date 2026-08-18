# PokeSync 🐾

PokeSync is a friendly, interactive competitive Pokémon team analysis assistant and platform. It combines Machine Learning (Random Forest) and deep competitive domain heuristics to analyze 6-Pokémon team compositions, predict their strategic archetypes, and evaluate comprehensive team synergy (defensive type matchups, speed control, attacker splits, and weather/Trick Room teamwork).

---

## Key Features

### 🔮 1. Archetype Predictor
- Uses a trained **RandomForestClassifier** to predict a team's core competitive archetype across 8 classes: *Rain*, *Sun*, *Sand*, *Snow*, *Trick Room*, *Hyper Offense*, *Stall*, and *Balance*.
- Calculates strategic alignment percentages and confidence distributions across all archetypes.
- Generates human-readable strategic rationales based on team stat variance and ability signatures.

### 🧩 2. Team Synergy Engine
- **Defensive Type Matrix**: Evaluates dual-type defensive multipliers across all 18 elemental types, flagging severe shared weaknesses and celebrating defensive resistance cores/immunities.
- **Offensive & Speed Tiers**: Analyzes Physical vs. Special attacker balance to prevent wall vulnerabilities, and maps speed distribution across Fast, Mid, and Slow tiers.
- **Strategic Cohesion**: Detects active weather synergies (setters + abusers) and Trick Room setups.
- **Beginner-Friendly Callouts**: Displays overall synergy scores (Strong / Moderate / Needs Attention) alongside actionable key strengths and critical vulnerability gap cards.

### 🎮 3. Retro Pokémon-Inspired Interface
- Authentic Pokémon aesthetic with custom FRLG typography, type badges, archetype vector icons, animated Poké Ball scanning sequence, and responsive layout.
- High-quality Sugimori-style dynamic artwork fetched directly from PokeAPI.

---

## Tech Stack

- **Backend**: Python 3.9+, FastAPI, Uvicorn
- **ML & Data Analysis**: Scikit-learn, Pandas, Joblib
- **Frontend**: Vanilla HTML5, Modern Responsive CSS3, JavaScript (ES6+)
- **External Integration**: PokeAPI (Official Artwork & Elemental Types)

---

## Project Structure

```text
PokeSync/
├── datasets/           # Raw Pokémon datasets (pokemon_complete.csv, pokemon_types.csv)
├── notebook/           # Original exploratory analysis and ML prototyping
├── scripts/            # Integration test scripts (test_endpoints.py, test_synergy.py)
├── server/             # FastAPI Backend
│   ├── app/
│   │   ├── api/        # API Endpoints (endpoints.py) & Pydantic Schemas (schemas.py)
│   │   ├── core/       # Configuration (config.py) & Utilities (utils.py)
│   │   ├── ml/         # ML Pipeline (data_loader, feature_engineering, generators, model, synergy)
│   │   └── main.py     # FastAPI Server Entry Point
│   ├── models/         # Serialized model artifacts (.joblib)
│   ├── train_model.py  # Model training orchestration script
│   └── requirements.txt
├── client/             # Frontend Application
│   ├── assets/         # Fonts, type badges, archetype SVGs, background motifs
│   ├── index.html      # Analysis Hub & Team Builder Layout
│   ├── main.js         # State management, API integration, and rendering
│   └── style.css       # Design tokens, responsive grid, and keyframe animations
└── README.md
```

---

## Installation & Setup

### Prerequisites
- Python 3.9+

### Running the Backend

1. **Navigate to the server directory**:
   ```bash
   cd server
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Train the ML model** (Optional — pre-trained model is included):
   ```bash
   python train_model.py
   ```

4. **Run the API server**:
   ```bash
   python -m app.main
   ```
   The API server will run at `http://localhost:8000`.

### Running the Frontend
Open `client/index.html` in any modern web browser or serve it via a local static web server (e.g. `npx serve client` or Python `python -m http.server 3000 --directory client`).

---

## API Endpoints

### 1. `POST /api/predict`
Predicts the strategic archetype and confidence distribution of a 6-Pokémon team.

**Request:**
```json
{
  "team": ["Toxapex", "Blissey", "Corviknight", "Clodsire", "Dondozo", "Alomomola"]
}
```

**Response:**
```json
{
  "success": true,
  "prediction": "stall",
  "probabilities": { "stall": 0.394, "balance": 0.28, ... },
  "explanations": ["High defensive/stall presence detected."],
  "team_data": [ ... ]
}
```

### 2. `POST /api/synergy`
Computes multi-dimensional defensive, offensive, and strategic team synergy.

**Request:**
```json
{
  "team": ["Pelipper", "Barraskewda", "Kingdra", "Ludicolo", "Zapdos", "Ferrothorn"]
}
```

**Response:**
```json
{
  "success": true,
  "overall": {
    "score": 92,
    "rating": "Strong",
    "rating_color": "success",
    "summary": "Your team has clear strategic cohesion, good balance, and well-covered roles.",
    "defensive_score": 96,
    "offensive_score": 93,
    "strategic_score": 86
  },
  "strengths": [
    { "title": "Strong Rain Synergy", "description": "Pelipper sets Rain, which directly activates Kingdra, Ludicolo, Barraskewda.", "tag": "Strategy" }
  ],
  "gaps": [
    { "title": "No Critical Overlapping Weaknesses", "description": "Team weaknesses are well-distributed...", "severity": "success", "tag": "Well-Covered" }
  ],
  "type_matchups": { ... },
  "offensive_profile": { "physical_attackers": 2, "special_attackers": 3, "fast_count": 2, ... }
}
```

### 3. `GET /api/pokemon`
Returns the alphabetically sorted list of valid Pokémon names for autocomplete.
