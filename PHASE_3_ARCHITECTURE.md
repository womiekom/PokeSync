# PokeSync — Phase 3 Architecture

> **Last Updated**: 2026-08-25
> **Status**: PROPOSED — NOT YET IMPLEMENTED
> **Prerequisites**: Phase 1 (Archetype Predictor) ✅ · Phase 2 (Team Synergy Engine) ✅

---

## 1. Phase 3 Objectives

### A. Moveset Recommender (PROPOSED)

**Goal**: Given contextual information about a Pokémon and its team, recommend strategically appropriate competitive moves.

**Input Context** (proposed):
- Pokémon name
- Pokémon ability (if specified)
- Team composition (6 Pokémon)
- Team archetype (from existing predictor)
- Role within the team (attacker, wall, support, etc.)
- Possibly existing moves already chosen

**Output** (proposed):
- Ranked list of recommended moves
- For each move: name, type, category (Physical/Special/Status), reasoning
- Optionally: suggested item, nature, EV emphasis

### B. Team Optimizer (PROPOSED)

**Goal**: Given a 6-Pokémon team, identify structural weaknesses and suggest specific Pokémon replacements to improve the team.

**Input Context** (proposed):
- Current 6-Pokémon team
- Existing synergy analysis results (from Phase 2)
- Optionally: user-specified constraints ("keep these 3 Pokémon")

**Output** (proposed):
- List of identified gaps/weaknesses (partially available from existing synergy analysis)
- For each gap: suggested replacement Pokémon with reasoning
- Before/after synergy score comparison

---

## 2. Proposed Hybrid Architecture

Phase 3 should follow a **hybrid deterministic + ML** architecture, similar to the existing Phase 1/2 pattern. The key insight is: **not everything needs ML**. Deterministic constraints should filter the solution space before ML models rank candidates.

### Layer 1 — Deterministic Constraints

Hard constraints that must be enforced regardless of ML output:

| Constraint | Description | Data Required |
|-----------|-------------|---------------|
| **Legal Learnset** | A Pokémon can only learn certain moves | Learnset data (NOT in current repo) |
| **Pokémon Typing / STAB** | Same-type attack bonus should be considered | `pokemon_complete.csv` (types available) |
| **Move Category / Stat Alignment** | Physical moves should match high Attack, Special moves should match high Sp.Atk | Stats from `pokemon_complete.csv` + move data |
| **Move Accuracy** | Moves with very low accuracy are risky | Move data (NOT in current repo) |
| **Ability Compatibility** | Some moves synergize with or require specific abilities | Ability + move interaction data |
| **Type Coverage** | Moves should not redundantly cover the same types | Type chart from `pokemon_types.csv` |

> **⚠ IMPORTANT**: The current repository does NOT contain learnset data or a move database. These are **critical prerequisites** for the Moveset Recommender.

### Layer 2 — Strategic Context

Contextual signals that should influence recommendations:

| Context | Description | Source |
|---------|-------------|--------|
| **Team Archetype** | Rain teams need Water/rain-abusing moves; Trick Room teams need different priorities | Existing Archetype Predictor |
| **Role on Team** | A designated wall needs recovery/status moves; a sweeper needs coverage moves | Needs role classification (partially possible from stats) |
| **Team Weaknesses** | If the team is weak to Ground, a Pokémon that can learn Ice Beam helps coverage | Existing Synergy Analysis |
| **Existing Moves** | If 3/4 moves are already chosen, the 4th should complement them | User input |
| **Speed Tier** | Fast Pokémon benefit from different move profiles than slow Pokémon | Stats from `pokemon_complete.csv` |
| **Weather/Terrain** | Weather-dependent moves gain priority in weather teams | Existing `strategies.py` definitions |

### Layer 3 — ML / Ranking (PROPOSED)

Potential ML approaches for ranking candidate moves or Pokémon:

| Approach | Description | Viability | Notes |
|----------|-------------|-----------|-------|
| **Learning-to-Rank** | Train a model to rank moves by competitive viability given context | Promising | Requires training data of competitive moveset choices |
| **Collaborative Filtering** | "Pokémon X with ability Y commonly uses moves A, B, C, D" | Promising | Requires competitive usage data |
| **Random Forest Scorer** | Extend existing RF approach to score move candidates | Feasible | Consistent with current architecture |
| **Embeddings** | Learn vector representations of Pokémon/moves/types for similarity | Ambitious | May be overkill for current scope |
| **Neural Ranker** | Deep learning model for contextual ranking | Ambitious | Requires significant data and adds complexity |

> **PROPOSED**: Start with a **deterministic scoring system** augmented by **competitive usage statistics** (collaborative filtering). ML ranking can be added later if sufficient training data is available.

### Layer 4 — Team Optimization (PROPOSED)

Potential optimization approaches:

| Approach | Description | Viability | Notes |
|----------|-------------|-----------|-------|
| **Greedy Replacement** | For each identified gap, find the single best replacement | Simplest | May miss synergistic multi-replacements |
| **Beam Search** | Explore top-K replacement candidates at each position | Moderate | Better than greedy, manageable complexity |
| **Genetic Algorithm** | Evolve team compositions through crossover/mutation | Ambitious | Complex, potentially slow, hard to explain |
| **Constraint Satisfaction** | Frame as CSP with type coverage, role balance constraints | Moderate | Explainable, deterministic |

> **PROPOSED**: Start with **Greedy Replacement** backed by the existing synergy scoring system. A replacement candidate is evaluated by computing the synergy delta (score after replacement minus score before).

---

## 3. Existing Components We Can Reuse

### 3.1 Archetype Predictor → Team Context

| Component | File | Reuse |
|-----------|------|-------|
| `ArchetypeModel.predict()` | `server/app/ml/model.py` | Provides team archetype context for moveset recommendations |
| `extract_team_features()` | `server/app/ml/feature_engineering.py` | Feature extraction can be extended for Phase 3 features |
| `explain_prediction()` | `server/app/ml/model.py` | Pattern for generating explanations can be reused |
| `STRATEGIES` | `server/app/ml/strategies.py` | Weather/TR ability definitions useful for contextual recommendations |

### 3.2 Team Synergy Analyzer → Gap Identification

| Component | File | Reuse |
|-----------|------|-------|
| `analyze_team_synergy()` | `server/app/ml/synergy.py` | **Directly reusable** for identifying team gaps that the optimizer should address |
| `build_type_chart()` | `server/app/ml/synergy.py` | Type effectiveness calculations needed for move/coverage analysis |
| `get_pokemon_type_multiplier()` | `server/app/ml/synergy.py` | Dual-type damage calculation |
| Defensive analysis | `synergy.py` lines 66-134 | Identifies severe/moderate type weaknesses |
| Offensive analysis | `synergy.py` lines 153-200 | Attacker balance and STAB coverage |
| Strategic analysis | `synergy.py` lines 202-279 | Weather/TR/role cohesion detection |
| Strengths/Gaps compilation | `synergy.py` lines 300-387 | Gap identification directly feeds optimizer |

### 3.3 Data Layer

| Component | File | Reuse |
|-----------|------|-------|
| `load_and_clean_data()` | `server/app/ml/data_loader.py` | Data loading pipeline can be extended for new datasets |
| `pokemon_complete.csv` | `datasets/` | Pokémon stats, types, abilities (Gen I-IX, 1351 entries) |
| `pokemon_types.csv` | `datasets/` | Type effectiveness chart (18 types) |

### 3.4 API Layer

| Component | File | Reuse |
|-----------|------|-------|
| `TeamRequest` schema | `server/app/api/schemas.py` | Existing request format for team input |
| `PokemonInfo` schema | `server/app/api/schemas.py` | Pokemon data response format |
| Endpoint patterns | `server/app/api/endpoints.py` | Pattern for new `/api/moveset` and `/api/optimize` endpoints |
| `get_pokemon_data()` | `server/app/core/utils.py` | Pokémon info formatting for responses |

### 3.5 Frontend

| Component | Location | Reuse |
|-----------|----------|-------|
| Hub card grid | `index.html` lines 80-144 | Existing placeholders for Phase 3 cards |
| Tab bar | `index.html` lines 150-156 | New tabs for Phase 3 results |
| Analysis overlay | `index.html` lines 22-37, `main.js` | Animated loading sequence |
| `.card` / `.card-inner` CSS | `style.css` | Result display containers |
| Score displays | `style.css` | Sub-score bars, badges, rating tags |

---

## 4. Moveset Recommendation Data Flow (PROPOSED)

```
User Context
│  Pokémon name + team composition
│  (optionally: ability, existing moves, role)
│
▼
┌─────────────────────────────────────────────┐
│ 1. TEAM CONTEXT ENRICHMENT                  │
│    • Run archetype predictor on team         │
│    • Run synergy analyzer on team            │
│    • Identify team gaps and role needs        │
│    Source: existing model.py + synergy.py     │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ 2. LEGAL MOVE FILTERING                     │
│    • Filter to moves the Pokémon can learn   │
│    • Requires: learnset data (NEW DATA)      │
│    • Output: candidate move pool             │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ 3. FEATURE EXTRACTION                        │
│    • For each candidate move, compute:       │
│      - STAB bonus?                           │
│      - Category alignment (Phys/Spec)?       │
│      - Type coverage contribution?           │
│      - Team gap coverage?                    │
│      - Archetype relevance?                  │
│      - Competitive usage frequency?          │
│    • Requires: move database (NEW DATA)      │
│    • Requires: competitive data (NEW DATA)   │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ 4. CANDIDATE RANKING                         │
│    • Score each candidate move               │
│    • Method: deterministic scoring +         │
│      competitive usage weighting             │
│    • OR: ML ranker if training data exists   │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ 5. TOP MOVE RECOMMENDATIONS                 │
│    • Return top N moves with scores          │
│    • Include explanation per move            │
│    • Format: ranked list with reasoning      │
└─────────────────────────────────────────────┘
```

---

## 5. Team Optimization Data Flow (PROPOSED)

```
Current 6-Pokémon Team
│
▼
┌─────────────────────────────────────────────┐
│ 1. TEAM ANALYSIS (EXISTING)                  │
│    • Run synergy analyzer                    │
│    • Run archetype predictor                 │
│    • Identify: severe weaknesses, gaps,      │
│      missing coverage, role imbalances       │
│    Source: existing synergy.py + model.py     │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ 2. GAP PRIORITIZATION                        │
│    • Rank identified gaps by severity         │
│    • Types: defensive holes, speed gaps,      │
│      attacker imbalance, coverage gaps        │
│    • User constraints: "keep these Pokémon"   │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ 3. CANDIDATE GENERATION                      │
│    • For each replaceable team slot:          │
│      - Query Pokémon pool that addresses gaps │
│      - Filter by type, stats, abilities       │
│    • Data: pokemon_complete.csv (existing)    │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ 4. CANDIDATE EVALUATION                      │
│    • For each candidate replacement:          │
│      - Compute new team synergy score         │
│      - Compute synergy delta                  │
│      - Check if gaps are addressed            │
│    Source: existing synergy.py                 │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ 5. RANKING & EXPLANATION                     │
│    • Rank candidates by synergy improvement   │
│    • Generate explanation for each suggestion  │
│    • Before/after comparison                   │
└─────────────────────────────────────────────┘
```

---

## 6. ML vs Deterministic Responsibilities

This distinction is critical. Forcing ML into every component is wasteful and unreliable. The following table proposes which tasks should remain deterministic and which are good ML candidates.

### Deterministic (DO NOT use ML)

| Task | Why Deterministic | Implementation |
|------|-------------------|----------------|
| **Move legality** | Binary fact — a Pokémon either can or cannot learn a move | Learnset lookup table |
| **STAB calculation** | Mathematical: 1.5x if move type matches Pokémon type | Type comparison |
| **Type effectiveness** | Fixed 18×18 matrix, no ambiguity | Existing `build_type_chart()` |
| **Stat alignment** | Physical moves → check Attack stat; Special → Sp.Atk | Threshold comparison |
| **Category matching** | Move is Physical/Special/Status — binary property | Move database lookup |
| **Type coverage computation** | Set arithmetic over types | Existing coverage logic in `synergy.py` |
| **Team gap identification** | Rule-based threshold detection | Existing gap logic in `synergy.py` |
| **Synergy score computation** | Weighted formula with deterministic inputs | Existing scoring in `synergy.py` |
| **Candidate filtering** | Hard constraint enforcement | Database queries |

### ML Candidates (CONSIDER using ML)

| Task | Why ML Could Help | Data Requirement |
|------|-------------------|------------------|
| **Move ranking** | Competitive viability is subjective and context-dependent | Competitive moveset usage data |
| **Role classification** | Pokémon roles depend on team context, not just stats | Labeled role data or competitive set data |
| **Team quality prediction** | Overall team strength involves complex interactions | Win/loss data or Elo-correlated data |
| **Usage pattern mining** | "What moves do top players use on this Pokémon?" | Smogon/Showdown usage statistics |
| **Replacement recommendation** | Requires understanding of complex team dynamics | Competitive team data |
| **Meta-aware ranking** | Adapting to current competitive meta | Temporal usage data |

### Hybrid Candidates (Deterministic First, ML Enhancement)

| Task | Deterministic Baseline | ML Enhancement |
|------|----------------------|----------------|
| **Moveset scoring** | STAB + coverage + stat alignment + category match | Weight by competitive usage frequency |
| **Replacement scoring** | Synergy delta + gap coverage | Weight by competitive viability |
| **Role assignment** | Stat-based heuristics (bulk → wall, speed+attack → sweeper) | Refine with competitive set data |

---

## 7. Open Architecture Questions

These are **unresolved research/design questions** that must be addressed before or during Phase 3 implementation.

### Data Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | **Where will learnset data come from?** The current repo has no move or learnset data. PokéAPI provides this but requires API calls or bulk download. | Blocks Moveset Recommender entirely |
| 2 | **Where will move data come from?** Need move name, type, category, power, accuracy, PP, effect for all moves. | Blocks Moveset Recommender |
| 3 | **Do we have enough competitive usage data for ML training?** | Determines if ML ranking is feasible vs. deterministic-only |
| 4 | **How should Gen 9 data be incorporated?** The Pokémon dataset covers Gen I-IX, but competitive data found so far mostly covers Gen 8 or earlier. | Gen 9 Pokémon may lack competitive recommendations |
| 5 | **How should different competitive formats be handled?** Singles vs. Doubles vs. VGC have very different move priorities. | Affects recommendation logic and training data |
| 6 | **What is the training target for an ML ranker?** Usage frequency? Win correlation? Expert labeling? | Determines model architecture |

### Architecture Questions

| # | Question | Impact |
|---|----------|--------|
| 7 | **Should the Moveset Recommender work per-Pokémon or per-team?** Recommending all 6 Pokémon's movesets simultaneously is significantly more complex. | Scope and UX design |
| 8 | **Should we add a move database as a new CSV, fetch from PokéAPI at runtime, or embed as a Python dict?** | Data architecture |
| 9 | **How should temporal meta shifts be handled?** Competitive viability changes between game patches and tournament seasons. | Data freshness strategy |
| 10 | **How should the Team Optimizer constrain its search space?** All 1351 Pokémon? Only same tier? Only same generation? | Performance and relevance |
| 11 | **How do we prevent illegal move recommendations?** | Must enforce learnset constraints as hard filter |
| 12 | **Should recommendations include items, natures, and EV spreads?** The UI placeholder mentions items and EVs, which significantly expands scope. | Feature scope |

### UX Questions

| # | Question | Impact |
|---|----------|--------|
| 13 | **How should recommendations be explained?** Free text? Structured cards? Visual type coverage diagrams? | Frontend design |
| 14 | **Should the optimizer show all suggestions at once or guide the user step-by-step?** | UX flow |
| 15 | **How should confidence/certainty be communicated?** Some recommendations may be strong; others speculative. | Trust and transparency |
| 16 | **How should the Moveset Recommender interact with the Team Optimizer?** Sequential? Combined? Independent? | Feature integration |

---

## 8. Proposed New API Endpoints

> **Status: PROPOSED — Subject to change based on architecture decisions**

### `POST /api/moveset` (PROPOSED)

```json
// Request
{
  "team": ["pelipper", "barraskewda", "kingdra", "ludicolo", "zapdos", "ferrothorn"],
  "target_pokemon": "barraskewda",
  "ability": "swift-swim",
  "existing_moves": ["liquidation"]
}

// Response
{
  "success": true,
  "pokemon": "barraskewda",
  "team_archetype": "rain",
  "recommendations": [
    {
      "move": "Close Combat",
      "type": "fighting",
      "category": "physical",
      "reasoning": "Provides coverage against Steel and Normal types that resist Water STAB.",
      "score": 0.92
    }
  ]
}
```

### `POST /api/optimize` (PROPOSED)

```json
// Request
{
  "team": ["charizard", "typhlosion", "infernape", "blaziken", "arcanine", "ninetales"],
  "locked_pokemon": ["charizard", "blaziken"]
}

// Response
{
  "success": true,
  "current_score": 34,
  "suggestions": [
    {
      "replace": "typhlosion",
      "with": "gastrodon",
      "reasoning": "Addresses critical Ground and Water weaknesses while maintaining Fire team core.",
      "new_score": 58,
      "score_delta": +24
    }
  ]
}
```

---

## 9. Proposed New File Structure

> **Status: PROPOSED — Extends existing project structure**

```
server/app/ml/
├── data_loader.py       # Existing — extend for new datasets
├── feature_engineering.py # Existing — extend for move features
├── generators.py        # Existing — no changes needed
├── model.py             # Existing — no changes needed
├── strategies.py        # Existing — potentially extend
├── synergy.py           # Existing — reuse for optimizer
├── moveset.py           # NEW — Moveset recommendation logic
├── optimizer.py          # NEW — Team optimization logic
└── move_data.py         # NEW — Move database and learnset utilities

server/app/api/
├── endpoints.py         # Existing — add /moveset and /optimize
└── schemas.py           # Existing — add new request/response schemas

datasets/
├── pokemon_complete.csv # Existing
├── pokemon_types.csv    # Existing
├── moves.csv            # NEW — Move database (name, type, category, power, accuracy, effect)
└── learnsets.csv         # NEW — Pokémon → learnable moves mapping
```
