import pytest
import os
import sys

# Ensure server directory is in python path
SERVER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from app.ml.constraints import load_game_data, get_pokemon_species
from app.ml.recommender import recommend_moveset
from app.ml.semantics_engine import score_item_priority, recommend_best_items, recommend_best_abilities
from app.ml.orchestrator import orchestrator
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def init_game_data():
    load_game_data()

class TestPostApprovalFeatures:
    """Comprehensive test suite for Phase 3 feature additions & pipeline orchestration."""

    def test_greninja_and_setup_move_stat_alignment(self):
        """TASK 2: Verify setup move target stat alignment (Swords Dance vs Nasty Plot vs Calm Mind)."""
        # 1. Greninja should NOT get Swords Dance under any archetype
        for arch in ["balance", "hyper_offense", "rain"]:
            res = recommend_moveset("Greninja", archetype=arch)
            move_names = [m["name"].lower() for m in res["recommended_moves"]]
            assert "swords dance" not in move_names, f"Greninja received Swords Dance under {arch}"

        # 2. Kingambit, Dragonite, Garchomp SHOULD get physical setup under Hyper Offense
        kg_res = recommend_moveset("Kingambit", archetype="hyper_offense")
        kg_moves = [m["name"].lower() for m in kg_res["recommended_moves"]]
        assert "swords dance" in kg_moves, "Kingambit should receive Swords Dance"

        dn_res = recommend_moveset("Dragonite", archetype="hyper_offense")
        dn_moves = [m["name"].lower() for m in dn_res["recommended_moves"]]
        assert "dragon dance" in dn_moves, "Dragonite should receive Dragon Dance"

        gc_res = recommend_moveset("Garchomp", archetype="hyper_offense")
        gc_moves = [m["name"].lower() for m in gc_res["recommended_moves"]]
        assert "swords dance" in gc_moves, "Garchomp should receive Swords Dance"

    def test_item_prioritization_and_deduplication(self):
        """TASK 1: Verify multi-factor item recommendation priority layer."""
        # 1. Dusclops (NFE Wall) -> Eviolite top priority
        dusc_res = recommend_moveset("Dusclops", archetype="trick_room")
        assert dusc_res["recommended_items"][0] == "Eviolite", "Dusclops must receive Eviolite as top item"

        # 2. Pelipper (Rain Setter) -> Damp Rock top priority
        pel_res = recommend_moveset("Pelipper", archetype="rain")
        assert "Damp Rock" in pel_res["recommended_items"], "Pelipper must receive Damp Rock"

        # 3. Walking Wake in Sun -> Booster Energy
        ww_res = recommend_moveset("Walking Wake", archetype="sun")
        assert "Booster Energy" in ww_res["recommended_items"], "Walking Wake should receive Booster Energy"

        # 4. Cloyster (Multi-hit Icicle Spear) -> Loaded Dice
        cloy_res = recommend_moveset("Cloyster", archetype="hyper_offense")
        assert "Loaded Dice" in cloy_res["recommended_items"], "Cloyster should receive Loaded Dice"

        # 5. Volcarona (4x SR weak) -> Heavy-Duty Boots
        volc_res = recommend_moveset("Volcarona", archetype="hyper_offense")
        assert "Heavy-Duty Boots" in volc_res["recommended_items"], "Volcarona should receive Heavy-Duty Boots"

        # 6. Items must be deduplicated
        for items in [dusc_res["recommended_items"], pel_res["recommended_items"], ww_res["recommended_items"]]:
            assert len(items) == len(set(items)), "Recommended items must not contain duplicate entries"

    def test_ability_recommendation_engine(self):
        """TASK 3 & 4: Verify Ability recommendations and moveset synergy."""
        # 1. Gallade with slicing moves -> Sharpness
        gal_res = recommend_moveset("Gallade", archetype="hyper_offense")
        assert gal_res["recommended_abilities"][0]["name"] == "Sharpness", "Gallade should prioritize Sharpness"
        assert gal_res["recommended_abilities"][0]["score"] > 3.0

        # 2. Pelipper under Rain -> Drizzle
        pel_res = recommend_moveset("Pelipper", archetype="rain")
        assert pel_res["recommended_abilities"][0]["name"] == "Drizzle", "Pelipper should prioritize Drizzle"

        # 3. Toxapex under Stall -> Regenerator
        tox_res = recommend_moveset("Toxapex", archetype="stall")
        assert tox_res["recommended_abilities"][0]["name"] == "Regenerator", "Toxapex should prioritize Regenerator"
        assert tox_res["recommended_abilities"][0]["is_hidden"] is True

        # 4. Dragonite -> Multiscale
        dn_res = recommend_moveset("Dragonite", archetype="hyper_offense")
        assert dn_res["recommended_abilities"][0]["name"] == "Multiscale", "Dragonite should prioritize Multiscale"

        # 5. Kingambit -> Supreme Overlord
        kg_res = recommend_moveset("Kingambit", archetype="hyper_offense")
        assert kg_res["recommended_abilities"][0]["name"] == "Supreme Overlord"

    def test_pipeline_orchestrator_dag_and_invalidation(self):
        """TASK 5, 6, 7: Verify DAG pipeline execution, order, and smart invalidation."""
        team = ["Pelipper", "Archaludon", "Swampert-Mega", "Overqwil", "Kilowattrel", "Iron Hands"]

        # Run 1: Cold start execution
        run1 = orchestrator.run_all(team=team, format_name="gen9ou")
        assert run1["success"] is True
        assert len(run1["trace"]) == 5

        # Check topological step ordering
        expected_steps = [
            "team_validation",
            "archetype_prediction",
            "team_synergy",
            "moveset_recommendation",
            "team_optimizer"
        ]
        actual_steps = [t["step_id"] for t in run1["trace"]]
        assert actual_steps == expected_steps, f"Pipeline steps not in topological order: {actual_steps}"

        # In cold start, all steps must be executed and marked invalidated
        for step in run1["trace"]:
            assert step["executed"] is True
            assert step["status"] == "completed"

        # Run 2: Exact re-run with cached state (steps 2-5 should be skipped)
        run2 = orchestrator.run_all(team=team, format_name="gen9ou", cached_state=run1["cache_state"])
        assert run2["success"] is True
        for step in run2["trace"][1:]:  # steps 2 through 5
            assert step["executed"] is False
            assert step["status"] == "skipped"
            assert "used cached" in step["invalidation_reason"].lower()

        # Run 3: Strategy parameter changed (target_archetype = 'sun')
        run3 = orchestrator.run_all(
            team=team,
            format_name="gen9ou",
            target_archetype="sun",
            cached_state=run1["cache_state"]
        )
        assert run3["success"] is True
        # Step 1 (validation), Step 2 (archetype), Step 3 (synergy) should be skipped from cache
        assert run3["trace"][1]["executed"] is False  # archetype skipped
        assert run3["trace"][2]["executed"] is False  # synergy skipped
        # Step 4 (movesets) and Step 5 (optimizer) should re-execute
        assert run3["trace"][3]["executed"] is True   # movesets re-executed
        assert run3["trace"][4]["executed"] is True   # optimizer re-executed

    def test_pipeline_api_endpoint(self):
        """TASK 8: Verify POST /api/pipeline/run-all API endpoint."""
        team = ["Pelipper", "Archaludon", "Swampert-Mega", "Overqwil", "Kilowattrel", "Iron Hands"]
        resp = client.post("/api/pipeline/run-all", json={
            "team": team,
            "format": "gen9ou"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "trace" in data
        assert len(data["trace"]) == 5
        assert "results" in data
        assert "validation" in data["results"]
        assert "archetype" in data["results"]
        assert "synergy" in data["results"]
        assert "movesets" in data["results"]
        assert "optimizer" in data["results"]

    def test_moveset_api_endpoint_abilities_and_items(self):
        """Verify POST /api/recommend/moveset includes recommended_abilities and prioritized items."""
        resp = client.post("/api/recommend/moveset", json={
            "pokemon": "Gallade",
            "archetype": "hyper_offense",
            "format": "gen9ou"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "recommended_abilities" in data
        assert len(data["recommended_abilities"]) > 0
        assert data["recommended_abilities"][0]["name"] == "Sharpness"
        assert "recommended_items" in data
        assert len(data["recommended_items"]) > 0
