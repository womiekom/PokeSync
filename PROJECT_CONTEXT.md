# PokeSync — Project Context

> **Last Updated**: 2026-08-25
> **Status**: Phase 2 Complete · Phase 3 Planned
> **Repository**: `PokeSync/`

---

## 1. Project Overview

PokeSync is an interactive competitive Pokémon team analysis assistant. It combines a trained **Random Forest** ML model with rule-based competitive domain heuristics to:

1. **Predict team archetypes** — classify a 6-Pokémon team's strategic playstyle across 8 categories.
2. **Analyze team synergy** — evaluate defensive type coverage, offensive balance, speed tier distribution, and strategic cohesion (weather/Trick Room).
3. **Explain results** — provide beginner-friendly, human-readable rationales for both predictions and synergy evaluations.

The application targets **competitive Pokémon players** and curious newcomers who want to understand their team's strategic identity and structural strengths/weaknesses.

### What PokeSync is NOT (currently)

- It does **not** recommend individual movesets.
- It does **not** suggest team replacements or optimizations.
- It does **not** provide EV spread, item, or ability recommendations.
- It does **not** use large language models or generative AI.

---

## 2. Current User Flow

```
User opens client/index.html
    │
    ▼
Team Roster Input (search + autocomplete, 6 slots)
    │  ── Pokémon images & type badges fetched from PokeAPI
    │
    ▼
Analysis Hub (choose one of four cards)
    │
    ├── ✅ Archetype Predictor   → POST /api/predict
    │       └── Results: predicted archetype, confidence distribution,
    │           strategic rationale, archetype icon
    │
    ├── ✅ Team Synergy Engine    → POST /api/synergy
    │       └── Results: overall score (0-96), defensive/offensive/strategic
    │           sub-scores, key strengths, gaps, elemental defense matrix,
    │           damage split, speed tiers, STAB coverage
    │
    ├── 🔒 Moveset Recommender   → PHASE 3 ROADMAP (disabled placeholder)
    │
    └── 🔒 Team Optimizer        → PHASE 3 ROADMAP (disabled placeholder)
```

**Key UX details:**
- Analysis overlay with animated Poké Ball scanning sequence plays during API calls.
- Results appear in a tabbed view (Archetype Prediction | Team Synergy).
- Both analysis types can be run independently; results persist in their respective tabs.

---

## 3. Current Features

### 3.1 Archetype Predictor ✅ IMPLEMENTED

| Aspect | Detail |
|--------|--------|
| **Purpose** | Predict team's competitive archetype (Rain, Sun, Sand, Snow, Trick Room, Hyper Offense, Stall, Balance) |
| **User Input** | 6 Pokémon names |
| **Output** | Predicted archetype label, probability distribution across all 8 classes, strategic alignment percentage, strategic rationale explanations |
| **Frontend** | `index.html` (lines 158-191): prediction header, archetype icon, alignment meter, explanation list, probability chart |
| **Backend API** | `POST /api/predict` → `server/app/api/endpoints.py` |
| **ML Model** | `RandomForestClassifier` (300 trees, max_depth=12) → `server/app/ml/model.py` |
| **Feature Engineering** | `extract_team_features()` → `server/app/ml/feature_engineering.py` |
| **Explanation** | `explain_prediction()` (rule-based) → `server/app/ml/model.py` (lines 70-87) |
| **Training Data** | Synthetically generated teams → `server/app/ml/generators.py` |
| **Trained Artifact** | `server/models/archetype_model.joblib` + `server/models/model_meta.joblib` |

### 3.2 Team Synergy Engine ✅ IMPLEMENTED

| Aspect | Detail |
|--------|--------|
| **Purpose** | Multi-dimensional team synergy evaluation |
| **User Input** | 6 Pokémon names |
| **Output** | Overall synergy score (20-96), rating (Strong/Moderate/Needs Attention), defensive/offensive/strategic sub-scores, key strengths list, gaps list, 18-type defensive matchup matrix, offensive profile, strategic insights, beginner guide |
| **Frontend** | `index.html` (lines 193-336): Poké Ball score dial, sub-score bars, strengths/gaps grid, elemental defense matrix, offensive profile breakdown |
| **Backend API** | `POST /api/synergy` → `server/app/api/endpoints.py` |
| **Algorithm** | Entirely **rule-based/deterministic** → `server/app/ml/synergy.py` (423 lines) |
| **Scoring** | Weighted composite: 35% defensive + 35% offensive + 30% strategic |
| **Data Source** | `pokemon_complete.csv` (stats, types, abilities) + `pokemon_types.csv` (type effectiveness chart) |

**Synergy sub-analyses:**
- **Defensive**: Dual-type multiplier matrix across 18 types, severe/moderate weakness detection, resistance/immunity counting
- **Offensive**: Physical vs. Special attacker balance, speed tier distribution (Fast 100+, Mid 65-99, Slow ≤60), STAB coverage count
- **Strategic**: Weather setter/abuser detection (Rain, Sun, Sand, Snow), Trick Room setter/abuser detection, Stall core detection, Hyper Offense momentum detection

### 3.3 Pokémon Autocomplete ✅ IMPLEMENTED

| Aspect | Detail |
|--------|--------|
| **Purpose** | Provide searchable Pokémon name list for team building |
| **Backend API** | `GET /api/pokemon` → returns sorted name list |
| **Frontend** | Keyboard-navigable dropdown with arrow keys and Enter selection |

### 3.4 Pokémon Image & Type Display ✅ IMPLEMENTED

| Aspect | Detail |
|--------|--------|
| **Purpose** | Display official artwork and type badges for selected Pokémon |
| **External API** | `https://pokeapi.co/api/v2/pokemon/{name}` (client-side fetch) |
| **Backend Alternative** | `get_sugimori_url()` in `server/app/core/utils.py` (uses PokeAPI sprites GitHub raw URL) |

### 3.5 Moveset Recommender 🔒 PLANNED (Phase 3)

Present only as a disabled UI card in `index.html` (lines 113-127) with `coming-soon-card` CSS class. No backend implementation exists.

### 3.6 Team Optimizer 🔒 PLANNED (Phase 3)

Present only as a disabled UI card in `index.html` (lines 129-143) with `coming-soon-card` CSS class. No backend implementation exists.

---

## 4. Current ML / Algorithmic Systems

### 4.1 Archetype Prediction (ML)

| Component | Type | File |
|-----------|------|------|
| Model | `RandomForestClassifier` (scikit-learn) | `server/app/ml/model.py` |
| Features | 30+ engineered features from team stats/abilities | `server/app/ml/feature_engineering.py` |
| Training Data | Synthetic team generation (500 samples × 8 archetypes) | `server/app/ml/generators.py` |
| Training Script | Data loading → synthetic generation → train → save | `server/train_model.py` |
| Serialization | Joblib (model + LabelEncoder + feature names) | `server/models/` |
| Explanation | Rule-based threshold checks on features | `server/app/ml/model.py` `explain_prediction()` |

**Engineered Features** (from `extract_team_features()`):
- Average base stats (HP, Atk, Def, SpA, SpD, Spe, BST)
- Bulk aggregates (avg_bulk, bulky_count, very_bulky_count, frail_count, bulk_variance)
- Speed brackets (fast_count, slow_count, very_slow_count, speed_variance)
- Attacker profile (physical_attackers, special_attackers, mixed_attackers)
- Balance metrics (offense_balance, defense_balance)
- Weather synergy scores (setter_count × 3 + abuser_count) for Rain, Sun, Sand, Snow
- Trick Room synergy (setter_count × 3 + abuser_count)
- Composite scores (stall_score, hyper_offense_score, balance_score)

### 4.2 Team Synergy Analysis (Deterministic)

| Component | Type | File |
|-----------|------|------|
| Type Chart | Built from `pokemon_types.csv` at runtime | `server/app/ml/synergy.py` `build_type_chart()` |
| Defensive Analysis | Dual-type multiplier calculation per attacking type | `synergy.py` lines 66-134 |
| Offensive Analysis | Stat-based attacker split + STAB coverage | `synergy.py` lines 153-200 |
| Strategic Analysis | Ability-based weather/TR detection + bulk/speed role checks | `synergy.py` lines 202-279 |
| Scoring | Weighted composite with clamped range [20, 96] | `synergy.py` lines 282-297 |
| Strengths/Gaps | Rule-based compilation of significant findings | `synergy.py` lines 300-387 |

### 4.3 Strategy Definitions (Static Data)

| Component | Detail | File |
|-----------|--------|------|
| Weather Abilities | Drizzle, Drought, Sand Stream, Snow Warning | `server/app/ml/strategies.py` |
| Weather Abusers | Swift Swim, Chlorophyll, Protosynthesis, Sand Rush, Sand Force, Slush Rush | `strategies.py` |
| Trick Room Setters | Hatterene, Cresselia, Porygon2, Bronzong, Mimikyu, Indeedee-F, Farigiraf | `strategies.py` |
| Trick Room Abusers | Ursaluna, Amoonguss, Iron Hands, Hariyama, Slowking, Clodsire | `strategies.py` |

> **Note**: The `strategies.py` definitions are manually curated and do not cover all possible setters/abusers. They focus on common competitive picks.

---

## 5. Current Technical Architecture

```
┌─────────────────────────────────────────────────┐
│                  FRONTEND                        │
│  Vanilla HTML5 / CSS3 / JavaScript (ES6+)        │
│  Single page: index.html + main.js + style.css   │
│  No build tools, no npm, no framework            │
│  External: PokeAPI (images/types, client-side)    │
└────────────────┬────────────────────────────────┘
                 │ HTTP (localhost:8000/api)
                 ▼
┌─────────────────────────────────────────────────┐
│                  BACKEND                         │
│  Python 3.9+ / FastAPI / Uvicorn                 │
│  Pydantic schemas for request/response           │
│  CORS: allow all origins                         │
└───────┬─────────────────┬───────────────────────┘
        │                 │
        ▼                 ▼
┌───────────────┐  ┌──────────────────────────────┐
│   ML LAYER    │  │      DATA LAYER              │
│ RandomForest  │  │ pokemon_complete.csv (1351)   │
│ scikit-learn  │  │ pokemon_types.csv (18 types)  │
│ Joblib models │  │ Loaded via pandas             │
└───────────────┘  └──────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Frontend** | HTML5, CSS3, Vanilla JS (ES6+) | No npm, no build step, served as static files |
| **Backend** | Python 3.9+, FastAPI, Uvicorn | Single process, CORS enabled |
| **ML** | scikit-learn (RandomForestClassifier), pandas, joblib | Pre-trained model loaded at startup |
| **Data** | CSV files (pandas DataFrames) | Loaded once, cached in global variables |
| **External API** | PokeAPI v2 | Client-side only (artwork + types) |
| **Database** | None | No persistent storage |
| **Deployment** | Local development only | `localhost:8000` backend, static file serving for frontend |

### Dependencies (`server/requirements.txt`)

- fastapi
- uvicorn
- pandas
- scikit-learn
- joblib
- pydantic
- python-multipart

---

## 6. Phase History

### Phase 1 — Archetype Predictor ✅ COMPLETE

**What was built:**
- Random Forest model training pipeline (synthetic data generation → feature engineering → training → serialization)
- `/api/predict` endpoint with full request/response schemas
- Rule-based explanation system for predictions
- Frontend: team input builder with autocomplete, archetype prediction results view with icon, alignment meter, probability chart, strategic rationale

### Phase 2 — Team Synergy Engine ✅ COMPLETE

**What was built:**
- Comprehensive rule-based synergy analysis system (`synergy.py`, 423 lines)
- `/api/synergy` endpoint with structured response schema
- Frontend: Poké Ball score dial, sub-score progress bars, strengths/gaps cards, 18-type elemental defense matrix, offensive profile breakdown (damage split, speed tiers, STAB coverage)
- Analysis Hub with 4-card selection grid (2 active, 2 disabled roadmap placeholders)
- Animated analysis overlay with Poké Ball scanning sequence
- Tab-based results navigation between Archetype and Synergy views

---

## 7. Phase 3 Goal

> **Status: PLANNED — NOT YET IMPLEMENTED**

### 7.1 Moveset Recommender

Given context about a Pokémon, its team, and the team's archetype/role, recommend strategically appropriate competitive moves.

**Placeholder in UI**: `index.html` line 120 — "Suggest optimal competitive movesets, items, and EV spreads tailored to your team's archetype."

### 7.2 Team Optimizer

Given a 6-Pokémon team, identify structural weaknesses/gaps and suggest possible Pokémon replacements to improve the team.

**Placeholder in UI**: `index.html` line 137 — "Discover alternative Pokémon replacements to patch severe defensive holes and expand offensive coverage."

### Important Phase 3 Notes

- **No implementation exists** for either feature in the current codebase.
- The existing **synergy analysis** provides a natural foundation for Team Optimizer (it already identifies gaps).
- The existing **archetype prediction** provides team context useful for moveset recommendations.
- The current dataset (`pokemon_complete.csv`) contains stats, types, and abilities but **does NOT contain move/learnset data**.
- **No competitive usage data** (Smogon sets, moveset frequencies, teammate frequencies) exists in the repository.
- Phase 3 will require **new data sources** not currently present.
