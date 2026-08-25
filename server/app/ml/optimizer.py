import os
import json
import pandas as pd
from typing import Dict, List, Optional, Any
from app.ml.synergy import analyze_team_synergy
from app.ml.recommender import load_meta_telemetry
from app.ml.constraints import to_canonical_id, get_pokemon_species
from app.core.utils import get_pokemon_data

def optimize_team(
    team: List[str],
    df_pokemon: pd.DataFrame,
    df_types: pd.DataFrame,
    format_name: str = "gen9ou",
    target_archetype: Optional[str] = None
) -> Dict[str, Any]:
    """
    Team Optimizer Engine.
    Audits a 6-Pokémon team for strategic gaps and defensive vulnerabilities,
    then executes a fast combinatorial candidate search to propose optimal 1-for-1 replacements.
    """
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
        
    # Check severe defensive vulnerabilities
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
        
    # 3. Candidate Pool (Pre-indexed lookup for high performance)
    canonical_to_name = {to_canonical_id(n): n for n in df_pokemon["name"]}
    meta = load_meta_telemetry(format_name)
    meta_pokemon = meta.get("pokemon", {})
    
    candidate_pool = []
    for c_id in sorted(meta_pokemon.keys(), key=lambda x: meta_pokemon[x].get("usage", 0.0), reverse=True):
        if c_id in canonical_to_name:
            cand_name = canonical_to_name[c_id]
            if cand_name not in normalized_team and cand_name not in candidate_pool:
                candidate_pool.append(cand_name)
        if len(candidate_pool) >= 25:
            break
            
    if len(candidate_pool) < 15:
        for _, row in df_pokemon.sort_values(by="base_stat_total", ascending=False).iterrows():
            if row["name"] not in normalized_team and row["name"] not in candidate_pool:
                candidate_pool.append(row["name"])
            if len(candidate_pool) >= 20:
                break

    # 4. Fast Combinatorial Evaluation
    proposals = []
    
    for i, current_mon in enumerate(normalized_team):
        current_display = current_mon.replace("-", " ").title()
        
        for cand in candidate_pool:
            test_team = list(normalized_team)
            test_team[i] = cand
            
            test_synergy = analyze_team_synergy(test_team, df_pokemon, df_types)
            if not test_synergy:
                continue
                
            new_score = test_synergy.get("overall", {}).get("score", 50)
            score_delta = new_score - baseline_score
            
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
                
                rationale_parts = [f"Replaces {current_display} with {cand_display} to boost team synergy score by +{score_delta} points"]
                if improved_types:
                    rationale_parts.append(f"Patches critical team defensive weakness against {', '.join(improved_types)}")
                if test_synergy.get("overall", {}).get("defensive_score", 0) > baseline_synergy.get("overall", {}).get("defensive_score", 0):
                    rationale_parts.append("Enhances overall elemental defensive resistances")
                if test_synergy.get("overall", {}).get("offensive_score", 0) > baseline_synergy.get("overall", {}).get("offensive_score", 0):
                    rationale_parts.append("Expands team offensive super-effective coverage")
                    
                rationale = ". ".join(rationale_parts) + "."
                
                proposals.append({
                    "remove_pokemon": current_display,
                    "remove_pokemon_raw": current_mon,
                    "add_pokemon": cand_display,
                    "add_pokemon_raw": cand,
                    "add_pokemon_data": cand_info,
                    "score_delta": score_delta,
                    "new_score": new_score,
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
