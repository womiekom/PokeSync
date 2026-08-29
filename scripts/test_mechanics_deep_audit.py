import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from app.ml.mechanics_engine import (
    get_effective_base_power,
    get_effective_accuracy,
    get_stab_multiplier,
    get_stat_alignment_score,
    get_move_priority,
    evaluate_move_mechanics,
    is_status_move
)
from app.ml.semantics_engine import (
    classify_archetype_role,
    evaluate_item_restrictions,
    recommend_best_items
)
from app.ml.recommender import recommend_moveset
from app.ml.optimizer import optimize_team
from app.ml.constraints import get_pokemon_species, get_legal_moves, load_game_data
from app.ml.data_loader import load_and_clean_data
from app.core.config import settings

class TestMechanicsDeepAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_game_data()
        cls.df_pokemon, cls.df_types = load_and_clean_data(settings.POKEMON_CSV, settings.TYPES_CSV)

    # -------------------------------------------------------------
    # 1. WEATHER MECHANICS TESTS
    # -------------------------------------------------------------
    def test_rain_mechanics(self):
        print("\n--- 1. Testing Rain Mechanics ---")
        # Water boosted 1.5x in rain
        eff_bp, notes = get_effective_base_power("surf", 90, "water", "Special", weather="rain")
        self.assertEqual(eff_bp, 135.0)
        # Fire halved 0.5x in rain
        eff_bp_fire, _ = get_effective_base_power("flamethrower", 90, "fire", "Special", weather="rain")
        self.assertEqual(eff_bp_fire, 45.0)
        # Hurricane & Thunder 100% accuracy in rain
        self.assertEqual(get_effective_accuracy("hurricane", 70, weather="rain"), 100)
        self.assertEqual(get_effective_accuracy("thunder", 70, weather="rain"), 100)
        # Weather Ball becomes 100 BP Water in rain (100 * 1.5 = 150)
        wb_bp, wb_notes = get_effective_base_power("weatherball", 50, "normal", "Special", weather="rain")
        self.assertEqual(wb_bp, 150.0)
        # Electro Shot has 1-turn note in Rain
        _, es_notes = get_effective_base_power("electroshot", 130, "electric", "Special", weather="rain")
        self.assertTrue(any("1 turn" in n for n in es_notes))
        print("[OK] Verified: Rain 1.5x Water, 0.5x Fire, 100% Thunder/Hurricane accuracy, 1-turn Electro Shot.")

    def test_sun_mechanics(self):
        print("\n--- 2. Testing Sun Mechanics ---")
        # Fire boosted 1.5x in sun
        eff_bp, _ = get_effective_base_power("flamethrower", 90, "fire", "Special", weather="sun")
        self.assertEqual(eff_bp, 135.0)
        # Water halved 0.5x in sun (except Hydro Steam)
        eff_bp_water, _ = get_effective_base_power("surf", 90, "water", "Special", weather="sun")
        self.assertEqual(eff_bp_water, 45.0)
        # Hydro Steam is boosted by 1.5x in Sun
        eff_bp_hs, _ = get_effective_base_power("hydrosteam", 80, "water", "Special", weather="sun")
        self.assertEqual(eff_bp_hs, 120.0)
        # Hurricane drops to 50% in sun
        self.assertEqual(get_effective_accuracy("hurricane", 70, weather="sun"), 50)
        # Solar Beam 1-turn in sun
        _, sb_notes = get_effective_base_power("solarbeam", 120, "grass", "Special", weather="sun")
        self.assertTrue(any("1 turn" in n for n in sb_notes))
        # Solar Beam halved in Rain
        sb_rain, _ = get_effective_base_power("solarbeam", 120, "grass", "Special", weather="rain")
        self.assertEqual(sb_rain, 60.0)
        print("[OK] Verified: Sun 1.5x Fire, 0.5x Water, Hydro Steam exception, 50% Hurricane accuracy, 1-turn Solar Beam.")

    def test_sand_and_snow_mechanics(self):
        print("\n--- 3. Testing Sand & Snow Mechanics ---")
        # Blizzard 100% accuracy in Snow
        self.assertEqual(get_effective_accuracy("blizzard", 70, weather="snow"), 100)
        # Weather Ball in Sand -> Rock, in Snow -> Ice
        wb_sand, _ = get_effective_base_power("weatherball", 50, "normal", "Special", weather="sand")
        self.assertEqual(wb_sand, 100.0)
        wb_snow, _ = get_effective_base_power("weatherball", 50, "normal", "Special", weather="snow")
        self.assertEqual(wb_snow, 100.0)
        print("[OK] Verified: Blizzard 100% accuracy in Snow, Weather Ball Rock/Ice transformations.")

    # -------------------------------------------------------------
    # 2. TERRAIN MECHANICS TESTS
    # -------------------------------------------------------------
    def test_terrain_mechanics(self):
        print("\n--- 4. Testing Terrain Mechanics ---")
        # Electric Terrain 1.3x
        bp_elec, _ = get_effective_base_power("thunderbolt", 90, "electric", "Special", terrain="electric")
        self.assertEqual(round(bp_elec, 1), 117.0)
        # Grassy Terrain 1.3x Grass & 0.5x Earthquake
        bp_grass, _ = get_effective_base_power("energyball", 90, "grass", "Special", terrain="grassy")
        self.assertEqual(round(bp_grass, 1), 117.0)
        bp_eq, _ = get_effective_base_power("earthquake", 100, "ground", "Physical", terrain="grassy")
        self.assertEqual(bp_eq, 50.0)
        # Grassy Glide +1 Priority in Grassy Terrain
        self.assertEqual(get_move_priority("grassyglide", 0, terrain="grassy"), 1)
        # Expanding Force in Psychic Terrain: 80 -> 120 (1.5x) * 1.3 Psychic boost = 156.0
        bp_ef, _ = get_effective_base_power("expandingforce", 80, "psychic", "Special", terrain="psychic")
        self.assertEqual(bp_ef, 156.0)
        print("[OK] Verified: Electric/Grassy/Psychic terrain damage modifiers, Earthquake halving, Grassy Glide priority.")

    # -------------------------------------------------------------
    # 3. STATUS VS DAMAGING MOVE STAB & RATIONALE TESTS
    # -------------------------------------------------------------
    def test_status_moves_never_receive_stab(self):
        print("\n--- 5. Testing Status Moves STAB Immunity ---")
        # Rain Dance on Water-type Pelipper
        stab_mult, note = get_stab_multiplier(["water", "flying"], "water", "Status")
        self.assertEqual(stab_mult, 1.0)
        self.assertIsNone(note)
        # Tailwind on Flying-type Kilowattrel
        stab_mult_tw, note_tw = get_stab_multiplier(["electric", "flying"], "flying", "Status")
        self.assertEqual(stab_mult_tw, 1.0)
        self.assertIsNone(note_tw)
        # Damaging attack DOES receive STAB
        stab_surf, note_surf = get_stab_multiplier(["water", "flying"], "water", "Special")
        self.assertEqual(stab_surf, 1.5)
        self.assertIsNotNone(note_surf)
        print("[OK] Verified: Status moves strictly receive 1.0 STAB multiplier (Zero STAB damage claim).")

    # -------------------------------------------------------------
    # 4. ITEM RESTRICTION TESTS
    # -------------------------------------------------------------
    def test_item_restrictions(self):
        print("\n--- 6. Testing Item Constraints (Assault Vest, Choice) ---")
        # Assault Vest strictly bans Status moves
        self.assertEqual(evaluate_item_restrictions("assaultvest", "Status"), -999.0)
        self.assertEqual(evaluate_item_restrictions("assaultvest", "Physical"), 0.0)
        # Recommendation with Assault Vest rejects status
        res = recommend_moveset("Swampert", item="Assault Vest", format_name="gen9ou")
        for m in res["recommended_moves"]:
            self.assertNotEqual(m["category"], "Status", f"Status move {m['name']} found on Assault Vest set!")
        print("[OK] Verified: Assault Vest bans status moves across all recommendations.")

    # -------------------------------------------------------------
    # 5. STAT CATEGORY ALIGNMENT TESTS
    # -------------------------------------------------------------
    def test_physical_special_stat_alignment(self):
        print("\n--- 7. Testing Physical/Special Stat Alignment ---")
        # Iron Hands: Base Atk 140, Base SpA 50
        res = recommend_moveset("Iron-Hands", archetype="rain", format_name="gen9ou")
        rec_move_ids = [m["id"] for m in res["recommended_moves"]]
        # Must NOT recommend Special Thunder on 50 SpA Iron Hands
        self.assertNotIn("thunder", rec_move_ids)
        self.assertTrue(any(m in rec_move_ids for m in ["drainpunch", "closecombat", "wildcharge", "icepunch", "heavyslam"]))
        print(f"Iron Hands recommended moves: {[m['name'] for m in res['recommended_moves']]}")
        print("[OK] Verified: Physical attacker Iron Hands does not get Special Thunder in Rain.")

    # -------------------------------------------------------------
    # 6. RAIN TEAM FULL INTEGRATION TEST
    # -------------------------------------------------------------
    def test_rain_team_comprehensive_audit(self):
        print("\n--- 8. Testing Rain Team Integration (Pelipper, Archaludon, Swampert, Overqwil, Kilowattrel, Iron Hands) ---")
        rain_team = ["Pelipper", "Archaludon", "Swampert", "Overqwil", "Kilowattrel", "Iron-Hands"]
        
        # Archaludon must get Electro Shot
        arch_res = recommend_moveset("Archaludon", archetype="rain", teammates=rain_team, format_name="gen9ou")
        arch_move_ids = [m["id"] for m in arch_res["recommended_moves"]]
        self.assertIn("electroshot", arch_move_ids, "Archaludon must be recommended signature Electro Shot in Rain!")
        electro_shot = next(m for m in arch_res["recommended_moves"] if m["id"] == "electroshot")
        self.assertTrue("1 turn" in electro_shot["rationale"] or "Rain" in electro_shot["rationale"])
        print(f"Archaludon moves: {[m['name'] for m in arch_res['recommended_moves']]}")
        print(f"Electro Shot rationale: {electro_shot['rationale']}")

        # Pelipper is Weather Setter -> Gets Damp Rock, Hurricane, Surf/Hydro Pump
        pel_res = recommend_moveset("Pelipper", archetype="rain", teammates=rain_team, format_name="gen9ou")
        self.assertIn("Damp Rock", pel_res["recommended_items"])
        pel_move_ids = [m["id"] for m in pel_res["recommended_moves"]]
        self.assertIn("hurricane", pel_move_ids)

        # Swampert & Overqwil are Swift Swimmers -> Must NOT get Rain Dance
        swamp_res = recommend_moveset("Swampert", archetype="rain", teammates=rain_team, format_name="gen9ou")
        swamp_move_ids = [m["id"] for m in swamp_res["recommended_moves"]]
        self.assertNotIn("raindance", swamp_move_ids, "Swift Swim Swampert must not be recommended manual Rain Dance!")

        overqwil_res = recommend_moveset("Overqwil", archetype="rain", teammates=rain_team, format_name="gen9ou")
        overqwil_move_ids = [m["id"] for m in overqwil_res["recommended_moves"]]
        self.assertNotIn("raindance", overqwil_move_ids, "Swift Swim Overqwil must not be recommended manual Rain Dance!")

        # Optimizer Strategy Preservation: Must NOT suggest Fire-types (like Cinderace) on Rain team
        opt_res = optimize_team(team=rain_team, df_pokemon=self.df_pokemon, df_types=self.df_types, format_name="gen9ou", target_archetype="rain")
        suggested_adds = [s["add_pokemon_raw"].lower() for s in opt_res.get("suggestions", [])]
        self.assertNotIn("cinderace", suggested_adds, "Optimizer must not suggest Fire-type Cinderace on Rain team!")
        print(f"Optimizer Suggestions for Rain Team: {[s['add_pokemon'] for s in opt_res.get('suggestions', [])]}")
        print("[OK] Verified: Archaludon gets Electro Shot, Swift Swimmers do not get Rain Dance, Optimizer preserves Rain strategy.")

    # -------------------------------------------------------------
    # 7. NON-RAIN ARCHETYPE TESTS (SUN, TRICK ROOM, SNOW)
    # -------------------------------------------------------------
    def test_non_rain_archetypes(self):
        print("\n--- 9. Testing Non-Rain Archetypes (Sun, Trick Room, Snow) ---")
        # Sun: Venusaur gets Growth + Weather Ball / Solar Beam
        sun_team = ["Torkoal", "Walking-Wake", "Venusaur", "Great-Tusk", "Raging-Bolt", "Roaring-Moon"]
        ven_res = recommend_moveset("Venusaur", ability="chlorophyll", archetype="sun", teammates=sun_team, format_name="gen9ou")
        ven_move_ids = [m["id"] for m in ven_res["recommended_moves"]]
        self.assertTrue(any(m in ven_move_ids for m in ["weatherball", "solarbeam", "growth", "gigadrain", "sludgebomb"]))
        print(f"Venusaur in Sun: {[m['name'] for m in ven_res['recommended_moves']]}")

        # Snow: Ninetales-Alola gets Aurora Veil + Blizzard
        snow_team = ["Ninetales-Alola", "Baxcalibur", "Cetitan", "Gholdengo", "Ting-Lu", "Slowking-Galar"]
        nine_res = recommend_moveset("Ninetales-Alola", ability="snowwarning", archetype="snow", teammates=snow_team, format_name="gen9ou")
        nine_move_ids = [m["id"] for m in nine_res["recommended_moves"]]
        self.assertIn("auroraveil", nine_move_ids)
        self.assertIn("blizzard", nine_move_ids)
        print(f"Ninetales-Alola in Snow: {[m['name'] for m in nine_res['recommended_moves']]}")

        # Trick Room: Ursaluna (Speed 50) gets physical attacks + Facade
        tr_team = ["Hatterene", "Ursaluna", "Torkoal", "Kingambit", "Porygon2", "Cresselia"]
        ursa_res = recommend_moveset("Ursaluna", ability="guts", archetype="trick_room", teammates=tr_team, format_name="gen9ou")
        ursa_move_ids = [m["id"] for m in ursa_res["recommended_moves"]]
        self.assertTrue(any(m in ursa_move_ids for m in ["headlongrush", "earthquake", "facade", "firepunch", "swordsdance"]))
        print(f"Ursaluna in Trick Room: {[m['name'] for m in ursa_res['recommended_moves']]}")
        print("[OK] Verified: Sun, Snow, and Trick Room archetypes receive mechanically tailored movesets.")

if __name__ == "__main__":
    unittest.main()
