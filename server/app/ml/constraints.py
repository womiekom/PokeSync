import os
import json
import re
from typing import Dict, List, Optional, Set, Any
from app.ml.mechanics_engine import (
    is_status_move,
    get_effective_accuracy,
    get_effective_base_power,
    get_stab_multiplier,
    get_stat_alignment_score,
    get_move_priority,
    evaluate_move_mechanics
)

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
    
    # Format banlists for moves (Standard Clauses: Evasion Clause, OHKO Clause, Sleep Moves where applicable)
    banned_moves = {
        "shedtail", "lastrespects", "batonpass",
        "doubleteam", "minimize",
        "fissure", "guillotine", "horndrill", "sheercold"
    } if "ou" in format_name.lower() else set()
    
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
            "flags": move_info.get("flags", {}),
            "secondary": move_info.get("secondary"),
            "secondaries": move_info.get("secondaries"),
            "overrideOffensiveStat": move_info.get("overrideOffensiveStat"),
            "overrideOffensivePokemon": move_info.get("overrideOffensivePokemon"),
            "damage": move_info.get("damage"),
            "boosts": move_info.get("boosts"),
            "self_effects": move_info.get("self"),
            "status": move_info.get("status"),
            "side_condition": move_info.get("sideCondition"),
            "volatile_status": move_info.get("volatileStatus"),
            "slot_condition": move_info.get("slotCondition"),
            "weather": move_info.get("weather"),
            "terrain": move_info.get("terrain"),
            "pseudo_weather": move_info.get("pseudoWeather"),
            "drain": move_info.get("drain"),
            "force_switch": move_info.get("forceSwitch"),
            "self_switch": move_info.get("selfSwitch")
        }
        
    return legal_moves
