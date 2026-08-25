import os
import json
import re
from typing import Dict, List, Optional, Set, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DATA_DIR = os.path.join(BASE_DIR, "data", "game_data")

_POKEDEX: Optional[Dict[str, Any]] = None
_MOVES: Optional[Dict[str, Any]] = None
_LEARNSETS: Optional[Dict[str, Any]] = None
_FORMATS: Optional[Dict[str, Any]] = None
_ITEMS: Optional[Dict[str, Any]] = None
_ABILITIES: Optional[Dict[str, Any]] = None

def to_canonical_id(name: str) -> str:
    """Normalizes a Pokémon, move, ability, or item name to canonical lowercase alphanumeric ID."""
    if not name:
        return ""
    return re.sub(r'[^a-z0-9]', '', str(name).lower().strip())

def load_game_data():
    global _POKEDEX, _MOVES, _LEARNSETS, _FORMATS, _ITEMS, _ABILITIES
    if _POKEDEX is None:
        with open(os.path.join(GAME_DATA_DIR, "pokedex.json"), "r", encoding="utf-8") as f:
            _POKEDEX = json.load(f)
    if _MOVES is None:
        with open(os.path.join(GAME_DATA_DIR, "moves.json"), "r", encoding="utf-8") as f:
            _MOVES = json.load(f)
    if _LEARNSETS is None:
        with open(os.path.join(GAME_DATA_DIR, "learnsets.json"), "r", encoding="utf-8") as f:
            _LEARNSETS = json.load(f)
    if _FORMATS is None:
        with open(os.path.join(GAME_DATA_DIR, "formats.json"), "r", encoding="utf-8") as f:
            _FORMATS = json.load(f)
    if _ITEMS is None:
        with open(os.path.join(GAME_DATA_DIR, "items.json"), "r", encoding="utf-8") as f:
            _ITEMS = json.load(f)
    if _ABILITIES is None:
        with open(os.path.join(GAME_DATA_DIR, "abilities.json"), "r", encoding="utf-8") as f:
            _ABILITIES = json.load(f)

def get_pokemon_species(pokemon_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves species information from Pokédex by name or canonical ID."""
    load_game_data()
    c_id = to_canonical_id(pokemon_name)
    if c_id in _POKEDEX:
        return _POKEDEX[c_id]
    # Check by name
    for k, v in _POKEDEX.items():
        if to_canonical_id(v.get("name", "")) == c_id:
            return v
    return None

def get_move_details(move_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves move metadata by name or canonical ID."""
    load_game_data()
    c_id = to_canonical_id(move_name)
    return _MOVES.get(c_id)

def get_legal_moves(pokemon_name: str, format_name: str = "gen9ou") -> Dict[str, Dict[str, Any]]:
    """
    Returns all legal moves for a given Pokémon in the specified Gen 9 format.
    Ensures that only moves learnable in Gen 9 (or valid transfers) and unbanned in the format are returned.
    """
    load_game_data()
    c_id = to_canonical_id(pokemon_name)
    
    # 1. Look up species in learnsets
    learnset_entry = _LEARNSETS.get(c_id, {})
    if not learnset_entry:
        # Check base species if this is a form/forme
        species = get_pokemon_species(pokemon_name)
        if species and "baseSpecies" in species:
            base_id = to_canonical_id(species["baseSpecies"])
            learnset_entry = _LEARNSETS.get(base_id, {})
    
    learnset_dict = learnset_entry.get("learnset", {})
    if not learnset_dict and c_id in _LEARNSETS:
        learnset_dict = _LEARNSETS[c_id]
    
    # Format banlists for moves
    banned_moves = {"shedtail", "lastrespects", "batonpass"} if "ou" in format_name.lower() else set()
    
    legal_moves = {}
    for move_id, sources in learnset_dict.items():
        if move_id in banned_moves:
            continue
        
        # In Gen 9 formats (OU, VGC, etc.), move must have a native Gen 9 acquisition method ("9M", "9L", "9E", "9T", "9D", etc.)
        # unless playing National Dex format.
        if "nationaldex" not in format_name.lower() and "gen9" in format_name.lower():
            has_gen9 = any(str(src).startswith("9") for src in sources) if isinstance(sources, list) else False
            if not has_gen9:
                continue
        
        move_info = _MOVES.get(move_id)
        if not move_info:
            continue
        
        # Move must not be non-standard / past-gen deleted move
        if move_info.get("isNonstandard") in ["Past", "LGPE", "Unobtainable", "Gigantamax"]:
            continue
            
        legal_moves[move_id] = {
            "id": move_id,
            "name": move_info.get("name", move_id),
            "type": move_info.get("type", "Normal").lower(),
            "category": move_info.get("category", "Status"),
            "power": move_info.get("basePower", 0),
            "accuracy": 100 if move_info.get("accuracy") is True else (move_info.get("accuracy") or 100),
            "pp": move_info.get("pp", 10),
            "priority": move_info.get("priority", 0),
            "target": move_info.get("target", "normal"),
            "flags": move_info.get("flags", {})
        }
        
    return legal_moves

def get_stab_multiplier(pokemon_types: List[str], move_type: str, ability: str = "") -> float:
    """Calculates STAB (Same-Type Attack Bonus)."""
    norm_types = [t.lower() for t in pokemon_types]
    if move_type.lower() in norm_types:
        return 2.0 if to_canonical_id(ability) == "adaptability" else 1.5
    return 1.0

def get_stat_alignment_score(category: str, base_atk: int, base_spa: int) -> float:
    """Evaluates whether the move's damage category matches the Pokémon's offensive stats."""
    if category == "Status":
        return 1.0
    max_stat = max(base_atk, base_spa, 1)
    if category == "Physical":
        return base_atk / max_stat
    elif category == "Special":
        return base_spa / max_stat
    return 1.0

def get_weather_terrain_multiplier(move_type: str, move_id: str, weather: str = "", terrain: str = "") -> float:
    """Calculates weather and terrain damage and utility multipliers."""
    mult = 1.0
    w = weather.lower()
    t = terrain.lower()
    m_type = move_type.lower()
    
    # Weather
    if w == "rain":
        if m_type == "water":
            mult *= 1.5
        elif m_type == "fire":
            mult *= 0.5
        elif move_id in ["hurricane", "thunder"]:
            mult *= 1.3  # Perfect accuracy bonus
    elif w == "sun":
        if m_type == "fire":
            mult *= 1.5
        elif m_type == "water":
            mult *= 0.5
        elif move_id in ["solarbeam", "solarblade", "growth"]:
            mult *= 1.4
        elif move_id == "weatherball":
            mult *= 2.0  # Turns into 100 BP Fire move boosted by Sun
    elif w == "snow":
        if move_id == "blizzard":
            mult *= 1.3
    
    # Terrain
    if t == "electric" and m_type == "electric":
        mult *= 1.3
    elif t == "grassy":
        if m_type == "grass":
            mult *= 1.3
        elif move_id == "grassyglide":
            mult *= 1.4  # Priority in terrain
    elif t == "psychic":
        if m_type == "psychic":
            mult *= 1.3
        elif move_id == "expandingforce":
            mult *= 1.5
            
    return mult
