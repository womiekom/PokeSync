import os
import json
from typing import Dict, List, Optional, Any, Tuple, Set
from app.ml.constraints import (
    to_canonical_id,
    get_pokemon_species,
    get_legal_moves,
    get_stab_multiplier,
    get_stat_alignment_score,
    get_weather_terrain_multiplier
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

# Archetype-specific synergistic moves
ARCHETYPE_MOVE_SYNERGY = {
    "rain": {
        "boosted_types": ["water"],
        "key_moves": ["hydropump", "surf", "waterfall", "liquidation", "flipturn", "hurricane", "thunder", "aquajet", "wavecrash"],
        "utility_moves": ["raindance", "tailwind", "protect"]
    },
    "sun": {
        "boosted_types": ["fire"],
        "key_moves": ["fireblast", "flamethrower", "overheat", "flareblitz", "bitterblade", "solarbeam", "solarblade", "weatherball", "growth", "morning_sun"],
        "utility_moves": ["sunnyday", "willowisp"]
    },
    "sand": {
        "boosted_types": ["rock", "ground", "steel"],
        "key_moves": ["earthquake", "headlongrush", "stoneedge", "rockslide", "ironhead", "shoreup"],
        "utility_moves": ["sandstorm", "stealthrock", "spikes"]
    },
    "snow": {
        "boosted_types": ["ice"],
        "key_moves": ["blizzard", "icebeam", "icespinner", "iciclespear", "freezedry", "auroraveil", "chillyreception"],
        "utility_moves": ["snowscape"]
    },
    "trick_room": {
        "boosted_types": [],
        "key_moves": ["trickroom", "gyroball", "headlongrush", "hammerarm", "hypervoice", "bloodmoon"],
        "utility_moves": ["helpinghand", "protect", "curse"]
    },
    "hyper_offense": {
        "boosted_types": [],
        "key_moves": ["swordsdance", "nastyplot", "dragondance", "quiverdance", "closecombat", "dracometeor", "shadowball", "headlongrush", "makeitrain", "suckerpunch", "extremespeed"],
        "utility_moves": ["stealthrock", "spikes", "taunt"]
    },
    "stall": {
        "boosted_types": [],
        "key_moves": ["recover", "roost", "softboiled", "slackoff", "wish", "protect", "toxic", "thunderwave", "willowisp", "seismictoss", "foulplay"],
        "utility_moves": ["haze", "whirlwind", "roar", "rapidspin", "defog"]
    },
    "balance": {
        "boosted_types": [],
        "key_moves": ["uturn", "voltswitch", "flipturn", "knockoff", "rapidspin", "recover", "earthquake", "scald", "stealthrock"],
        "utility_moves": ["thunderwave", "willowisp"]
    }
}

def analyze_team_coverage_gaps(teammates: List[str]) -> Tuple[Set[str], Set[str]]:
    """Analyzes the teammate roster to identify missing offensive types and shared defensive weaknesses."""
    covered_types = set()
    for tm in teammates:
        spec = get_pokemon_species(tm)
        if spec:
            for t in spec.get("types", []):
                covered_types.add(t.lower())
    
    all_types = {"normal", "fire", "water", "grass", "electric", "ice", "fighting", "poison", "ground", "flying", "psychic", "bug", "rock", "ghost", "dragon", "steel", "dark", "fairy"}
    missing_coverage = all_types - covered_types
    return covered_types, missing_coverage

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
    Context-Aware Moveset Recommendation Engine.
    Evaluates all legal moves through a hybrid deterministic + empirical telemetry ranking pipeline.
    """
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
    
    # 1. Retrieve Legal Movepool (Hard Legality Mask)
    legal_moves = get_legal_moves(pokemon_name, format_name)
    if not legal_moves:
        return {
            "success": False,
            "error": f"No legal moves found for '{pokemon_name}' in {format_name}."
        }
        
    # 2. Load Empirical High-Ladder Telemetry
    meta = load_meta_telemetry(format_name)
    mon_meta = meta.get("pokemon", {}).get(c_id, {})
    meta_moves = mon_meta.get("moves", {})
    total_meta_count = sum(meta_moves.values()) if meta_moves else 1.0
    
    # 3. Analyze Team Context & Archetype
    covered_types, missing_coverage = analyze_team_coverage_gaps(teammates)
    arch_key = archetype.lower().replace(" ", "_")
    arch_info = ARCHETYPE_MOVE_SYNERGY.get(arch_key, ARCHETYPE_MOVE_SYNERGY["balance"])
    
    # 4. Score Candidate Moves
    scored_moves = []
    
    for m_id, m_info in legal_moves.items():
        m_name = m_info["name"]
        m_type = m_info["type"]
        m_cat = m_info["category"]
        m_bp = m_info["power"]
        
        # A. Empirical High-Ladder Frequency Score (0.0 to 1.0)
        raw_emp = meta_moves.get(m_id, 0.0)
        emp_score = min(raw_emp / total_meta_count * 4.0, 1.0) if total_meta_count > 0 else 0.0
        
        # B. STAB Alignment (1.0 to 2.0)
        stab_mult = get_stab_multiplier(types, m_type, ability)
        stab_score = (stab_mult - 1.0) * 2.0  # 0.0, 1.0, or 2.0
        
        # C. Stat Alignment (0.0 to 1.0)
        stat_score = get_stat_alignment_score(m_cat, base_atk, base_spa)
        
        # D. Archetype Synergy
        arch_score = 0.0
        if m_id in arch_info.get("key_moves", []):
            arch_score += 1.2
        elif m_id in arch_info.get("utility_moves", []):
            arch_score += 0.8
        if m_type in arch_info.get("boosted_types", []):
            arch_score += 0.5
            
        # E. Team Coverage Gap Fulfillment
        coverage_score = 0.0
        if m_cat in ["Physical", "Special"] and m_type in missing_coverage and m_type not in types:
            coverage_score = 0.6  # High value for filling teammate coverage gaps
            
        # F. Weather / Terrain Mechanics Boost
        weather_boost = get_weather_terrain_multiplier(m_type, m_id, arch_key)
        
        # G. Power / Accuracy Utility Base
        base_power_score = (min(m_bp, 130) / 130.0) if m_bp > 0 else 0.4
        
        # Combined Weighted Score Formula
        # Moves with high real-world empirical usage get a strong baseline,
        # but archetype synergy and coverage gap fulfillment dynamically promote contextual moves.
        total_score = (
            (emp_score * 3.5) +
            (arch_score * 2.5) +
            (coverage_score * 1.5) +
            (stab_score * 1.5) +
            (stat_score * 1.2) +
            (base_power_score * 1.0)
        ) * weather_boost
        
        # Determine strategic role tag
        if m_cat == "Status":
            if m_id in ["swordsdance", "nastyplot", "dragondance", "quiverdance", "calmmind", "bulkup", "growth", "curse", "bellydrum"]:
                role_tag = "Setup / Stat Boost"
            elif m_id in ["recover", "roost", "slackoff", "softboiled", "wish", "synthesis", "morningsun", "shoreup"]:
                role_tag = "Recovery / Sustain"
            elif m_id in ["stealthrock", "spikes", "toxicspikes", "stickyweb", "ceaselessedge"]:
                role_tag = "Entry Hazard"
            elif m_id in ["rapidspin", "defog", "mortalspin", "courtchange", "tidyup"]:
                role_tag = "Hazard Removal"
            elif m_id in ["thunderwave", "willowisp", "toxic", "hypnosis", "spore", "glare"]:
                role_tag = "Status Control"
            elif m_id in ["trickroom", "tailwind", "auroraveil"]:
                role_tag = "Field / Speed Control"
            else:
                role_tag = "Utility"
        else:
            if stab_mult > 1.0:
                role_tag = "Primary STAB"
            elif coverage_score > 0:
                role_tag = "Team Coverage"
            elif m_info.get("priority", 0) > 0:
                role_tag = "Priority Finisher"
            elif m_id in ["uturn", "voltswitch", "flipturn", "partingshot"]:
                role_tag = "Pivoting Momentum"
            else:
                role_tag = "Coverage"
                
        # Generate beginner-friendly rationale
        rationale_parts = []
        if stab_mult > 1.0:
            rationale_parts.append(f"Receives {int(stab_mult*100)}% STAB damage boost matching {m_type.capitalize()} typing")
        if arch_score > 0:
            rationale_parts.append(f"Synergizes strongly with {archetype.capitalize()} team gameplan")
        if coverage_score > 0:
            rationale_parts.append(f"Provides critical {m_type.capitalize()} coverage missing from teammates")
        if emp_score > 0.4:
            rationale_parts.append("Dominant competitive standard on high-ladder teams")
        if m_info.get("priority", 0) > 0:
            rationale_parts.append("Provides clutch priority speed control to finish weakened foes")
            
        rationale = ". ".join(rationale_parts) if rationale_parts else f"Strong {m_cat.lower()} option with reliable {m_bp} base power."
        
        scored_moves.append({
            "id": m_id,
            "name": m_name,
            "type": m_type,
            "category": m_cat,
            "power": m_bp,
            "accuracy": m_info["accuracy"],
            "priority": m_info["priority"],
            "score": round(total_score, 2),
            "role_tag": role_tag,
            "rationale": rationale
        })
        
    # Sort by descending score
    scored_moves.sort(key=lambda x: x["score"], reverse=True)
    
    # 5. Build Balanced Top-4 Moveset (Avoids 4 identical status moves or 4 identical type attacks)
    selected_moves = []
    seen_types = set()
    has_attack = False
    
    # First pass: take highest scoring moves
    for m in scored_moves:
        if len(selected_moves) >= top_n:
            break
        # Allow at most 2 moves of the exact same type unless status
        type_count = sum(1 for sm in selected_moves if sm["type"] == m["type"] and sm["category"] != "Status")
        if type_count >= 2 and m["category"] != "Status":
            continue
        selected_moves.append(m)
        if m["category"] in ["Physical", "Special"]:
            has_attack = True
            
    # If no attack was selected, force best STAB attack
    if not has_attack:
        for m in scored_moves:
            if m["category"] in ["Physical", "Special"] and m not in selected_moves:
                selected_moves[-1] = m
                break
                
    # 6. Recommended Tera Types & Held Items from Telemetry
    raw_tera = mon_meta.get("tera_types", {})
    recommended_tera = [t.capitalize() for t, _ in sorted(raw_tera.items(), key=lambda x: x[1], reverse=True)[:3]]
    if not recommended_tera:
        recommended_tera = [t.capitalize() for t in types]
        
    raw_items = mon_meta.get("items", {})
    recommended_items = [it.replace("-", " ").title() for it, _ in sorted(raw_items.items(), key=lambda x: x[1], reverse=True)[:3]]
    if not recommended_items:
        recommended_items = ["Leftovers", "Life Orb", "Choice Scarf"]
        
    return {
        "success": True,
        "pokemon": species_info.get("name", pokemon_name),
        "types": [t.capitalize() for t in types],
        "format": format_name,
        "archetype": archetype,
        "recommended_moves": selected_moves,
        "recommended_tera_types": recommended_tera,
        "recommended_items": recommended_items,
        "archetype_fit_summary": f"Moveset customized for {species_info.get('name', pokemon_name)} within a {archetype.capitalize()} team context."
    }
