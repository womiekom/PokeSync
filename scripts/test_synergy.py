import sys
import os

# Add server to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "server"))

from app.ml.data_loader import load_and_clean_data
from app.ml.synergy import analyze_team_synergy
from app.core.config import settings

def test_synergy():
    print("Loading data...")
    df_pokemon, df_types = load_and_clean_data(settings.POKEMON_CSV, settings.TYPES_CSV)
    
    rain_team = ["Pelipper", "Barraskewda", "Kingdra", "Ludicolo", "Zapdos", "Ferrothorn"]
    print(f"\n--- Testing Rain Team: {rain_team} ---")
    result = analyze_team_synergy(rain_team, df_pokemon, df_types)
    assert result is not None, "Synergy calculation returned None"
    assert result["success"] is True
    print("Overall Score:", result["overall"]["score"])
    print("Rating:", result["overall"]["rating"])
    print("Rating Summary:", result["overall"]["summary"])
    print("Defensive Score:", result["overall"]["defensive_score"])
    print("Offensive Score:", result["overall"]["offensive_score"])
    print("Strategic Score:", result["overall"]["strategic_score"])
    print("Strengths:", len(result["strengths"]))
    for s in result["strengths"]:
        print(f"  [+] {s['title']} ({s['tag']}): {s['description']}")
    print("Gaps:", len(result["gaps"]))
    for g in result["gaps"]:
        print(f"  [-] {g['title']} ({g['tag']}): {g['description']}")
        
    stall_team = ["Toxapex", "Blissey", "Corviknight", "Clodsire", "Dondozo", "Alomomola"]
    print(f"\n--- Testing Stall Team: {stall_team} ---")
    result_stall = analyze_team_synergy(stall_team, df_pokemon, df_types)
    assert result_stall is not None
    print("Stall Score:", result_stall["overall"]["score"])
    print("Rating:", result_stall["overall"]["rating"])
    print("Stall Def Score:", result_stall["overall"]["defensive_score"])
    print("Stall Off Score:", result_stall["overall"]["offensive_score"])
    print("Stall Strat Score:", result_stall["overall"]["strategic_score"])
    
    trick_room_team = ["Hatterene", "Ursaluna", "Amoonguss", "Cresselia", "Torkoal", "Kingambit"]
    print(f"\n--- Testing Trick Room Team: {trick_room_team} ---")
    result_tr = analyze_team_synergy(trick_room_team, df_pokemon, df_types)
    assert result_tr is not None
    print("TR Score:", result_tr["overall"]["score"])
    print("TR Rating:", result_tr["overall"]["rating"])
    
    print("\n--- ALL SYNERGY TESTS PASSED! ---")

if __name__ == "__main__":
    test_synergy()
