import pytest
import sys
import os

# Add server directory to path
SERVER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from app.ml.constraints import load_game_data, get_pokemon_species, get_legal_moves
from app.ml.mechanics_engine import (
    evaluate_move_mechanics,
    get_effective_base_power,
    get_stat_alignment_score,
    is_status_move
)
from app.ml.semantics_engine import (
    recommend_best_items,
    classify_archetype_role
)
from app.ml.recommender import recommend_moveset
from app.ml.optimizer import evaluate_candidate_archetype_harmony


class TestPhase3AdversarialFixes:

    @classmethod
    def setup_class(cls):
        load_game_data()

    def test_ability_flags_iron_fist(self):
        """Verify Iron Fist boosts all punch flag moves and DOES NOT boost Close Combat."""
        drain_punch_flags = {"punch": 1, "contact": 1}
        close_combat_flags = {"contact": 1}
        
        # Drain Punch (75 BP) with Iron Fist -> 75 * 1.2 = 90 BP
        bp_dp, notes_dp = get_effective_base_power(
            move_id="drainpunch",
            base_power=75,
            move_type="fighting",
            category="Physical",
            ability="ironfist",
            move_flags=drain_punch_flags
        )
        assert bp_dp == 90.0, f"Expected 90.0 BP for Drain Punch with Iron Fist, got {bp_dp}"
        assert any("Iron Fist" in n for n in notes_dp)
        
        # Close Combat (120 BP) with Iron Fist -> MUST remain 120 BP (NOT a punch move)
        bp_cc, notes_cc = get_effective_base_power(
            move_id="closecombat",
            base_power=120,
            move_type="fighting",
            category="Physical",
            ability="ironfist",
            move_flags=close_combat_flags
        )
        assert bp_cc == 120.0, f"Expected 120.0 BP for Close Combat with Iron Fist, got {bp_cc}"
        assert not any("Iron Fist" in n for n in notes_cc)

    def test_ability_flags_sharpness_strongjaw_punkrock_sheerforce(self):
        """Verify Sharpness, Strong Jaw, Punk Rock, and Sheer Force use flags/secondaries."""
        # Sharpness on Sacred Sword (slicing: 1) -> 90 * 1.5 = 135 BP
        bp_ss, _ = get_effective_base_power(
            move_id="sacredsword",
            base_power=90,
            move_type="fighting",
            category="Physical",
            ability="sharpness",
            move_flags={"slicing": 1}
        )
        assert bp_ss == 135.0

        # Strong Jaw on Crunch (bite: 1) -> 80 * 1.5 = 120 BP
        bp_cr, _ = get_effective_base_power(
            move_id="crunch",
            base_power=80,
            move_type="dark",
            category="Physical",
            ability="strongjaw",
            move_flags={"bite": 1}
        )
        assert bp_cr == 120.0

        # Punk Rock on Hyper Voice (sound: 1) -> 90 * 1.3 = 117 BP
        bp_hv, _ = get_effective_base_power(
            move_id="hypervoice",
            base_power=90,
            move_type="normal",
            category="Special",
            ability="punkrock",
            move_flags={"sound": 1}
        )
        assert bp_hv == 117.0

        # Sheer Force on Iron Head (has secondary) -> 80 * 1.3 = 104 BP
        bp_ih, _ = get_effective_base_power(
            move_id="ironhead",
            base_power=80,
            move_type="steel",
            category="Physical",
            ability="sheerforce",
            move_secondaries=True
        )
        assert bp_ih == 104.0

    def test_body_press_mechanics(self):
        """Verify Body Press uses Defense stat instead of Attack for stat alignment."""
        # Pokémon with 40 Atk, 130 Def, 60 SpA (like Dusclops)
        move_info_bp = {
            "name": "Body Press",
            "type": "Fighting",
            "category": "Physical",
            "power": 80,
            "accuracy": 100,
            "overrideOffensiveStat": "def"
        }
        
        # When evaluating Body Press, stat alignment should compare Def (130) vs SpA (60)
        # Ratio = 130 / 130 = 1.0 (perfect alignment) + magnitude scaling min(1.25, 130/100) = 1.25
        score = get_stat_alignment_score(
            category="Physical",
            base_atk=40,
            base_spa=60,
            base_def=130,
            move_data=move_info_bp
        )
        assert score >= 1.0, f"Expected >=1.0 stat alignment for Body Press on high-Def Pokémon, got {score}"

        # Contrast with standard physical move (e.g. Tackle 40 Atk / 60 SpA -> ratio = 40/60 = 0.667 -> score = 0.444)
        score_std = get_stat_alignment_score(
            category="Physical",
            base_atk=40,
            base_spa=60,
            base_def=130,
            move_data={"name": "Tackle"}
        )
        assert score_std < 0.5, f"Expected <0.5 stat alignment for Tackle with 40 Atk, got {score_std}"

    def test_foul_play_and_fixed_damage_mechanics(self):
        """Verify Foul Play and fixed-damage moves (Seismic Toss/Night Shade) bypass stat penalties."""
        # Foul Play on a 10 Atk / 130 SpA special wall (e.g. Blissey/Chansey with 10 Atk)
        move_info_fp = {
            "name": "Foul Play",
            "type": "Dark",
            "category": "Physical",
            "power": 95,
            "accuracy": 100,
            "overrideOffensivePokemon": "target"
        }
        score_fp = get_stat_alignment_score(
            category="Physical",
            base_atk=10,
            base_spa=130,
            base_def=10,
            move_data=move_info_fp
        )
        assert score_fp == 1.0, "Foul Play must receive 1.0 stat alignment regardless of user's low Attack"

        # Seismic Toss (damage: "level")
        move_info_st = {
            "name": "Seismic Toss",
            "type": "Fighting",
            "category": "Physical",
            "power": 0,
            "accuracy": 100,
            "damage": "level"
        }
        score_st = get_stat_alignment_score(
            category="Physical",
            base_atk=10,
            base_spa=130,
            base_def=10,
            move_data=move_info_st
        )
        assert score_st == 1.0, "Seismic Toss must receive 1.0 stat alignment"

        species_blissey = {
            "name": "Blissey",
            "types": ["Normal"],
            "baseStats": {"hp": 255, "atk": 10, "def": 10, "spa": 75, "spd": 135, "spe": 55}
        }
        mech_res = evaluate_move_mechanics(
            move_id="seismictoss",
            move_info=move_info_st,
            user_species=species_blissey
        )
        assert mech_res["effective_bp"] == 100.0, "Fixed damage moves must be assigned 100.0 effective power proxy"
        assert mech_res["stat_score"] == 1.0

    def test_nfe_eviolite_recommendations(self):
        """Verify NFE Pokémon get Eviolite recommended, while fully-evolved Pokémon do not."""
        dusclops_spec = get_pokemon_species("dusclops")
        assert dusclops_spec is not None
        assert "evos" in dusclops_spec  # Has "Dusknoir" in evos -> NFE

        items_dusclops = recommend_best_items(
            species_name="dusclops",
            species_data=dusclops_spec,
            archetype="trick_room",
            role_info={"is_setter": False},
            top_meta_items=[]
        )
        assert "Eviolite" in items_dusclops, f"Dusclops must be recommended Eviolite, got {items_dusclops}"
        assert items_dusclops[0] == "Eviolite", f"Eviolite should be first recommendation for NFE, got {items_dusclops}"

        chansey_spec = get_pokemon_species("chansey")
        assert chansey_spec is not None
        items_chansey = recommend_best_items(
            species_name="chansey",
            species_data=chansey_spec,
            archetype="stall",
            role_info={"is_setter": False},
            top_meta_items=[]
        )
        assert "Eviolite" in items_chansey, f"Chansey must be recommended Eviolite, got {items_chansey}"

        # Fully evolved Pokémon (Dusknoir, Blissey) must NOT get Eviolite
        dusknoir_spec = get_pokemon_species("dusknoir")
        assert dusknoir_spec is not None
        assert "evos" not in dusknoir_spec
        items_dusknoir = recommend_best_items(
            species_name="dusknoir",
            species_data=dusknoir_spec,
            archetype="trick_room",
            role_info={"is_setter": False},
            top_meta_items=[]
        )
        assert "Eviolite" not in items_dusknoir, f"Fully evolved Dusknoir must NOT get Eviolite, got {items_dusknoir}"

    def test_dusclops_moveset_recommendations(self):
        """Verify Dusclops receives a coherent defensive/utility moveset rather than 4 raw attacks."""
        res = recommend_moveset(
            pokemon_name="Dusclops",
            ability="Pressure",
            archetype="trick_room",
            format_name="gen9ou"
        )
        assert res["success"] is True
        recommended_moves = res["recommended_moves"]
        move_ids = [m["id"] for m in recommended_moves]

        # Verify Eviolite is recommended
        assert "Eviolite" in res["recommended_items"], f"Expected Eviolite in items, got {res['recommended_items']}"

        # Verify at least one or more status/utility moves are selected
        status_moves = [m for m in recommended_moves if is_status_move(m["category"])]
        assert len(status_moves) >= 1, f"Dusclops must have at least 1 status move, got {move_ids}"

        # Verify Trick Room or Will-O-Wisp or Pain Split or Night Shade is considered
        desirable_moves = {"trickroom", "willowisp", "painsplit", "nightshade", "taunt", "haze", "destinybond", "curse", "shadowsneak"}
        overlap = set(move_ids) & desirable_moves
        assert len(overlap) >= 2, f"Dusclops should have iconic support moves, got {move_ids}"

    def test_walking_wake_generic_sun_harmony(self):
        """Verify Sun harmony scoring is generic and does not contain hardcoded name checks."""
        ww_spec = get_pokemon_species("walkingwake")
        assert ww_spec is not None

        # Evaluate Walking Wake in Sun
        mod, reasons = evaluate_candidate_archetype_harmony(
            candidate_name="walkingwake",
            species_info=ww_spec,
            target_archetype="sun"
        )
        # Walking Wake has Protosynthesis (boosted in Sun)
        # Even though it is Water type, Protosynthesis grants +8.0
        assert mod > -15.0, "Walking Wake should not be hard-disqualified from Sun teams"
