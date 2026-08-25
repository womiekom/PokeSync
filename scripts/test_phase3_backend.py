import os
import sys
import unittest

# Add server directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from fastapi.testclient import TestClient
from app.main import app
from app.ml.constraints import get_legal_moves, get_stab_multiplier, get_pokemon_species
from app.ml.recommender import recommend_moveset
from app.ml.optimizer import optimize_team
from app.ml.data_loader import load_and_clean_data
from app.core.config import settings

class TestPhase3Backend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.df_pokemon, cls.df_types = load_and_clean_data(settings.POKEMON_CSV, settings.TYPES_CSV)

    def test_constraints_legal_moves(self):
        print("\n--- Testing Move Constraints ---")
        # Great Tusk legal moves
        moves = get_legal_moves("greattusk", "gen9ou")
        self.assertTrue(len(moves) > 20)
        self.assertIn("headlongrush", moves)
        self.assertIn("rapidspin", moves)
        self.assertIn("icespinner", moves)
        # Scald on Toxapex should NOT be legal in Gen 9
        toxapex_moves = get_legal_moves("toxapex", "gen9ou")
        self.assertNotIn("scald", toxapex_moves)
        print(f"Great Tusk legal moves count: {len(moves)}")
        print("Verified: Scald is correctly excluded from Gen 9 Toxapex legal learnset.")

    def test_recommender_sun_synergy(self):
        print("\n--- Testing Moveset Recommender (Sun Archetype) ---")
        res = recommend_moveset(
            pokemon_name="Venusaur",
            ability="chlorophyll",
            archetype="sun",
            teammates=["Torkoal", "Walking-Wake", "Great-Tusk", "Raging-Bolt", "Hatterene"],
            format_name="gen9ou"
        )
        self.assertTrue(res["success"])
        rec_move_ids = [m["id"] for m in res["recommended_moves"]]
        print("Recommended moves for Venusaur in Sun:", [m["name"] for m in res["recommended_moves"]])
        print("Recommended Tera types:", res["recommended_tera_types"])
        # Should recommend Sun-boosted moves
        self.assertTrue(any(m in rec_move_ids for m in ["growth", "weatherball", "solarbeam", "gigadrain", "sludgebomb"]))

    def test_recommender_hyper_offense(self):
        print("\n--- Testing Moveset Recommender (Hyper Offense Great Tusk) ---")
        res = recommend_moveset(
            pokemon_name="Great Tusk",
            ability="protosynthesis",
            archetype="hyper_offense",
            teammates=["Gholdengo", "Kingambit", "Dragapult", "Iron-Valiant", "Ogerpon-Wellspring"],
            format_name="gen9ou"
        )
        self.assertTrue(res["success"])
        rec_move_ids = [m["id"] for m in res["recommended_moves"]]
        print("Recommended moves for Great Tusk in HO:", [m["name"] for m in res["recommended_moves"]])
        self.assertTrue(any(m in rec_move_ids for m in ["headlongrush", "earthquake", "closecombat"]))
        self.assertTrue(any(m in rec_move_ids for m in ["rapidspin", "icespinner", "knockoff", "stealthrock"]))

    def test_optimizer_improves_weak_team(self):
        print("\n--- Testing Team Optimizer ---")
        # Team with 4 Fire-types (severe Ground/Water/Rock weakness)
        weak_team = ["Charizard", "Arcanine", "Ninetales", "Flareon", "Pikachu", "Snorlax"]
        res = optimize_team(
            team=weak_team,
            df_pokemon=self.df_pokemon,
            df_types=self.df_types,
            format_name="gen9ou"
        )
        self.assertTrue(res["success"])
        self.assertTrue(len(res["suggestions"]) > 0)
        top_suggestion = res["suggestions"][0]
        print(f"Baseline Score: {res['baseline_score']}")
        print(f"Top Suggestion: Replace {top_suggestion['remove_pokemon']} with {top_suggestion['add_pokemon']}")
        print(f"Score Delta: +{top_suggestion['score_delta']} (New Score: {top_suggestion['new_score']})")
        print(f"Improved Matchups: {top_suggestion['improved_matchups']}")
        self.assertGreater(top_suggestion["score_delta"], 0)

    def test_api_endpoints(self):
        print("\n--- Testing FastAPI Phase 3 Endpoints ---")
        # 1. Format endpoint
        resp_fmt = self.client.get("/api/formats")
        self.assertEqual(resp_fmt.status_code, 200)
        self.assertEqual(len(resp_fmt.json()["formats"]), 2)

        # 2. Moveset recommend endpoint
        resp_rec = self.client.post("/api/recommend/moveset", json={
            "pokemon": "Gholdengo",
            "ability": "goodasgold",
            "archetype": "balance",
            "format": "gen9ou",
            "team": ["Great-Tusk", "Dragonite", "Kingambit", "Rillaboom", "Primarina"]
        })
        self.assertEqual(resp_rec.status_code, 200)
        data = resp_rec.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["recommended_moves"]), 4)
        print("API Moveset Recommendation for Gholdengo:", [m["name"] for m in data["recommended_moves"]])

        # 3. Optimize endpoint
        resp_opt = self.client.post("/api/optimize/team", json={
            "team": ["Charizard", "Arcanine", "Ninetales", "Flareon", "Pikachu", "Snorlax"],
            "format": "gen9ou"
        })
        self.assertEqual(resp_opt.status_code, 200)
        opt_data = resp_opt.json()
        self.assertTrue(opt_data["success"])
        self.assertTrue(len(opt_data["suggestions"]) > 0)
        print(f"API Optimizer returned {len(opt_data['suggestions'])} replacement proposals.")

if __name__ == "__main__":
    unittest.main()
