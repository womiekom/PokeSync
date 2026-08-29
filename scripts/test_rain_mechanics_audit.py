import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from app.ml.recommender import recommend_moveset
from app.ml.optimizer import optimize_team
from app.ml.data_loader import load_and_clean_data
from app.core.config import settings

df_pokemon, df_types = load_and_clean_data(settings.POKEMON_CSV, settings.TYPES_CSV)

rain_team = ["Pelipper", "Archaludon", "Swampert", "Overqwil", "Kilowattrel", "Iron-Hands"]

print("="*80)
print("AUDITING PHASE 3 MOVESET RECOMMENDER ON RAIN TEST TEAM")
print("="*80)

for mon in rain_team:
    print(f"\n--- {mon} (Archetype: Rain) ---")
    res = recommend_moveset(
        pokemon_name=mon,
        archetype="rain",
        teammates=[m for m in rain_team if m != mon],
        format_name="gen9ou"
    )
    if res.get("success"):
        print(f"Species: {res['pokemon']} | Types: {res['types']}")
        print(f"Recommended Tera Types: {res['recommended_tera_types']}")
        print(f"Recommended Items: {res['recommended_items']}")
        print("Recommended Moves:")
        for idx, m in enumerate(res['recommended_moves'], 1):
            print(f"  {idx}. {m['name']} ({m['type']} | {m['category']} | BP: {m['power']} | Acc: {m['accuracy']} | Pri: {m['priority']})")
            print(f"     Score: {m['score']} | Role: {m['role_tag']}")
            print(f"     Rationale: {m['rationale']}")
    else:
        print("Error:", res.get("error"))

print("\n" + "="*80)
print("AUDITING PHASE 3 TEAM OPTIMIZER ON RAIN TEST TEAM")
print("="*80)

opt_res = optimize_team(
    team=rain_team,
    df_pokemon=df_pokemon,
    df_types=df_types,
    format_name="gen9ou",
    target_archetype="rain"
)

print(f"Baseline Synergy Score: {opt_res.get('baseline_score')}")
print("Gaps Detected:")
for g in opt_res.get("gaps_detected", []):
    print(f"  - [{g.get('severity')}] {g.get('title')}: {g.get('description')}")

print("\nOptimization Suggestions:")
for s in opt_res.get("suggestions", []):
    print(f"  - Replace {s['remove_pokemon']} with {s['add_pokemon']} (Score Delta: +{s['score_delta']} -> New Score: {s['new_score']})")
    print(f"    Improved Matchups: {s['improved_matchups']}")
    print(f"    Rationale: {s['rationale']}")
