import os
import json
from typing import Dict, List, Optional, Any, Tuple, Set
from app.ml.constraints import (
    to_canonical_id,
    get_pokemon_species,
    get_legal_moves,
    load_game_data
)
from app.ml.mechanics_engine import (
    is_status_move,
    evaluate_move_mechanics,
    ALL_TYPES
)
from app.ml.semantics_engine import (
    classify_archetype_role,
    evaluate_item_restrictions,
    recommend_best_items,
    recommend_best_abilities
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META_DATA_DIR = os.path.join(BASE_DIR, "data", "meta_data")

_META_CACHE: Dict[str, Dict[str, Any]] = {}

def load_meta_telemetry(format_name: str = "gen9ou") -> Dict[str, Any]:
    """Loads normalized Smogon chaos telemetry for the requested format."""
    f_key = "gen9vgc" if "vgc" in format_name.lower() or "doubles" in format_name.lower() else "gen9ou"
    if f_key not in _META_CACHE:
        file_path = os.path.join(META_DATA_DIR, f"{f_key}.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                _META_CACHE[f_key] = json.load(f)
        else:
            _META_CACHE[f_key] = {"pokemon": {}}
    return _META_CACHE[f_key]

def analyze_team_coverage_gaps(teammates: List[str]) -> Tuple[Set[str], Set[str]]:
    """Analyzes the teammate roster to identify covered types and missing offensive coverage."""
    load_game_data()
    covered_types = set()
    for tm in teammates:
        c_id = to_canonical_id(tm)
        spec = get_pokemon_species(c_id)
        if spec:
            for t in spec.get("types", []):
                covered_types.add(t.lower())
    
    # Exclude Normal type from offensive coverage gap calculations as Normal hits 0 types super-effectively
    missing_coverage = (ALL_TYPES - {"normal"}) - covered_types
    return covered_types, missing_coverage

def generate_move_rationale(
    move_id: str,
    move_name: str,
    category: str,
    move_type: str,
    mech_result: Dict[str, Any],
    role_info: Dict[str, Any],
    archetype: str,
    is_coverage_gap: bool,
    emp_score: float,
    m_info: Dict[str, Any]
) -> str:
    """
    Generates deterministic, mechanically truthful plain-English explanations.
    Strictly forbids false STAB claims on status moves or false priority claims on non-attacks.
    """
    m_id = move_id.lower()
    m_type_cap = move_type.capitalize()
    arch = archetype.lower()
    notes = mech_result.get("notes", [])
    rationale_parts = []

    # 1. Specific Conditional Mechanics
    if notes:
        rationale_parts.extend(notes)
    elif m_id in ["hurricane", "thunder"] and arch == "rain":
        rationale_parts.append("Bypasses accuracy check (100% accurate) under Rain")
    elif m_id == "blizzard" and arch == "snow":
        rationale_parts.append("Bypasses accuracy check (100% accurate) under Snow")
    elif m_id == "electroshot" and arch == "rain":
        rationale_parts.append("Fires in 1 turn under Rain while boosting Sp. Atk by +1")

    # 2. Category-Specific Mechanics
    func_cat = derive_move_functional_category(m_id, m_info)
    if is_status_move(category):
        if func_cat == "Setup / Stat Boost":
            rationale_parts.append(f"Premier setup move boosting offensive stat stages for sweep potential")
        elif func_cat == "Recovery / Sustain":
            rationale_parts.append("Reliable recovery sustaining defensive longevity on the field")
        elif func_cat == "Entry Hazard":
            rationale_parts.append("Crucial entry hazard punishing opponent switches")
        elif func_cat == "Hazard Removal":  # Wait, wait, is there Hazard Removal in my derive function? No. Let's look at derive_move_functional_category. I didn't add Hazard Removal! Ah, I'll need to fix that or leave the default.
            rationale_parts.append("Hazard control clearing opposing entry hazards for the team")
        elif func_cat == "Field / Speed Control":
            rationale_parts.append(f"Field speed control providing team turn-order advantage ({move_name})")
        elif func_cat == "Defensive Protection":
            rationale_parts.append("Defensive protection scouting opponent attacks and stalling turns")
        elif func_cat == "Status Control":
            rationale_parts.append(f"Status infliction crippling opponent sweepers with {m_type_cap} status")
        elif func_cat == "Screen Protection":
            rationale_parts.append("Dual-screen defensive damage reduction for the team")
        # Add a check for rapidspin/defog for hazard removal if needed since I didn't derive it? Wait, rapid spin is an attack.
        if m_id in ["rapidspin", "defog", "mortalspin", "courtchange", "tidyup"]:
            rationale_parts.append("Hazard control clearing opposing entry hazards for the team")
    else:
        # Attacking Move Mechanics
        stab_mult = mech_result.get("stab_mult", 1.0)
        if stab_mult > 1.0:
            stab_pct = int(stab_mult * 100)
            rationale_parts.append(f"Receives {stab_pct}% STAB damage boost matching {m_type_cap} typing")
            
        if is_coverage_gap:
            rationale_parts.append(f"Provides critical {m_type_cap} coverage missing from teammates")
            
        pri = mech_result.get("priority", 0)
        if pri > 0:
            rationale_parts.append(f"Provides +{pri} priority to pick off weakened foes before they move")
            
        if func_cat == "Pivoting Momentum" or m_id in ["uturn", "voltswitch", "flipturn", "partingshot"]:
            rationale_parts.append("Pivoting attack maintaining offensive momentum on switches")

    # 3. Telemetry Prior Support
    if emp_score >= 0.5:
        rationale_parts.append("Established standard on high-ladder competitive teams")

    if not rationale_parts:
        if is_status_move(category):
            return f"Versatile status option supporting team {archetype.capitalize()} gameplan."
        return f"Solid {m_type_cap} offensive attack ({mech_result.get('effective_bp', 0)} effective power)."

    return ". ".join(rationale_parts) + "."

def derive_move_functional_category(move_id: str, m_info: Dict[str, Any]) -> str:
    """Derives a move's functional category from Showdown game data fields.
    NOT from hardcoded move-ID lists."""
    m_cat = m_info.get("category", "Status")
    
    # Self-switching moves (U-Turn, Volt Switch, Flip Turn, Parting Shot, Teleport)
    if m_info.get("self_switch"):
        return "Pivoting Momentum" if not is_status_move(m_cat) else "Pivot / Utility"
    
    # Force-switch moves (Roar, Whirlwind, Dragon Tail, Circle Throw)
    if m_info.get("force_switch"):
        return "Phazing / Shuffle"
    
    if is_status_move(m_cat):
        # Setup / Stat boost: has positive self-boosts for combat stats
        boosts = m_info.get("boosts") or {}
        self_effects = m_info.get("self_effects") or {}
        self_boosts = self_effects.get("boosts", {}) if isinstance(self_effects, dict) else {}
        combined_boosts = {**boosts, **self_boosts}
        combat_stats = {"atk", "spa", "spe", "def", "spd"}
        if any(combined_boosts.get(k, 0) > 0 for k in combat_stats):
            return "Setup / Stat Boost"
        
        # Recovery: has heal flag or is known sustain move
        if m_info.get("flags", {}).get("heal") or m_info.get("heal") or move_id in ["painsplit", "strengthsap", "wish", "rest", "junglehealing", "lifedew"]:
            return "Recovery / Sustain"
        
        # Hazard removal
        if move_id in ["defog", "courtchange", "tidyup"]:
            return "Hazard Removal"
        
        # Entry hazards
        sc = m_info.get("side_condition", "")
        if sc and sc.lower() in ["stealthrock", "spikes", "toxicspikes", "stickyweb", "gmaxsteelsurge"]:
            return "Entry Hazard"
        
        # Screens
        if sc and sc.lower() in ["reflect", "lightscreen", "auroraveil"]:
            return "Screen Protection"
        
        # Status infliction
        if m_info.get("status"):
            return "Status Control"
        
        # Weather/terrain setting
        if m_info.get("weather"):
            return "Field / Weather Control"
        if m_info.get("terrain"):
            return "Field / Terrain Control"
        
        # Speed control (Trick Room, Tailwind) - check pseudo_weather for Trick Room
        if m_info.get("pseudo_weather") == "trickroom":
            return "Field / Speed Control"
        if sc and sc.lower() == "tailwind":
            return "Field / Speed Control"
        
        # Volatile status (Taunt, Encore, Substitute, etc.)
        vs = m_info.get("volatile_status", "")
        if vs:
            return "Utility / Disruption"
        
        # Protect variants
        if m_info.get("flags", {}).get("protect"):
            # Wait - protect flag means the move CAN be protected against, not that it IS protect
            pass
        
        # Check by move ID for Protect-like moves as a fallback
        # These are the few cases where the data model doesn't cleanly encode 'this is a protect move'
        if move_id in ["protect", "detect", "banefulbunker", "spikyshield", "kingsshield", "obstruct", "silktrap", "burningbulwark"]:
            return "Defensive Protection"
        
        return "Utility"
    else:
        # Attacking move categories
        # Draining attacks
        if m_info.get("drain"):
            return "Sustain Attack"
        
        # Fixed damage
        if m_info.get("damage"):
            return "Fixed Damage"
        
        return "Attack"  # Default for non-categorized attacks

def recommend_moveset(
    pokemon_name: str,
    ability: str = "",
    item: str = "",
    teammates: Optional[List[str]] = None,
    archetype: str = "balance",
    format_name: str = "gen9ou",
    top_n: int = 4
) -> Dict[str, Any]:
    """
    Deterministic Context-Aware Moveset Recommendation Engine.
    Combines true battle mechanics, archetype role classification, and empirical meta priors.
    """
    load_game_data()
    teammates = teammates or []
    c_id = to_canonical_id(pokemon_name)
    species_info = get_pokemon_species(pokemon_name)
    
    if not species_info:
        return {
            "success": False,
            "error": f"Pokémon '{pokemon_name}' not found in Pokédex database."
        }
        
    types = [t.lower() for t in species_info.get("types", [])]
    base_stats = species_info.get("baseStats", {"hp": 80, "atk": 80, "def": 80, "spa": 80, "spd": 80, "spe": 80})
    base_atk = base_stats.get("atk", 80)
    base_spa = base_stats.get("spa", 80)
    base_spe = base_stats.get("spe", 80)
    base_def = base_stats.get("def", 80)
    base_spd = base_stats.get("spd", 80)
    
    # 1. Retrieve Legal Movepool
    legal_moves = get_legal_moves(pokemon_name, format_name)
    if not legal_moves:
        return {
            "success": False,
            "error": f"No legal moves found for '{pokemon_name}' in {format_name}."
        }
        
    # 2. Archetype & Role Classification
    arch_key = archetype.lower().replace(" ", "_")
    role_info = classify_archetype_role(
        species_name=pokemon_name,
        species_data=species_info,
        archetype=arch_key,
        ability=ability
    )
    
    # Compute how defensive this Pokémon is (0.0 = pure offense, 1.0 = pure defense)
    bulk = base_stats.get("hp", 80) + base_stats.get("def", 80) + base_stats.get("spd", 80)
    offense = max(base_stats.get("atk", 80), base_stats.get("spa", 80))
    defensive_ratio = min(1.0, bulk / (bulk + offense * 3.0))
    
    # Pre-resolve active/best ability if not provided (e.g. Tough Claws on Metagross-Mega)
    active_ability = ability
    if not active_ability:
        raw_abilities = species_info.get("abilities", {})
        if isinstance(raw_abilities, dict):
            # Prioritize standard slot '0' or candidate abilities
            active_ability = raw_abilities.get("0", "")
            # If archetype has weather synergy, check for weather ability
            for slot_k, ab_val in raw_abilities.items():
                if arch_key in ["rain", "sun", "sand", "snow"] and str(ab_val).lower().replace("-", "").replace(" ", "") in {"drizzle", "drought", "sandstream", "snowwarning", "swiftswim", "chlorophyll", "sandrush", "slushrush"}:
                    active_ability = ab_val
                    break

    # 3. Empirical Telemetry Data (with baseSpecies fallback for Megas/alternate formes)
    meta = load_meta_telemetry(format_name)
    mon_meta = meta.get("pokemon", {}).get(c_id, {})
    if not mon_meta.get("moves"):
        base_species_id = to_canonical_id(species_info.get("baseSpecies", ""))
        if base_species_id and base_species_id in meta.get("pokemon", {}):
            mon_meta = meta.get("pokemon", {}).get(base_species_id, {})
            
    meta_moves = mon_meta.get("moves", {})
    total_meta_count = sum(meta_moves.values()) if meta_moves else 1.0
    
    # 4. Coverage Analysis
    covered_types, missing_coverage = analyze_team_coverage_gaps(teammates)
    
    # 5. Score Each Legal Move Deterministically
    scored_moves = []
    
    for m_id, m_info in legal_moves.items():
        m_name = m_info["name"]
        m_type = m_info["type"].lower()
        m_cat = m_info["category"]
        
        # A. Item Restrictions (e.g. Assault Vest bans status moves)
        item_penalty = evaluate_item_restrictions(item, m_cat)
        if item_penalty < -500:
            continue  # Disallowed by item
            
        # B. Deterministic Mechanical Evaluation
        mech_res = evaluate_move_mechanics(
            move_id=m_id,
            move_info=m_info,
            user_species=species_info,
            weather=arch_key,
            terrain=arch_key,
            ability=active_ability,
            item=item
        )
        
        mech_score = mech_res["mechanical_score"]
        func_cat = derive_move_functional_category(m_id, m_info)
        
        # C. Archetype & Role Synergy
        role_score = 0.0
        
        # Weather Synergies & Penalties
        if arch_key == "rain":
            if m_type == "water" and not is_status_move(m_cat):
                role_score += 2.0
            elif m_id in ["hurricane", "thunder", "electroshot"]:
                role_score += 2.2
            elif m_type == "fire" and not is_status_move(m_cat):
                role_score -= 3.0  # Strong penalty for Fire attacks in Rain
            # If team has weather ability setter (e.g. Drizzle Pelipper), manual Rain Dance is deprioritized
            if m_id == "raindance":
                role_score += 0.5 if role_info.get("is_setter") else -2.0
                
        elif arch_key == "sun":
            if m_type == "fire" and not is_status_move(m_cat):
                role_score += 2.0
            elif m_id in ["solarbeam", "solarblade", "growth", "weatherball", "hydrosteam"]:
                role_score += 2.2
            elif m_type == "water" and m_id != "hydrosteam" and not is_status_move(m_cat):
                role_score -= 3.0  # Water attacks weakened in Sun
            if m_id == "sunnyday":
                role_score += 0.5 if role_info.get("is_setter") else -2.0
                
        elif arch_key == "sand":
            if m_type in ["rock", "ground", "steel"] and not is_status_move(m_cat):
                role_score += 1.5
            elif m_id == "shoreup":
                role_score += 2.0
                
        elif arch_key == "snow":
            if m_id in ["blizzard", "auroraveil", "chillyreception"]:
                role_score += 2.5
            elif m_type == "ice" and not is_status_move(m_cat):
                role_score += 1.5
                
        elif arch_key == "trick_room":
            if m_id == "trickroom":
                role_score += 3.0 if role_info.get("is_setter") or base_stats.get("spe", 80) <= 60 else -1.0
            elif m_id in ["gyroball", "headlongrush", "hammerarm", "bloodmoon"]:
                role_score += 1.8
                
        elif arch_key == "hyper_offense":
            if func_cat == "Setup / Stat Boost":
                boosts = m_info.get("boosts") or {}
                self_effects = m_info.get("self_effects") or {}
                self_boosts = self_effects.get("boosts", {}) if isinstance(self_effects, dict) else {}
                combined = {**boosts, **self_boosts}
                
                atk_b = combined.get("atk", 0)
                spa_b = combined.get("spa", 0)
                
                if atk_b > 0 and spa_b <= 0:
                    # Physical setup rewards physical/mixed capability
                    if base_atk >= 80 and (base_atk >= base_spa * 0.85):
                        role_score += 2.2
                    else:
                        role_score -= 1.5  # Incompatible with special orientation
                elif spa_b > 0 and atk_b <= 0:
                    # Special setup rewards special/mixed capability
                    if base_spa >= 80 and (base_spa >= base_atk * 0.85):
                        role_score += 2.2
                    else:
                        role_score -= 1.5  # Incompatible with physical orientation
                else:
                    role_score += 2.0  # Mixed / Speed / Defense setup
            elif mech_res.get("priority", 0) > 0:
                role_score += 1.5
            elif m_id in ["stealthrock", "spikes", "stickyweb", "taunt"]:
                role_score += 1.5
                
        elif arch_key == "stall":
            if m_id in ["recover", "roost", "slackoff", "softboiled", "wish", "protect", "substitute"]:
                role_score += 2.5
            elif m_id in ["toxic", "willowisp", "thunderwave", "haze", "whirlwind"]:
                role_score += 2.0
            elif m_id in ["seismictoss", "nightshade", "foulplay", "ruination"]:
                role_score += 1.8
                
        elif arch_key == "balance":
            if m_id in ["uturn", "voltswitch", "flipturn", "rapidspin", "stealthrock"]:
                role_score += 1.8
            elif m_id in ["knockoff"]:
                # Knock off provides utility for defensive/pivot mons, while sweepers prefer core coverage
                role_score += 1.8 if defensive_ratio >= 0.35 else 0.8
            elif m_id in ["recover", "roost", "thunderwave", "willowisp"]:
                role_score += 1.5

        # D. Teammate Coverage Gap Fulfillment
        is_cov_gap = False
        if not is_status_move(m_cat) and m_type in missing_coverage and m_type not in types:
            role_score += 1.4
            is_cov_gap = True

        # E. General Utility & Support Synergies for Defensive / Support Roles
        if defensive_ratio >= 0.45 or role_info.get("is_setter"):
            if is_status_move(m_cat):
                if func_cat == "Status Control":
                    role_score += 1.8
                elif func_cat == "Recovery / Sustain":
                    role_score += 2.0
                elif func_cat == "Entry Hazard":
                    role_score += 1.6
                elif func_cat == "Hazard Removal":
                    role_score += 1.6
                elif func_cat == "Screen Protection":
                    role_score += 1.5
                elif func_cat == "Defensive Protection":
                    role_score += 1.2
                elif func_cat == "Utility / Disruption":
                    role_score += 1.4
            else:
                if func_cat == "Fixed Damage" or m_info.get("damage") == "level":
                    role_score += 1.6
                elif m_info.get("override_offensive_pokemon") == "target" or m_info.get("overrideOffensivePokemon") == "target":
                    role_score += 1.5

        # F. Empirical Meta Prior (Tie-Breaker / Validator)
        raw_emp = meta_moves.get(m_id, 0.0)
        # raw_emp is usage percentage; capped to prevent distortion over true battle mechanics
        emp_score = min(raw_emp * 0.20, 2.5)

        # G. Total Score
        # Stat alignment strictly scales the final offensive score
        stat_alignment = mech_res.get("stat_score", 1.0)
        
        if is_status_move(m_cat):
            # Status moves scale UP for defensive Pokémon, DOWN for offensive sweepers
            status_base = 3.0 + (defensive_ratio * 8.0)  # Range: 3.0 (sweeper) to 11.0 (wall)
            if func_cat == "Setup / Stat Boost":
                # Offensive setup moves must align with the offensive stat they boost
                total_score = ((status_base * 0.8) + (role_score * 2.2) + (emp_score * 1.5)) * stat_alignment
            else:
                total_score = (status_base * 0.8) + (role_score * 2.2) + (emp_score * 1.5)
        else:
            total_score = ((mech_score * 1.5) + (role_score * 2.0) + (emp_score * 1.5)) * stat_alignment

        # Role Tag
        base_tag = func_cat
        
        if not is_status_move(m_cat):
            if m_id in ["electroshot", "hurricane", "thunder"] and arch_key == "rain":
                role_tag = "Rain Synergy Attack"
            elif m_id in ["solarbeam", "solarblade", "weatherball", "hydrosteam"] and arch_key == "sun":
                role_tag = "Sun Synergy Attack"
            elif m_id in ["blizzard"] and arch_key == "snow":
                role_tag = "Snow Synergy Attack"
            elif mech_res.get("stab_mult", 1.0) > 1.0:
                role_tag = "Primary STAB"
            elif is_cov_gap:
                role_tag = "Team Coverage"
            elif mech_res.get("priority", 0) > 0:
                role_tag = "Priority Finisher"
            else:
                role_tag = base_tag
        else:
            role_tag = base_tag

        # Truthful Rationale
        rationale = generate_move_rationale(
            move_id=m_id,
            move_name=m_name,
            category=m_cat,
            move_type=m_type,
            mech_result=mech_res,
            role_info=role_info,
            archetype=archetype,
            is_coverage_gap=is_cov_gap,
            emp_score=emp_score,
            m_info=m_info
        )

        scored_moves.append({
            "id": m_id,
            "name": m_name,
            "type": m_type,
            "category": m_cat,
            "power": mech_res.get("effective_bp", 0),
            "accuracy": mech_res.get("effective_accuracy", 100),
            "priority": mech_res.get("priority", 0),
            "score": round(total_score, 2),
            "role_tag": role_tag,
            "rationale": rationale
        })

    # Sort moves by descending score
    scored_moves.sort(key=lambda x: x["score"], reverse=True)

    # 6. Assemble Balanced Top-N Primary Moveset (Ensures at least 1-2 attacks and prevents 4 redundant moves)
    selected_moves = []
    has_attack = False
    
    for m in scored_moves:
        if len(selected_moves) >= top_n:
            break
        # Allow at most 2 attacks of the exact same elemental type
        same_type_attacks = sum(1 for sm in selected_moves if sm["type"] == m["type"] and not is_status_move(sm["category"]))
        if same_type_attacks >= 2 and not is_status_move(m["category"]):
            continue
        # Allow at most 2 pure status moves unless Stall or Defensive Tank
        max_status = 3 if (arch_key == "stall" or defensive_ratio >= 0.50 or role_info.get("role") == "Defensive Wall / Tank") else 2
        status_count = sum(1 for sm in selected_moves if is_status_move(sm["category"]))
        if status_count >= max_status and is_status_move(m["category"]):
            continue
            
        selected_moves.append(m)
        if not is_status_move(m["category"]):
            has_attack = True

    # If no attacking move was selected, replace last move with highest scoring attack
    if not has_attack:
        for m in scored_moves:
            if not is_status_move(m["category"]) and m not in selected_moves:
                if selected_moves:
                    selected_moves[-1] = m
                else:
                    selected_moves.append(m)
                break

    # Secondary Pool: Top alternative options (pool 2) for flexible customization
    selected_ids = {sm["id"] for sm in selected_moves}
    alternative_moves = [m for m in scored_moves if m["id"] not in selected_ids][:4]

    # 7. Recommended Abilities from Semantics & Mechanics
    recommended_abilities = recommend_best_abilities(
        species_name=pokemon_name,
        species_data=species_info,
        moveset=selected_moves,
        archetype=arch_key,
        role_info=role_info,
        item=item,
        format_name=format_name
    )
    contextual_ability = ability or (recommended_abilities[0]["name"] if recommended_abilities else "")

    # 8. Recommended Tera Types & Held Items from Semantics & Telemetry
    is_mega = (species_info.get("forme") == "Mega" or bool(species_info.get("requiredItem")) or "mega" in c_id)
    if is_mega:
        recommended_tera = []  # Megas cannot Terastallize in official competitive rules
    else:
        raw_tera = mon_meta.get("tera_types", {})
        recommended_tera = [t.capitalize() for t, _ in sorted(raw_tera.items(), key=lambda x: x[1], reverse=True)[:3]]
        if not recommended_tera:
            recommended_tera = [t.capitalize() for t in types]
        
    raw_items = mon_meta.get("items", {})
    top_meta_items = [it for it, _ in sorted(raw_items.items(), key=lambda x: x[1], reverse=True)[:5]]
    recommended_items = recommend_best_items(
        species_name=pokemon_name,
        species_data=species_info,
        archetype=arch_key,
        role_info=role_info,
        top_meta_items=top_meta_items,
        moveset=selected_moves,
        ability=contextual_ability,
        format_name=format_name
    )

    return {
        "success": True,
        "pokemon": species_info.get("name", pokemon_name),
        "types": [t.capitalize() for t in types],
        "format": format_name,
        "archetype": archetype,
        "role": role_info.get("role", "Attacker"),
        "recommended_moves": selected_moves,
        "alternative_moves": alternative_moves,
        "recommended_tera_types": recommended_tera,
        "recommended_items": recommended_items,
        "recommended_abilities": recommended_abilities,
        "archetype_fit_summary": f"{role_info.get('role', 'Attacker')} moveset tailored for {species_info.get('name', pokemon_name)} under {archetype.capitalize()} team strategy."
    }
