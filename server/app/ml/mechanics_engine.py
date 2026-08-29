from typing import Dict, List, Optional, Any, Set, Tuple
import math

ALL_TYPES = {
    "normal", "fire", "water", "grass", "electric", "ice",
    "fighting", "poison", "ground", "flying", "psychic", "bug",
    "rock", "ghost", "dragon", "steel", "dark", "fairy", "stellar"
}

def is_status_move(category: str) -> bool:
    """Returns True if the move is a non-damaging Status move."""
    return str(category).strip().lower() == "status"

def get_effective_accuracy(move_id: str, base_accuracy: Any, weather: str = "", terrain: str = "", ability: str = "") -> int:
    """
    Calculates effective accuracy for a move under active weather, terrain, and abilities.
    Returns 100 for moves that bypass accuracy checks (e.g., Thunder/Hurricane in Rain, Blizzard in Snow).
    """
    w = str(weather).strip().lower()
    m_id = str(move_id).strip().lower()
    ab = str(ability).strip().lower()
    
    # Showdown represents perfect accuracy moves (e.g. Aerial Ace) as True
    if base_accuracy is True:
        return 100
        
    try:
        acc = int(base_accuracy)
    except (ValueError, TypeError):
        acc = 100

    # Weather-conditioned accuracy
    if w == "rain":
        if m_id in ["hurricane", "thunder", "bleakwindstorm", "wildboltstorm", "sandsearstorm"]:
            return 100  # Never misses in rain
    elif w == "sun":
        if m_id in ["hurricane", "thunder"]:
            return 50   # Drops to 50% in harsh sunlight
    elif w == "snow":
        if m_id == "blizzard":
            return 100  # Never misses in snow/hail

    # Ability accuracy modifications
    if ab == "compoundeyes":
        acc = min(100, int(acc * 1.3))
    elif ab == "notheft": # or no guard
        pass
    elif ab == "noguard":
        return 100

    return max(1, min(100, acc))

def get_effective_base_power(
    move_id: str,
    base_power: int,
    move_type: str,
    category: str,
    weather: str = "",
    terrain: str = "",
    ability: str = "",
    item: str = "",
    user_types: Optional[List[str]] = None,
    move_flags: Optional[Dict] = None,
    move_secondaries: bool = False,
    user_species: Optional[Dict[str, Any]] = None
) -> Tuple[float, List[str]]:
    """
    Calculates deterministic effective Base Power accounting for weather, terrain, conditional states, and items.
    Returns (effective_bp, list_of_mechanics_notes).
    """
    if is_status_move(category):
        return 0.0, []

    bp = float(base_power)
    m_id = str(move_id).strip().lower().replace("-", "").replace(" ", "")
    m_type = str(move_type).strip().lower()
    w = str(weather).strip().lower().replace("-", "").replace(" ", "")
    t = str(terrain).strip().lower().replace("-", "").replace(" ", "")
    ab = str(ability).strip().lower().replace("-", "").replace(" ", "")
    it = str(item).strip().lower().replace("-", "").replace(" ", "")
    notes = []

    # 1. Conditional Base Power & Typing Transformations
    if m_id == "weatherball":
        if w == "rain":
            bp = 100.0
            m_type = "water"
            notes.append("Transforms into 100 BP Water move in Rain")
        elif w == "sun":
            bp = 100.0
            m_type = "fire"
            notes.append("Transforms into 100 BP Fire move in Sun")
        elif w == "sand":
            bp = 100.0
            m_type = "rock"
            notes.append("Transforms into 100 BP Rock move in Sandstorm")
        elif w == "snow":
            bp = 100.0
            m_type = "ice"
            notes.append("Transforms into 100 BP Ice move in Snow")
        else:
            bp = 50.0

    elif m_id in ["solarbeam", "solarblade"]:
        if w == "sun":
            notes.append("Fires in 1 turn without charge in Sun")
        elif w in ["rain", "sand", "snow"]:
            bp *= 0.5
            notes.append("Power halved (50%) in non-Sun weather")
            
    elif m_id == "electroshot":
        if w == "rain":
            notes.append("Executes in 1 turn in Rain with +1 Sp. Atk boost")
        else:
            notes.append("Requires 2 turns to charge outside Rain")

    elif m_id == "hydrosteam":
        if w == "sun":
            bp *= 1.5
            notes.append("Boosted by 1.5x in Sun instead of being weakened")

    elif m_id == "facade":
        # Competitively, Facade is run on Guts/Flame Orb or as status retaliation
        if it in ["flameorb", "toxicorb"] or ab == "guts":
            bp = 140.0
            notes.append("Doubles to 140 BP with status orb/condition")

    elif m_id == "knockoff":
        # Standard competitive assumption: target holds an item on first hit
        bp *= 1.5  # 97.5 BP effective
        notes.append("Boosted to ~97.5 BP when removing target's held item")

    elif m_id in ["heavyslam", "heatcrash"]:
        # Weight-based moves vary heavily by opponent weight; normalized competitive average is ~70-80 BP against meta targets
        user_weight = float(user_species.get("weightkg", 100) if isinstance(user_species, dict) else 100)
        if user_weight >= 400:
            bp = 80.0
            notes.append("High ~80 BP based on user's extreme weight against average targets")
        elif user_weight >= 200:
            bp = 70.0
            notes.append("Standard ~70 BP based on user's heavy weight")
        else:
            bp = 60.0

    elif m_id == "expandingforce":
        if t == "psychic":
            bp *= 1.5
            notes.append("Boosted by 1.5x on grounded target in Psychic Terrain")

    elif m_id in ["iciclespear", "bulletseed", "rockblast", "tailslap", "armthrust"]:
        if ab == "skilllink" or it == "loadeddice":
            bp *= 4.5  # Consistent 4-5 hits
            notes.append("Hits 4-5 times with Loaded Dice / Skill Link")
        else:
            bp *= 3.0  # Average ~3 hits

    elif m_id in ["tripleaxel", "triplekick"]:
        # Cumulative multi-strike: Hit 1 (20) + Hit 2 (40) + Hit 3 (60) = 120 Total Base Power
        if it in ["widelens", "wide_lens"]:
            bp = 120.0
            notes.append("Full 3-strike connection (120 total BP) with Wide Lens accuracy")
        else:
            bp = 100.0  # Expected EV output factoring 90% accuracy per consecutive hit
            notes.append("Multi-strike attack (20+40+60 BP across 3 consecutive hits)")

    elif m_id in ["surgingstrikes", "wickedblow"]:
        bp *= 1.5  # Guaranteed critical hit multiplier
        notes.append("Guaranteed Critical Hit (1.5x damage multiplier)")

    elif m_id == "populationbomb":
        if it == "wide_lens" or it == "widelens":
            bp *= 9.5
            notes.append("Hits up to 10 times with Wide Lens accuracy boost")
        else:
            bp *= 7.0

    # 2. Weather Base Power Multipliers
    if w == "rain":
        if m_type == "water":
            bp *= 1.5
            notes.append("Boosted by 1.5x under Rain")
        elif m_type == "fire":
            bp *= 0.5
            notes.append("Weakened by 50% under Rain")
    elif w == "sun":
        if m_type == "fire":
            bp *= 1.5
            notes.append("Boosted by 1.5x under Harsh Sunlight")
        elif m_type == "water" and m_id != "hydrosteam":
            bp *= 0.5
            notes.append("Weakened by 50% under Harsh Sunlight")

    # 3. Terrain Base Power Multipliers
    if t == "electric" and m_type == "electric":
        bp *= 1.3
        notes.append("Boosted by 1.3x in Electric Terrain")
    elif t == "grassy":
        if m_type == "grass":
            bp *= 1.3
            notes.append("Boosted by 1.3x in Grassy Terrain")
        elif m_id in ["earthquake", "bulldoze", "magnitude"]:
            bp *= 0.5
            notes.append("Ground damage halved by Grassy Terrain")
    elif t == "psychic" and m_type == "psychic":
        bp *= 1.3
        notes.append("Boosted by 1.3x in Psychic Terrain")
    elif t == "misty" and m_type == "dragon":
        bp *= 0.5
        notes.append("Dragon damage halved by Misty Terrain")

    # 4. Ability Base Power Multipliers
    if ab == "toughclaws" and move_flags and move_flags.get("contact"):
        bp *= 1.3
        notes.append("Tough Claws boost (1.3x on contact moves)")
    elif ab == "technician" and bp <= 60:
        bp *= 1.5
        notes.append("Technician boost (1.5x on moves <= 60 BP)")
    elif ab == "sheerforce" and move_secondaries:
        bp *= 1.3
        notes.append("Sheer Force boost (1.3x on secondary effect moves)")
    elif ab == "sharpness" and move_flags and move_flags.get("slicing"):
        bp *= 1.5
        notes.append("Sharpness boost (1.5x on slicing moves)")
    elif ab == "strongjaw" and move_flags and move_flags.get("bite"):
        bp *= 1.5
        notes.append("Strong Jaw boost (1.5x on biting moves)")
    elif ab == "ironfist" and move_flags and move_flags.get("punch"):
        bp *= 1.2
        notes.append("Iron Fist boost (1.2x on punching moves)")
    elif ab == "punkrock" and move_flags and move_flags.get("sound"):
        bp *= 1.3
        notes.append("Punk Rock boost (1.3x on sound moves)")

    # 5. Item Multipliers
    if it in ["choiceband"] and category == "Physical":
        bp *= 1.5
        notes.append("Choice Band 1.5x Physical Attack boost")
    elif it in ["choicespecs"] and category == "Special":
        bp *= 1.5
        notes.append("Choice Specs 1.5x Special Attack boost")
    elif it in ["lifeorb"]:
        bp *= 1.3
        notes.append("Life Orb 1.3x damage boost")
    elif it in ["expertbelt"]:
        bp *= 1.2
        notes.append("Expert Belt 1.2x on super-effective hits")

    return bp, notes

def get_stab_multiplier(
    user_types: List[str],
    move_type: str,
    category: str,
    ability: str = "",
    tera_type: str = ""
) -> Tuple[float, Optional[str]]:
    """
    Calculates STAB multiplier.
    STRICT RULE: Non-damaging / Status moves NEVER receive STAB damage bonuses (returns 1.0, None).
    """
    if is_status_move(category):
        return 1.0, None

    m_type = str(move_type).strip().lower()
    norm_types = [t.strip().lower() for t in user_types]
    ab = str(ability).strip().lower()
    t_type = str(tera_type).strip().lower()

    # Tera STAB calculation
    if t_type and t_type != "none":
        if t_type == "stellar":
            return 1.2, "Stellar Tera Boost (1.2x)"
        elif t_type == m_type:
            if m_type in norm_types:
                return 2.0, f"Tera STAB Boost (2.0x for matching {m_type.capitalize()} type)"
            else:
                return 1.5, f"Tera STAB Boost (1.5x for Tera {m_type.capitalize()})"

    # Protean / Libero STAB calculation (Changes user's type to the move's type upon execution)
    if ab in ["protean", "libero"]:
        return 1.5, f"Protean / Libero STAB (1.5x {m_type.capitalize()})"

    # Normal STAB calculation
    if m_type in norm_types:
        if ab == "adaptability":
            return 2.0, "Adaptability STAB (2.0x)"
        return 1.5, f"STAB (1.5x {m_type.capitalize()})"

    return 1.0, None

def get_stat_alignment_score(category: str, base_atk: int, base_spa: int, base_def: int = 80, move_data: Optional[Dict] = None) -> float:
    """
    Evaluates whether a move's category matches the Pokémon's offensive stats using squared ratio.
    Status moves receive 1.0 (neutral).
    Attacking moves receive a steep penalty if they mismatch the primary attacking stat.
    """
    atk = max(1, int(base_atk))
    if move_data and move_data.get("overrideOffensiveStat") == "def":
        atk = max(1, int(base_def))
        
    spa = max(1, int(base_spa))
    max_stat = max(atk, spa)

    if is_status_move(category):
        # Status setup moves should align with the offensive stat they boost
        if move_data:
            boosts = move_data.get("boosts") or {}
            self_effects = move_data.get("self_effects") or {}
            self_boosts = self_effects.get("boosts", {}) if isinstance(self_effects, dict) else {}
            combined = {**boosts, **self_boosts}
            
            atk_boost = combined.get("atk", 0)
            spa_boost = combined.get("spa", 0)
            
            if atk_boost > 0 and spa_boost <= 0:
                ratio = atk / max_stat
                mag_scale = min(1.25, max(0.2, atk / 100.0))
                return (ratio * ratio) * mag_scale
            elif spa_boost > 0 and atk_boost <= 0:
                ratio = spa / max_stat
                mag_scale = min(1.25, max(0.2, spa / 100.0))
                return (ratio * ratio) * mag_scale
            elif atk_boost > 0 and spa_boost > 0:
                max_atk_spa = max(atk, spa)
                mag_scale = min(1.25, max(0.2, max_atk_spa / 100.0))
                return mag_scale
                
        return 1.0
        
    if move_data:
        if move_data.get("overrideOffensivePokemon") == "target" or move_data.get("damage") == "level":
            return 1.0
    
    if category == "Physical":
        ratio = atk / max_stat
        mag_scale = min(1.25, max(0.2, atk / 100.0))
        return (ratio * ratio) * mag_scale
    elif category == "Special":
        ratio = spa / max_stat
        mag_scale = min(1.25, max(0.2, spa / 100.0))
        return (ratio * ratio) * mag_scale
        
    return 1.0

def get_move_priority(move_id: str, base_priority: int, terrain: str = "", ability: str = "") -> int:
    """Calculates effective priority including terrain and ability modifiers."""
    pri = int(base_priority)
    m_id = str(move_id).strip().lower()
    t = str(terrain).strip().lower()
    ab = str(ability).strip().lower()

    if t == "grassy" and m_id == "grassyglide":
        pri += 1
    elif ab == "prankster" and m_id not in ["damaging"]: # Status moves
        pass # Handled by status category check in semantics

    return pri

def evaluate_move_mechanics(
    move_id: str,
    move_info: Dict[str, Any],
    user_species: Dict[str, Any],
    weather: str = "",
    terrain: str = "",
    ability: str = "",
    item: str = "",
    tera_type: str = ""
) -> Dict[str, Any]:
    """
    Comprehensive deterministic mechanics evaluator for a single candidate move.
    """
    m_id = str(move_id).strip().lower().replace("-", "").replace(" ", "")
    m_name = move_info.get("name", move_id)
    m_type = move_info.get("type", "normal").lower()
    m_cat = move_info.get("category", "Status")
    raw_bp = move_info.get("power", 0)
    raw_acc = move_info.get("accuracy", 100)
    raw_pri = move_info.get("priority", 0)
    
    user_types = [t.lower() for t in user_species.get("types", [])]
    base_stats = user_species.get("baseStats", {"atk": 80, "spa": 80, "spe": 80, "def": 80, "spd": 80, "hp": 80})
    base_atk = base_stats.get("atk", 80)
    base_spa = base_stats.get("spa", 80)
    base_def = base_stats.get("def", 80)

    # 1. Effective BP & Notes
    move_flags = move_info.get("flags", {})
    move_secondaries = bool(move_info.get("secondary") or move_info.get("secondaries"))
    
    is_fixed_damage = (move_info.get("damage") == "level")
    if is_fixed_damage:
        eff_bp = 100.0
        bp_notes = ["Fixed damage equal to user's level (100 at Lv100)"]
    else:
        eff_bp, bp_notes = get_effective_base_power(
            move_id=move_id,
            base_power=raw_bp,
            move_type=m_type,
            category=m_cat,
            weather=weather,
            terrain=terrain,
            ability=ability,
            item=item,
            user_types=user_types,
            move_flags=move_flags,
            move_secondaries=move_secondaries,
            user_species=user_species
        )

    # 2. Effective Accuracy
    eff_acc = get_effective_accuracy(
        move_id=move_id,
        base_accuracy=raw_acc,
        weather=weather,
        terrain=terrain,
        ability=ability
    )

    # 3. STAB Multiplier (Zero for Status moves)
    if is_fixed_damage:
        stab_mult = 1.0
        stab_note = None
    else:
        stab_mult, stab_note = get_stab_multiplier(
            user_types=user_types,
            move_type=m_type,
            category=m_cat,
            ability=ability,
            tera_type=tera_type
        )

    # 4. Stat Alignment Score
    stat_score = get_stat_alignment_score(
        category=m_cat,
        base_atk=base_atk,
        base_spa=base_spa,
        base_def=base_def,
        move_data=move_info
    )

    # 5. Effective Priority
    eff_pri = get_move_priority(
        move_id=move_id,
        base_priority=raw_pri,
        terrain=terrain,
        ability=ability
    )

    # 6. Deterministic Mechanical Score Calculation
    if is_status_move(m_cat):
        # Status moves score purely on utility and field setup
        base_mech_score = 3.0
    else:
        # Relative power proxy = Effective BP * (Accuracy/100) * STAB * Stat Alignment
        expected_output = eff_bp * (eff_acc / 100.0) * stab_mult
        base_mech_score = (expected_output / 100.0) * 4.0 * stat_score
        
        # Penalize unviable competitive drawbacks (Recharge turn, Focus disruption, Self-KO)
        if move_id in ["hyperbeam", "gigaimpact", "frenzyplant", "blastburn", "hydrocannon", "meteorassault", "roaroftime", "prismaticlaser"]:
            base_mech_score *= 0.35  # Severe penalty for losing an entire turn
        elif move_id in ["explosion", "selfdestruct", "mistyexplosion", "chloroblast", "mindblown", "steelbeam"]:
            base_mech_score *= 0.40  # Severe penalty for self-KO / sacrificing own HP/life
        elif move_id in ["focuspunch"] and ability != "substitute":
            base_mech_score *= 0.5   # Focus Punch fails if hit before moving
        elif move_id in ["solarbeam", "solarblade"] and str(weather).lower() != "sun":
            base_mech_score *= 0.4   # 2-turn charge outside Sun
        elif move_id in ["electroshot"] and str(weather).lower() != "rain":
            base_mech_score *= 0.4   # 2-turn charge outside Rain
            
        # Bonus for high-value competitive attributes & Signature / Iconic STAB attacks
        if eff_pri > 0:
            base_spe = base_stats.get("spe", 80)
            # Slower Pokémon benefit significantly more from priority moves (e.g. Speed <= 75 gives maximum priority urgency)
            speed_urgency = max(1.0, (110.0 - base_spe) / 10.0) if base_spe < 100 else 1.0
            pri_bonus = (eff_pri * 2.5) * speed_urgency
            if stab_mult > 1.0:
                pri_bonus += 3.5  # Additional bonus for STAB priority attacks (e.g. Bullet Punch, Mach Punch, Aqua Jet, Ice Shard)
            base_mech_score += pri_bonus
        if m_id in ["drainpunch", "gigadrain", "hornleech", "bitterblade", "oblivionwing"]:
            base_mech_score += 1.2   # Healing / sustain utility
        elif m_id in ["uturn", "voltswitch", "flipturn", "partingshot"]:
            base_mech_score += 1.5   # Pivoting momentum
        elif m_id in ["knockoff"]:
            base_mech_score += 0.8   # Utility item removal (balanced vs STAB attacks)
        elif m_id in ["rapidspin", "mortalspin"]:
            base_mech_score += 1.5   # Hazard removal + Speed boost
        elif m_id in ["icespinner"]:
            base_mech_score += 1.0   # Terrain removal + coverage
        elif m_id in ["psychicfangs", "brickbreak"]:
            base_mech_score += 1.8   # Screen-breaking utility (destroys Reflect, Light Screen, Aurora Veil)
        elif m_id in ["hammerarm", "closecombat", "superpower", "sacredsword", "aurasphere", "focusblast", "lowkick", "drainpunch"]:
            base_mech_score += 4.5   # High-value Fighting coverage breaking opposing Steel, Dark, Normal, and Ice types
        elif m_id in ["earthquake", "earthpower", "headlongrush"]:
            base_mech_score += 1.2   # Essential Ground coverage against Steel, Fire, Poison, Electric types

        # Signature & Iconic STAB Move Boost (e.g. Meteor Mash, Sacred Sword, Dragon Ascent, Pyro Ball)
        SIGNATURE_ICONIC_MOVES = {
            "meteormash", "sacredsword", "bitterblade", "ceaselessedge", "stoneaxe",
            "kowtowcleave", "torchsong", "flowertrick", "aqua-step", "aquastep",
            "dragonascent", "precipiceblades", "originpulse", "geomancy", "spectrier",
            "astralbarrage", "glaciallance", "surgingstrikes", "wickedblow", "collisioncourse",
            "electrodrift", "makeitrain", "gigatonhammer", "vcreate", "fusionflare", "fusionbolt",
            "psyblade", "bloodmoon", "syrupbomb", "matchagotcha", "ivycudgel", "tachyoncutter"
        }
        if m_id in SIGNATURE_ICONIC_MOVES and stab_mult > 1.0:
            base_mech_score += 6.5   # Massive priority boost for signature / iconic STAB attacks

        # Recoil penalties (unless Rock Head or Magic Guard)
        if ability not in ["rockhead", "magicguard"]:
            if m_id in ["headsmash", "doubleedge", "takedown", "submission", "wildcharge"]:
                base_mech_score *= 0.7  # Severe recoil penalty
            elif m_id in ["bravebird", "flareblitz", "woodhammer", "wavecrash"] and stab_mult == 1.0:
                base_mech_score *= 0.8  # Recoil penalty on non-STAB

    return {
        "move_id": move_id,
        "name": m_name,
        "type": m_type,
        "category": m_cat,
        "effective_bp": round(eff_bp, 1),
        "effective_accuracy": eff_acc,
        "priority": eff_pri,
        "stab_mult": stab_mult,
        "stab_note": stab_note,
        "stat_score": round(stat_score, 3),
        "mechanical_score": round(base_mech_score, 2),
        "notes": bp_notes
    }
