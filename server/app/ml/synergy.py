import pandas as pd
from app.ml.strategies import STRATEGIES

ALL_TYPES = [
    "normal", "fire", "water", "grass", "electric", "ice",
    "fighting", "poison", "ground", "flying", "psychic", "bug",
    "rock", "ghost", "dragon", "steel", "dark", "fairy"
]

def build_type_chart(df_types: pd.DataFrame) -> dict:
    """
    Builds a defensive multiplier lookup from df_types.
    Returns {defending_type: {attacking_type: multiplier}}
    """
    chart = {}
    for _, row in df_types.iterrows():
        def_type = str(row["type"]).strip().lower()
        chart[def_type] = {atk: 1.0 for atk in ALL_TYPES}
        
        # Parse double damage from (2.0x)
        double_from = str(row.get("double_damage_from", ""))
        if pd.notna(row.get("double_damage_from")) and double_from:
            for atk in double_from.split("|"):
                atk = atk.strip().lower()
                if atk in chart[def_type]:
                    chart[def_type][atk] = 2.0
                    
        # Parse half damage from (0.5x)
        half_from = str(row.get("half_damage_from", ""))
        if pd.notna(row.get("half_damage_from")) and half_from:
            for atk in half_from.split("|"):
                atk = atk.strip().lower()
                if atk in chart[def_type]:
                    chart[def_type][atk] = 0.5
                    
        # Parse no damage from (0.0x)
        no_from = str(row.get("no_damage_from", ""))
        if pd.notna(row.get("no_damage_from")) and no_from:
            for atk in no_from.split("|"):
                atk = atk.strip().lower()
                if atk in chart[def_type]:
                    chart[def_type][atk] = 0.0
                    
    return chart

def get_pokemon_type_multiplier(type_1: str, type_2: str, attacking_type: str, type_chart: dict) -> float:
    """
    Calculates the combined damage multiplier against a single or dual-type Pokémon.
    """
    m1 = type_chart.get(type_1, {}).get(attacking_type, 1.0)
    if not type_2 or type_2 == "none" or type_2 == type_1:
        return m1
    m2 = type_chart.get(type_2, {}).get(attacking_type, 1.0)
    return m1 * m2

def analyze_team_synergy(team: list, df_pokemon: pd.DataFrame, df_types: pd.DataFrame) -> dict:
    """
    Performs comprehensive, transparent, explainable synergy analysis on a 6-Pokémon team.
    """
    normalized_team = [p.lower().replace(" ", "-") for p in team]
    selected = df_pokemon[df_pokemon["name"].isin(normalized_team)].copy()
    
    if len(selected) != 6:
        return None
        
    type_chart = build_type_chart(df_types)
    
    # -------------------------------------------------------------
    # 1. DEFENSIVE SYNERGY ANALYSIS
    # -------------------------------------------------------------
    type_matchups = {}
    severe_weaknesses = []
    moderate_weaknesses = []
    strong_resistances = []
    total_immunities = 0
    total_resistances = 0
    
    for atk_type in ALL_TYPES:
        weak_mons = []
        resist_mons = []
        immune_mons = []
        
        for _, mon in selected.iterrows():
            mult = get_pokemon_type_multiplier(mon["type_1"], mon["type_2"], atk_type, type_chart)
            name_display = mon["name"].capitalize().replace("-", " ")
            if mult >= 2.0:
                weak_mons.append({"name": name_display, "multiplier": mult})
            elif mult == 0.0:
                immune_mons.append({"name": name_display, "multiplier": mult})
            elif mult <= 0.5:
                resist_mons.append({"name": name_display, "multiplier": mult})
                
        weak_count = len(weak_mons)
        resist_count = len(resist_mons)
        immune_count = len(immune_mons)
        def_coverage = (resist_count + immune_count) - weak_count
        
        total_immunities += immune_count
        total_resistances += resist_count
        
        status = "balanced"
        if weak_count >= 3 and (resist_count + immune_count) < 2:
            status = "danger"
            severe_weaknesses.append({
                "type": atk_type,
                "weak_count": weak_count,
                "resist_count": resist_count + immune_count,
                "weak_pokemon": [m["name"] for m in weak_mons]
            })
        elif weak_count >= 2 and (resist_count + immune_count) == 0:
            status = "warning"
            moderate_weaknesses.append({
                "type": atk_type,
                "weak_count": weak_count,
                "resist_count": 0,
                "weak_pokemon": [m["name"] for m in weak_mons]
            })
        elif (resist_count + immune_count) >= 3 and weak_count <= 1:
            status = "strength"
            strong_resistances.append({
                "type": atk_type,
                "defense_count": resist_count + immune_count,
                "immune_count": immune_count
            })
            
        type_matchups[atk_type] = {
            "type": atk_type,
            "weak_count": weak_count,
            "resist_count": resist_count,
            "immune_count": immune_count,
            "net_rating": def_coverage,
            "status": status,
            "weak_pokemon": [m["name"] for m in weak_mons]
        }

    # Defensive Score Computation
    bulk_series = selected["hp"] + selected["defense"] + selected["sp_defense"]
    avg_bulk = float(bulk_series.mean())
    
    def_score = 72
    def_score -= len(severe_weaknesses) * 12
    def_score -= len(moderate_weaknesses) * 6
    def_score += min(len(strong_resistances) * 3, 12)
    def_score += min(total_immunities * 4, 12)
    
    if avg_bulk >= 310:
        def_score += 6
    elif avg_bulk <= 230:
        def_score -= 8
        
    def_score = max(20, min(96, def_score))
    
    # -------------------------------------------------------------
    # 2. OFFENSIVE SYNERGY ANALYSIS
    # -------------------------------------------------------------
    physical_attackers = int(sum(selected["attack"] > selected["sp_attack"] + 15))
    special_attackers = int(sum(selected["sp_attack"] > selected["attack"] + 15))
    mixed_attackers = 6 - (physical_attackers + special_attackers)
    
    fast_count = int(sum(selected["speed"] >= 100))
    mid_count = int(sum((selected["speed"] >= 65) & (selected["speed"] < 100)))
    slow_count = int(sum(selected["speed"] <= 60))
    
    # STAB Coverage
    team_types = set(selected["type_1"].tolist() + selected["type_2"].tolist())
    team_types.discard("none")
    
    covered_types = set()
    for t in team_types:
        row = df_types[df_types["type"] == t]
        if not row.empty:
            double_to = str(row.iloc[0].get("double_damage_to", ""))
            if pd.notna(double_to) and double_to:
                for target in double_to.split("|"):
                    covered_types.add(target.strip().lower())
                    
    coverage_count = len(covered_types)
    
    # Offensive Score Computation
    off_score = 65
    if 2 <= physical_attackers <= 4 and 2 <= special_attackers <= 4:
        off_score += 12  # Ideal split
    elif physical_attackers == 0 or special_attackers == 0:
        off_score -= 14  # Vulnerable to physical or special walls
        
    if fast_count >= 2:
        off_score += 10
    elif fast_count == 0 and slow_count >= 4:
        off_score += 4   # Trick room candidate
    elif fast_count == 0:
        off_score -= 10  # Outsped easily
        
    if coverage_count >= 13:
        off_score += 12
    elif coverage_count >= 9:
        off_score += 6
    elif coverage_count <= 5:
        off_score -= 10
        
    off_score = max(20, min(96, off_score))
    
    # -------------------------------------------------------------
    # 3. STRATEGIC & WEATHER SYNERGY ANALYSIS
    # -------------------------------------------------------------
    strat_score = 60
    strategic_insights = []
    
    # Weather Checks
    for weather in ["rain", "sun", "sand", "snow"]:
        setter_abs = set(STRATEGIES[weather]["weather_abilities"])
        abuser_abs = set(STRATEGIES[weather]["weather_abuser_abilities"])
        
        setters = [
            m["name"].capitalize().replace("-", " ")
            for _, m in selected.iterrows()
            if any(a in setter_abs for a in m["all_abilities"])
        ]
        abusers = [
            m["name"].capitalize().replace("-", " ")
            for _, m in selected.iterrows()
            if any(a in abuser_abs for a in m["all_abilities"])
        ]
        
        if setters and abusers:
            strat_score += 26
            strategic_insights.append({
                "type": "weather",
                "weather": weather,
                "title": f"Strong {weather.capitalize()} Synergy",
                "description": f"{', '.join(setters)} sets {weather.capitalize()}, which directly activates {', '.join(abusers)}.",
                "status": "success"
            })
        elif setters and not abusers:
            strategic_insights.append({
                "type": "weather",
                "weather": weather,
                "title": f"{weather.capitalize()} Setter Without Abusers",
                "description": f"{', '.join(setters)} summons {weather.capitalize()}, but no teammates have abilities that directly exploit it.",
                "status": "warning"
            })
            
    # Trick Room Checks
    tr_setters = set(STRATEGIES["trick_room"]["setters"])
    tr_abusers = set(STRATEGIES["trick_room"]["abusers"])
    
    team_set = set(normalized_team)
    found_tr_setters = [m.capitalize().replace("-", " ") for m in (team_set & tr_setters)]
    found_tr_abusers = [m.capitalize().replace("-", " ") for m in (team_set & tr_abusers)]
    
    if found_tr_setters and (found_tr_abusers or slow_count >= 3):
        strat_score += 24
        strategic_insights.append({
            "type": "trick_room",
            "title": "Trick Room Strategy Active",
            "description": f"{', '.join(found_tr_setters)} can reverse turn order for your slow heavy hitters ({', '.join(found_tr_abusers) if found_tr_abusers else f'{slow_count} slow Pokémon'}).",
            "status": "success"
        })
        
    # Stall / Bulky Balance Check
    very_bulky_count = int(sum(bulk_series >= 360))
    bulky_count = int(sum(bulk_series >= 300))
    if very_bulky_count >= 3 or bulky_count >= 4:
        strat_score += 15
        strategic_insights.append({
            "type": "role_cohesion",
            "title": "Defensive Stall Core",
            "description": f"Team possesses {bulky_count} high-bulk defensive pillars capable of absorbing repeated hits.",
            "status": "info"
        })
    elif fast_count >= 4:
        strat_score += 15
        strategic_insights.append({
            "type": "role_cohesion",
            "title": "Hyper Offensive Momentum",
            "description": f"Team features {fast_count} high-speed attackers designed to maintain relentless offensive pressure.",
            "status": "info"
        })
        
    strat_score = max(25, min(96, strat_score))
    
    # -------------------------------------------------------------
    # 4. COMPOSITE OVERALL SCORE & RATING
    # -------------------------------------------------------------
    overall_score = round(0.35 * def_score + 0.35 * off_score + 0.30 * strat_score)
    
    if overall_score >= 75:
        rating = "Strong"
        rating_color = "success"
        rating_summary = "Your team has clear strategic cohesion, good balance, and well-covered roles."
    elif overall_score >= 52:
        rating = "Moderate"
        rating_color = "warning"
        rating_summary = "Your team has a solid foundation, but there are overlapping weaknesses or offensive gaps to address."
    else:
        rating = "Needs Attention"
        rating_color = "danger"
        rating_summary = "Your team has notable structural vulnerabilities or lacks a unified strategic core."
        
    # -------------------------------------------------------------
    # 5. KEY STRENGTHS & CRITICAL GAPS COMPILATION
    # -------------------------------------------------------------
    strengths = []
    gaps = []
    
    # Strengths
    if total_immunities >= 2:
        strengths.append({
            "title": "Defensive Immunities",
            "description": f"Your team possesses {total_immunities} full type immunities, providing safe free switches during battle.",
            "tag": "Defense"
        })
    if 2 <= physical_attackers <= 4 and 2 <= special_attackers <= 4:
        strengths.append({
            "title": "Balanced Attack Vectors",
            "description": f"Balanced mix of {physical_attackers} Physical and {special_attackers} Special attackers prevents your team from being shut down by a single wall.",
            "tag": "Offense"
        })
    if coverage_count >= 11:
        strengths.append({
            "title": "Wide STAB Coverage",
            "description": f"Your team's natural STAB moves hit {coverage_count} out of 18 elemental types for super-effective damage.",
            "tag": "Coverage"
        })
    if fast_count >= 2:
        strengths.append({
            "title": "Fast Speed Tiers",
            "description": f"Contains {fast_count} Pokémon with base Speed 100+, allowing you to threaten quick knockouts.",
            "tag": "Speed"
        })
    for insight in strategic_insights:
        if insight["status"] == "success":
            strengths.append({
                "title": insight["title"],
                "description": insight["description"],
                "tag": "Strategy"
            })
            
    # Gaps
    for severe in severe_weaknesses:
        gaps.append({
            "title": f"Critical {severe['type'].capitalize()} Weakness",
            "description": f"{severe['weak_count']} Pokémon take 2x/4x damage from {severe['type'].capitalize()} attacks with only {severe['resist_count']} resistance on the team ({', '.join(severe['weak_pokemon'])}).",
            "severity": "danger",
            "tag": "Defensive Gap"
        })
    for moderate in moderate_weaknesses:
        gaps.append({
            "title": f"Unresisted {moderate['type'].capitalize()} Matchup",
            "description": f"{moderate['weak_count']} Pokémon are weak to {moderate['type'].capitalize()} with zero team resistances ({', '.join(moderate['weak_pokemon'])}).",
            "severity": "warning",
            "tag": "Defensive Gap"
        })
    if physical_attackers == 0:
        gaps.append({
            "title": "All-Special Offense",
            "description": "Your team has no dedicated physical attackers. Specially defensive walls (like Blissey or Clodsire) can stall your entire team.",
            "severity": "warning",
            "tag": "Offense Gap"
        })
    elif special_attackers == 0:
        gaps.append({
            "title": "All-Physical Offense",
            "description": "Your team has no dedicated special attackers. Physically defensive walls (like Dondozo or Corviknight) can stonewall your attacks.",
            "severity": "warning",
            "tag": "Offense Gap"
        })
    if fast_count == 0 and not found_tr_setters:
        gaps.append({
            "title": "Low Speed Control",
            "description": "No Pokémon with base Speed 100+ and no Trick Room setter. Faster opponent teams will consistently move first against you.",
            "severity": "warning",
            "tag": "Speed Gap"
        })
        
    if not strengths:
        strengths.append({
            "title": "Flexible Roster",
            "description": "Team maintains general versatility without heavy reliance on a single restrictive strategy.",
            "tag": "Flexibility"
        })
    if not gaps:
        gaps.append({
            "title": "No Critical Overlapping Weaknesses",
            "description": "Team weaknesses are well-distributed with adequate defensive resistances covering common offensive threats.",
            "severity": "success",
            "tag": "Well-Covered"
        })
        
    return {
        "success": True,
        "overall": {
            "score": overall_score,
            "rating": rating,
            "rating_color": rating_color,
            "summary": rating_summary,
            "defensive_score": def_score,
            "offensive_score": off_score,
            "strategic_score": strat_score
        },
        "strengths": strengths,
        "gaps": gaps,
        "offensive_profile": {
            "physical_attackers": physical_attackers,
            "special_attackers": special_attackers,
            "mixed_attackers": mixed_attackers,
            "fast_count": fast_count,
            "mid_count": mid_count,
            "slow_count": slow_count,
            "coverage_count": coverage_count,
            "covered_types": sorted(list(covered_types))
        },
        "type_matchups": type_matchups,
        "strategic_insights": strategic_insights,
        "beginner_guide": {
            "summary": "Team synergy measures how effectively your 6 Pokémon cover each other's weaknesses and coordinate toward a winning game plan.",
            "key_takeaways": [
                "Defensive coverage prevents single super-effective attacks from sweeping your team.",
                "A balanced mix of Physical and Special attackers keeps opponents from walling you.",
                "Speed tiers determine which side controls momentum and attacks first."
            ]
        }
    }
