import os
import json
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from app.ml.synergy import analyze_team_synergy
from app.ml.recommender import load_meta_telemetry, recommend_moveset
from app.ml.constraints import to_canonical_id, get_pokemon_species, load_game_data
from app.ml.semantics_engine import (
    WEATHER_SETTER_ABILITIES,
    WEATHER_ABUSER_ABILITIES,
    TERRAIN_SETTER_ABILITIES,
    TERRAIN_ABUSER_ABILITIES
)
from app.core.utils import get_pokemon_data

def evaluate_candidate_archetype_harmony(
    candidate_name: str,
    species_info: Dict[str, Any],
    target_archetype: str
) -> Tuple[float, List[str]]:
    """
    Evaluates whether a candidate Pokémon strengthens or destroys the team's active archetype strategy.
    Returns (harmony_modifier, list_of_reasons).
    """
    arch = str(target_archetype).strip().lower().replace(" ", "_")
    types = [t.lower() for t in species_info.get("types", [])]
    abilities = [str(a).lower() for a in species_info.get("abilities", {}).values()] if isinstance(species_info.get("abilities"), dict) else []
    base_stats = species_info.get("baseStats", {"hp": 80, "atk": 80, "def": 80, "spa": 80, "spd": 80, "spe": 80})
    spe = base_stats.get("spe", 80)
    
    mod = 0.0
    reasons = []

    # 1. Rain Archetype
    if arch == "rain":
        if any(a in WEATHER_SETTER_ABILITIES["rain"] for a in abilities):
            mod += 10.0
            reasons.append("Brings Drizzle weather-setting ability to power team rain strategy")
        elif any(a in WEATHER_ABUSER_ABILITIES["rain"] for a in abilities):
            mod += 8.0
            reasons.append("Possesses Swift Swim/Rain ability doubling speed or recovering under Rain")
        elif "water" in types:
            mod += 4.0
            reasons.append("Water STAB attacks receive 1.5x damage boost under Rain")
        elif any(t in ["electric", "flying", "steel", "dragon"] for t in types):
            mod += 3.0
            reasons.append("Synergizes with Rain defense and perfect accuracy Thunder/Hurricane")
            
        # Severe anti-synergy: Fire Pokémon in Rain
        if "fire" in types and "water" not in types:
            mod -= 18.0
            reasons.append("Fire STAB damage is halved (0.5x) in Rain, causing severe strategic anti-synergy")
        # Disqualify conflicting weather setters
        if any(a in WEATHER_SETTER_ABILITIES["sun"] | WEATHER_SETTER_ABILITIES["snow"] | WEATHER_SETTER_ABILITIES["sand"] for a in abilities):
            mod -= 25.0
            reasons.append("Summons conflicting weather that overrides Rain")

    # 2. Sun Archetype
    elif arch == "sun":
        if any(a in WEATHER_SETTER_ABILITIES["sun"] for a in abilities):
            mod += 10.0
            reasons.append("Brings Drought weather-setting ability")
        elif any(a in WEATHER_ABUSER_ABILITIES["sun"] for a in abilities):
            mod += 8.0
            reasons.append("Directly activates Chlorophyll or Protosynthesis in Sun")
        elif "fire" in types:
            mod += 5.0
            reasons.append("Fire STAB attacks receive 1.5x damage boost under Sun")
        elif "grass" in types:
            mod += 4.0
            reasons.append("Executes 1-turn Solar Beam and boosted Growth in Sun")
            
        if "water" in types:
            mod -= 18.0
            reasons.append("Water STAB damage is halved (0.5x) in Harsh Sunlight")
        if any(a in WEATHER_SETTER_ABILITIES["rain"] | WEATHER_SETTER_ABILITIES["snow"] for a in abilities):
            mod -= 25.0
            reasons.append("Summons conflicting weather that overrides Sun")

    # 3. Sand Archetype
    elif arch == "sand":
        if any(a in WEATHER_SETTER_ABILITIES["sand"] for a in abilities):
            mod += 10.0
            reasons.append("Sets Sandstorm for the team")
        elif any(a in WEATHER_ABUSER_ABILITIES["sand"] for a in abilities):
            mod += 8.0
            reasons.append("Sand Rush / Sand Force abuser in Sandstorm")
        elif "rock" in types:
            mod += 6.0
            reasons.append("Gains 1.5x Special Defense boost in Sandstorm")
        elif any(t in ["ground", "steel"] for t in types):
            mod += 4.0
            reasons.append("Immune to Sandstorm residual chip damage")

    # 4. Snow Archetype
    elif arch == "snow":
        if any(a in WEATHER_SETTER_ABILITIES["snow"] for a in abilities):
            mod += 10.0
            reasons.append("Sets Snow for the team")
        elif any(a in WEATHER_ABUSER_ABILITIES["snow"] for a in abilities):
            mod += 8.0
            reasons.append("Slush Rush speed abuser in Snow")
        elif "ice" in types:
            mod += 6.0
            reasons.append("Gains 1.5x physical Defense boost in Snow")

    # 5. Trick Room Archetype
    elif arch == "trick_room":
        if spe <= 50 and max(base_stats.get("atk", 80), base_stats.get("spa", 80)) >= 105:
            mod += 8.0
            reasons.append(f"Low speed ({spe}) allows moving first under Trick Room")
        elif spe >= 105:
            mod -= 15.0
            reasons.append(f"High speed ({spe}) is severely penalized when Trick Room reverses turn order")

    # 6. Hyper Offense Archetype
    elif arch == "hyper_offense":
        if spe >= 100 or max(base_stats.get("atk", 80), base_stats.get("spa", 80)) >= 120:
            mod += 5.0
            reasons.append("Fast, high-octane offensive sweeper keeping relentless momentum")

    # 7. Stall Archetype
    elif arch == "stall":
        if (base_stats.get("hp", 80) + base_stats.get("def", 80) + base_stats.get("spd", 80)) >= 290:
            mod += 6.0
            reasons.append("Formidable defensive bulk absorbing repeated offensive pressure")

    return mod, reasons

def optimize_team(
    team: List[str],
    df_pokemon: pd.DataFrame,
    df_types: pd.DataFrame,
    format_name: str = "gen9ou",
    target_archetype: Optional[str] = None
) -> Dict[str, Any]:
    """
    Strategy-Preserving Team Optimizer Engine.
    Audits team for tactical gaps and evaluates candidate replacements strictly under the active archetype.
    """
    load_game_data()
    if len(team) != 6:
        return {
            "success": False,
            "error": "Team must contain exactly 6 Pokémon for optimization."
        }
        
    normalized_team = [p.lower().replace(" ", "-") for p in team]
    valid_names = set(df_pokemon["name"])
    invalid = [p for p in normalized_team if p not in valid_names]
    if invalid:
        return {
            "success": False,
            "error": f"Invalid Pokémon detected in team: {invalid}"
        }
        
    # 1. Baseline Team Synergy Analysis
    baseline_synergy = analyze_team_synergy(normalized_team, df_pokemon, df_types)
    if not baseline_synergy:
        return {
            "success": False,
            "error": "Baseline synergy calculation failed."
        }
        
    baseline_score = baseline_synergy.get("overall", {}).get("score", 50)
    
    # 2. Identify Role Gaps & Weaknesses from Baseline
    gaps_detected = []
    baseline_gaps = baseline_synergy.get("gaps", [])
    for g in baseline_gaps:
        gaps_detected.append({
            "title": g.get("title", ""),
            "description": g.get("description", ""),
            "severity": g.get("severity", "medium"),
            "tag": g.get("tag", "defense")
        })
        
    type_matchups = baseline_synergy.get("type_matchups", {})
    severe_types = []
    for t_name, t_info in type_matchups.items():
        if t_info.get("weak_count", 0) >= 3 and (t_info.get("resist_count", 0) + t_info.get("immune_count", 0)) <= 1:
            severe_types.append(t_name.capitalize())
            
    if severe_types:
        gaps_detected.append({
            "title": f"Critical Shared Weakness ({', '.join(severe_types)})",
            "description": f"Three or more teammates are vulnerable to {', '.join(severe_types)} attacks with insufficient defensive resistances.",
            "severity": "high",
            "tag": "defense"
        })

    # 3. Candidate Pool
    canonical_to_name = {to_canonical_id(n): n for n in df_pokemon["name"]}
    meta = load_meta_telemetry(format_name)
    meta_pokemon = meta.get("pokemon", {})
    
    candidate_pool = []
    for c_id in sorted(meta_pokemon.keys(), key=lambda x: meta_pokemon[x].get("usage", 0.0), reverse=True):
        if c_id in canonical_to_name:
            cand_name = canonical_to_name[c_id]
            if cand_name not in normalized_team and cand_name not in candidate_pool:
                candidate_pool.append(cand_name)
        if len(candidate_pool) >= 35:
            break
            
    if len(candidate_pool) < 20:
        for _, row in df_pokemon.sort_values(by="base_stat_total", ascending=False).iterrows():
            if row["name"] not in normalized_team and row["name"] not in candidate_pool:
                candidate_pool.append(row["name"])
            if len(candidate_pool) >= 25:
                break

    # 4. Strategy-Aware Candidate Evaluation Loop
    proposals = []
    target_arch = str(target_archetype or "balance").lower()

    for i, current_mon in enumerate(normalized_team):
        current_display = current_mon.replace("-", " ").title()
        
        for cand in candidate_pool:
            test_team = list(normalized_team)
            test_team[i] = cand
            
            cand_spec = get_pokemon_species(cand)
            if not cand_spec:
                continue
                
            # A. Evaluate Archetype Strategy Harmony
            harmony_mod, harmony_reasons = evaluate_candidate_archetype_harmony(
                candidate_name=cand,
                species_info=cand_spec,
                target_archetype=target_arch
            )
            
            # If candidate actively breaks team strategy (e.g. Fire in Rain), skip or heavily penalize
            if harmony_mod <= -15.0:
                continue
                
            test_synergy = analyze_team_synergy(test_team, df_pokemon, df_types)
            if not test_synergy:
                continue
                
            raw_new_score = test_synergy.get("overall", {}).get("score", 50)
            # Adjusted score with strategy harmony
            adjusted_new_score = max(10, min(99, raw_new_score + int(harmony_mod * 0.4)))
            score_delta = adjusted_new_score - baseline_score
            
            if score_delta > 0:
                new_matchups = test_synergy.get("type_matchups", {})
                improved_types = []
                for t_name in severe_types:
                    t_key = t_name.lower()
                    old_weak = type_matchups.get(t_key, {}).get("weak_count", 0)
                    new_weak = new_matchups.get(t_key, {}).get("weak_count", 0)
                    new_res = new_matchups.get(t_key, {}).get("resist_count", 0) + new_matchups.get(t_key, {}).get("immune_count", 0)
                    if new_weak < old_weak or new_res > 1:
                        improved_types.append(t_name)
                        
                cand_display = cand.replace("-", " ").title()
                cand_data = get_pokemon_data([cand], df_pokemon)
                cand_info = cand_data[0] if cand_data else None
                
                # Formulate Comprehensive Rationale
                rationale_parts = [f"Replaces {current_display} with {cand_display} to boost team synergy score by +{score_delta} points"]
                if harmony_reasons:
                    rationale_parts.append(harmony_reasons[0])
                if improved_types:
                    rationale_parts.append(f"Patches critical team defensive weakness against {', '.join(improved_types)}")
                elif test_synergy.get("overall", {}).get("defensive_score", 0) > baseline_synergy.get("overall", {}).get("defensive_score", 0):
                    rationale_parts.append("Enhances overall elemental defensive resistances")
                if test_synergy.get("overall", {}).get("offensive_score", 0) > baseline_synergy.get("overall", {}).get("offensive_score", 0):
                    rationale_parts.append("Expands team super-effective offensive coverage")
                    
                rationale = ". ".join(rationale_parts) + "."
                
                proposals.append({
                    "remove_pokemon": current_display,
                    "remove_pokemon_raw": current_mon,
                    "add_pokemon": cand_display,
                    "add_pokemon_raw": cand,
                    "add_pokemon_data": cand_info,
                    "score_delta": score_delta,
                    "new_score": adjusted_new_score,
                    "improved_matchups": improved_types,
                    "rationale": rationale
                })

    proposals.sort(key=lambda x: (x["score_delta"], len(x["improved_matchups"])), reverse=True)
    
    filtered_suggestions = []
    seen_adds = set()
    
    for p in proposals:
        if len(filtered_suggestions) >= 3:
            break
        if p["add_pokemon"] not in seen_adds:
            filtered_suggestions.append(p)
            seen_adds.add(p["add_pokemon"])
            
    if len(filtered_suggestions) < 3:
        for p in proposals:
            if len(filtered_suggestions) >= 3:
                break
            if p not in filtered_suggestions:
                filtered_suggestions.append(p)

    return {
        "success": True,
        "format": format_name,
        "baseline_score": baseline_score,
        "baseline_synergy": baseline_synergy,
        "gaps_detected": gaps_detected,
        "suggestions": filtered_suggestions,
        "team_data": get_pokemon_data(normalized_team, df_pokemon)
    }
