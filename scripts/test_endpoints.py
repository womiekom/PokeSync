import sys
import os

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "server"))

from fastapi.testclient import TestClient
from app.main import app

def test_api_endpoints():
    client = TestClient(app)
    
    print("--- 1. Testing GET / ---")
    res_root = client.get("/")
    assert res_root.status_code == 200
    print("Root response:", res_root.json())
    
    print("\n--- 2. Testing GET /api/pokemon ---")
    res_poke = client.get("/api/pokemon")
    assert res_poke.status_code == 200
    poke_list = res_poke.json()["pokemon"]
    assert len(poke_list) > 1000
    print(f"Total Pokemon count: {len(poke_list)}")
    
    print("\n--- 3. Testing POST /api/predict (Stall Team) ---")
    stall_team = ["Toxapex", "Blissey", "Corviknight", "Clodsire", "Dondozo", "Alomomola"]
    res_predict = client.post("/api/predict", json={"team": stall_team})
    assert res_predict.status_code == 200
    data_predict = res_predict.json()
    assert data_predict["success"] is True
    assert data_predict["prediction"] == "stall"
    print(f"Predicted: {data_predict['prediction']} with alignment {data_predict['probabilities']['stall']*100:.1f}%")
    print(f"Explanations: {data_predict['explanations']}")
    
    print("\n--- 4. Testing POST /api/synergy (Rain Team) ---")
    rain_team = ["Pelipper", "Barraskewda", "Kingdra", "Ludicolo", "Zapdos", "Ferrothorn"]
    res_synergy = client.post("/api/synergy", json={"team": rain_team})
    assert res_synergy.status_code == 200
    data_synergy = res_synergy.json()
    assert data_synergy["success"] is True
    print("Rain Synergy Score:", data_synergy["overall"]["score"])
    print("Rain Rating:", data_synergy["overall"]["rating"])
    print("Rain Summary:", data_synergy["overall"]["summary"])
    print("Strengths Count:", len(data_synergy["strengths"]))
    print("Gaps Count:", len(data_synergy["gaps"]))
    assert len(data_synergy["type_matchups"]) == 18
    assert len(data_synergy["team_data"]) == 6
    
    print("\n--- 5. Testing POST /api/synergy (Mono-Fire Team) ---")
    mono_fire = ["Charizard", "Arcanine", "Flareon", "Ninetales", "Rapidash", "Magmortar"]
    res_fire = client.post("/api/synergy", json={"team": mono_fire})
    assert res_fire.status_code == 200
    data_fire = res_fire.json()
    assert data_fire["success"] is True
    print("Mono-Fire Score:", data_fire["overall"]["score"])
    print("Mono-Fire Rating:", data_fire["overall"]["rating"])
    print("Mono-Fire Gaps:", [g["title"] for g in data_fire["gaps"]])
    
    print("\n--- 6. Testing Error Cases ---")
    # Wrong length
    res_err1 = client.post("/api/synergy", json={"team": ["Pikachu"]})
    assert res_err1.json()["success"] is False
    print("Short team error caught successfully")
    
    # Duplicate
    res_err2 = client.post("/api/synergy", json={"team": ["Pikachu", "Pikachu", "Pelipper", "Kingdra", "Ludicolo", "Zapdos"]})
    assert res_err2.json()["success"] is False
    print("Duplicate mon error caught successfully")
    
    # Invalid Mon
    res_err3 = client.post("/api/synergy", json={"team": ["FakeMon99", "Blissey", "Pelipper", "Kingdra", "Ludicolo", "Zapdos"]})
    assert res_err3.json()["success"] is False
    print("Invalid mon error caught successfully")

    print("\n==========================================")
    print(">>> ALL FULL-STACK API TESTS PASSED 100%! <<<")
    print("==========================================")

if __name__ == "__main__":
    test_api_endpoints()
