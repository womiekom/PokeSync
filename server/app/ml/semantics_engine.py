from typing import Dict, List, Optional, Any, Set, Tuple

WEATHER_SETTER_ABILITIES = {
    "rain": {"drizzle"},
    "sun": {"drought", "orichalcumpulse"},
    "sand": {"sandstream", "sandspit"},
    "snow": {"snowwarning"}
}

WEATHER_ABUSER_ABILITIES = {
    "rain": {"swiftswim", "dryskin", "hydration", "raindish"},
    "sun": {"chlorophyll", "solarpower", "protosynthesis", "leafguard", "harvest"},
    "sand": {"sandrush", "sandforce", "sandveil"},
    "snow": {"slushrush", "icebody", "snowcloak"}
}

TERRAIN_SETTER_ABILITIES = {
    "electric": {"electricsurge", "hadronengine"},
    "grassy": {"grassysurge"},
    "psychic": {"psychicsurge"},
    "misty": {"mistysurge"}
}

TERRAIN_ABUSER_ABILITIES = {
    "electric": {"surgesurfer", "quarkdrive"},
    "grassy": {},
    "psychic": {},
    "misty": {}
}

ABILITY_IMMUNITIES = {
    "water": {"waterabsorb", "stormdrain", "dryskin"},
    "electric": {"voltabsorb", "lightningrod", "motordrive"},
    "fire": {"flashfire", "wellbakedbody"},
    "ground": {"levitate", "eartheater"},
    "grass": {"sapsipper"}
}

def classify_archetype_role(
    species_name: str,
    species_data: Dict[str, Any],
    archetype: str,
    ability: str = ""
) -> Dict[str, Any]:
    """
    Classifies a Pokémon's role within an archetype (e.g. Weather Setter, Weather Sweeper, Pivot, Wall).
    """
    arch = str(archetype).strip().lower().replace(" ", "_")
    ab = str(ability).strip().lower()
    all_abilities = [str(a).lower() for a in species_data.get("abilities", {}).values()] if isinstance(species_data.get("abilities"), dict) else [ab]
    
    base_stats = species_data.get("baseStats", {"hp": 80, "atk": 80, "def": 80, "spa": 80, "spd": 80, "spe": 80})
    base_atk = base_stats.get("atk", 80)
    base_spa = base_stats.get("spa", 80)
    base_spe = base_stats.get("spe", 80)
    base_hp = base_stats.get("hp", 80)
    base_def = base_stats.get("def", 80)
    base_spd = base_stats.get("spd", 80)
    
    # 1. Weather Setters & Abusers
    if arch in ["rain", "sun", "sand", "snow"]:
        setter_set = WEATHER_SETTER_ABILITIES.get(arch, set())
        abuser_set = WEATHER_ABUSER_ABILITIES.get(arch, set())
        
        is_setter = ab in setter_set or any(a in setter_set for a in all_abilities)
        is_abuser = ab in abuser_set or any(a in abuser_set for a in all_abilities)
        
        if is_setter:
            return {
                "role": "Weather Setter",
                "is_setter": True,
                "is_abuser": False,
                "prioritize_weather_moves": False, # Automatic ability setting -> no need for manual Rain Dance/Sunny Day!
                "prioritize_pivot": True,
                "preferred_item": f"{arch}_rock"
            }
        elif is_abuser:
            return {
                "role": "Weather Sweeper",
                "is_setter": False,
                "is_abuser": True,
                "prioritize_weather_moves": False, # Swift swimmers should NOT run Rain Dance
                "prioritize_pivot": False,
                "preferred_item": "lifeorb"
            }

    # 2. Trick Room Roles
    if arch == "trick_room":
        if base_spe <= 55 and max(base_atk, base_spa) >= 105:
            return {
                "role": "Trick Room Sweeper",
                "is_setter": False,
                "is_abuser": True,
                "prioritize_weather_moves": False,
                "prioritize_pivot": False,
                "preferred_item": "lifeorb"
            }

    # 3. Standard Roles
    if (base_hp + base_def + base_spd) >= 280 and max(base_atk, base_spa) <= 95:
        return {
            "role": "Defensive Wall / Tank",
            "is_setter": False,
            "is_abuser": False,
            "prioritize_weather_moves": False,
            "prioritize_pivot": True,
            "preferred_item": "leftovers"
        }
    elif base_atk >= 115 and base_atk > base_spa:
        return {
            "role": "Physical Wallbreaker",
            "is_setter": False,
            "is_abuser": False,
            "prioritize_weather_moves": False,
            "prioritize_pivot": False,
            "preferred_item": "choiceband"
        }
    elif base_spa >= 115:
        return {
            "role": "Special Wallbreaker",
            "is_setter": False,
            "is_abuser": False,
            "prioritize_weather_moves": False,
            "prioritize_pivot": False,
            "preferred_item": "choicespecs"
        }
        
    return {
        "role": "Balanced Pivot",
        "is_setter": False,
        "is_abuser": False,
        "prioritize_weather_moves": False,
        "prioritize_pivot": True,
        "preferred_item": "heavydutyboots"
    }

def evaluate_item_restrictions(item_id: str, category: str) -> float:
    """
    Evaluates item hard constraints.
    Example: Assault Vest strictly bans all Status moves (-999.0 penalty).
    """
    it = str(item_id).strip().lower().replace("-", "").replace(" ", "")
    cat = str(category).strip().lower()
    
    if it == "assaultvest" and cat == "status":
        return -999.0  # Impossible/illegal combination
        
    return 0.0

def score_item_priority(
    item_id: str,
    species_name: str,
    species_data: Dict[str, Any],
    moveset: Optional[List[Dict[str, Any]]] = None,
    ability: str = "",
    role_info: Optional[Dict[str, Any]] = None,
    archetype: str = "balance",
    top_meta_items: Optional[List[str]] = None,
    format_name: str = "gen9ou"
) -> float:
    """
    Evaluates recommendation priority for an item based on moveset, ability, role, bulk, and team context.
    Distinguishes: Legally valid != Strategically viable != Recommended != Highest-priority recommendation.
    """
    it = str(item_id).strip().lower().replace("-", "").replace(" ", "").replace("'", "")
    types = [t.lower() for t in species_data.get("types", [])]
    arch = str(archetype).strip().lower().replace(" ", "_")
    ab = str(ability).strip().lower().replace("-", "").replace(" ", "")
    moveset = moveset or []
    role_info = role_info or {}
    top_meta_items = [str(x).strip().lower().replace("-", "").replace(" ", "").replace("'", "") for x in (top_meta_items or [])]
    
    base_stats = species_data.get("baseStats", {"hp": 80, "atk": 80, "def": 80, "spa": 80, "spd": 80, "spe": 80})
    bulk = base_stats.get("hp", 80) + base_stats.get("def", 80) + base_stats.get("spd", 80)
    spe = base_stats.get("spe", 80)
    atk = base_stats.get("atk", 80)
    spa = base_stats.get("spa", 80)

    has_status_move = any(m.get("category") == "Status" for m in moveset)
    num_attacks = sum(1 for m in moveset if m.get("category") in ["Physical", "Special"])
    num_physical = sum(1 for m in moveset if m.get("category") == "Physical")
    num_special = sum(1 for m in moveset if m.get("category") == "Special")
    has_pivot = any(m.get("id") in ["uturn", "voltswitch", "flipturn", "partingshot", "teleport"] for m in moveset)
    has_multihit = any(m.get("id") in ["iciclespear", "bulletseed", "rockblast", "tailslap", "armthrust", "pinmissile", "scalehot", "populationbomb", "watershuriken"] for m in moveset)
    has_setup = any(m.get("role_tag") == "Setup / Stat Boost" for m in moveset)
    has_recovery = any(m.get("role_tag") == "Recovery / Sustain" for m in moveset)
    
    score = 0.0

    # 1. Assault Vest: Strictly banned with status moves
    if it == "assaultvest":
        if has_status_move:
            return -999.0
        if num_attacks >= 4 and bulk >= 240:
            score += 7.5
        else:
            score += 3.0

    # 2. Eviolite: Mandatory priority for NFE, completely invalid for fully evolved
    elif it == "eviolite":
        if species_data.get("evos"):
            score += 15.0  # Top tier priority for NFE defensive/support Pokémon
        else:
            return -999.0

    # 3. Weather Rocks for dedicated Weather Setters
    elif it in ["damprock", "heatrock", "smoothrock", "icyrock"]:
        is_setter = role_info.get("is_setter", False)
        rock_map = {"rain": "damprock", "sun": "heatrock", "sand": "smoothrock", "snow": "icyrock"}
        if is_setter and rock_map.get(arch) == it:
            score += 12.0
        else:
            score -= 10.0

    # 4. Paradox Booster Energy
    elif it == "boosterenergy":
        all_abs = [str(a).lower().replace("-", "").replace(" ", "") for a in species_data.get("abilities", {}).values()] if isinstance(species_data.get("abilities"), dict) else []
        if ab in ["protosynthesis", "quarkdrive"] or any(a in ["protosynthesis", "quarkdrive"] for a in all_abs):
            score += 8.5
        else:
            return -999.0

    # 5. Loaded Dice for Multi-Hit Moves
    elif it == "loadeddice":
        if has_multihit:
            score += 9.5
        else:
            score -= 8.0

    # 6. Status Orbs (Flame Orb / Toxic Orb)
    elif it in ["flameorb", "toxicorb"]:
        if ab in ["guts", "quickfeet", "toxicboost", "flareboost"]:
            score += 10.0
        elif ab == "poisonheal" and it == "toxicorb":
            score += 12.0
        elif any(m.get("id") == "facade" for m in moveset):
            score += 7.0
        else:
            score -= 12.0

    # 7. Heavy-Duty Boots (Stealth Rock Weakness & Pivoting)
    elif it == "heavydutyboots":
        sr_weak_types = {"flying", "fire", "bug", "ice"}
        sr_count = sum(1 for t in types if t in sr_weak_types)
        if sr_count >= 2:  # 4x weak to SR (e.g. Volcarona, Moltres, Charizard, Articuno)
            score += 10.0
        elif sr_count == 1:  # 2x weak to SR
            score += 5.5
        if has_pivot:
            score += 3.5

    # 8. Choice Items (Band / Specs / Scarf)
    elif it == "choiceband":
        if has_status_move:
            score -= 4.0
        if num_physical >= 3 and atk >= 110:
            score += 6.5
            if has_pivot:
                score += 2.5
    elif it == "choicespecs":
        if has_status_move:
            score -= 4.0
        if num_special >= 3 and spa >= 110:
            score += 6.5
            if has_pivot:
                score += 2.5
    elif it == "choicescarf":
        if has_status_move:
            score -= 3.0
        if 70 <= spe <= 115 and num_attacks >= 3:
            score += 6.0
            if has_pivot:
                score += 2.5

    # 9. Leftovers (Bulky Tanks, Setup Sweepers, Recovery)
    elif it == "leftovers":
        if bulk >= 270 or has_recovery or has_setup or role_info.get("role") in ["Defensive Wall / Tank", "Balanced Pivot"]:
            score += 6.0
        else:
            score += 2.5

    # 10. Focus Sash (Frail Fast Leads / Hyper Offense Sweepers)
    elif it == "focussash":
        if bulk < 225 and (arch == "hyper_offense" or spe >= 105):
            score += 6.5
        else:
            score += 2.0

    # 11. Life Orb (Wallbreakers, Sweepers)
    elif it == "lifeorb":
        if num_attacks >= 3 and max(atk, spa) >= 100:
            score += 5.5
            if has_setup:
                score += 1.5
        else:
            score += 2.0

    # 12. Rocky Helmet (High Physical Defense Tanks)
    elif it == "rockyhelmet":
        if base_stats.get("def", 80) >= 110 and (bulk >= 270 or has_recovery):
            score += 5.5
        else:
            score += 1.0

    # Meta Telemetry Prior Boost
    if it in top_meta_items:
        score += 2.5

    return score

def recommend_best_items(
    species_name: str,
    species_data: Dict[str, Any],
    archetype: str,
    role_info: Dict[str, Any],
    top_meta_items: List[str],
    moveset: Optional[List[Dict[str, Any]]] = None,
    ability: str = "",
    format_name: str = "gen9ou"
) -> List[str]:
    """
    Recommends competitive held items using multi-factor prioritization on candidate items.
    """
    types = [t.lower() for t in species_data.get("types", [])]
    arch = str(archetype).strip().lower()
    ab = str(ability).strip().lower()
    
    # 1. Gather all plausible candidate items
    candidates = set()

    # Required Item (e.g. Mega Stones like Metagrossite, Garchompite, or Orbs)
    req_item = species_data.get("requiredItem")
    if req_item:
        return [req_item]

    # NFE check
    if species_data.get("evos"):
        candidates.add("Eviolite")

    # Weather rocks
    if role_info.get("is_setter"):
        if arch == "rain": candidates.add("Damp Rock")
        elif arch == "sun": candidates.add("Heat Rock")
        elif arch == "sand": candidates.add("Smooth Rock")
        elif arch == "snow": candidates.add("Icy Rock")

    # Boots for SR weak
    sr_weak_types = {"flying", "fire", "bug", "ice"}
    if any(t in sr_weak_types for t in types):
        candidates.add("Heavy-Duty Boots")

    # Booster Energy for Paradox
    all_abs = [str(a).lower() for a in species_data.get("abilities", {}).values()] if isinstance(species_data.get("abilities"), dict) else []
    if ab in ["protosynthesis", "quarkdrive"] or any(a in ["protosynthesis", "quarkdrive"] for a in all_abs):
        candidates.add("Booster Energy")

    # Status Orbs
    if ab in ["guts", "quickfeet", "toxicboost", "flareboost"]:
        candidates.add("Flame Orb")
    elif ab == "poisonheal":
        candidates.add("Toxic Orb")

    # Loaded Dice for multi-hit moves
    moveset = moveset or []
    if any(m.get("id") in ["iciclespear", "bulletseed", "rockblast", "tailslap", "armthrust", "pinmissile", "scalehot", "populationbomb"] for m in moveset):
        candidates.add("Loaded Dice")

    # Telemetry candidates
    for m_it in top_meta_items:
        clean_it = m_it.replace("-", " ").title()
        candidates.add(clean_it)

    # Standard fallback competitive items
    fallbacks = ["Leftovers", "Life Orb", "Choice Scarf", "Choice Band", "Choice Specs", "Focus Sash", "Assault Vest", "Rocky Helmet", "Heavy-Duty Boots"]
    for fb in fallbacks:
        candidates.add(fb)

    # 2. Score and prioritize candidate items
    scored_items = []
    for it_cand in candidates:
        p_score = score_item_priority(
            item_id=it_cand,
            species_name=species_name,
            species_data=species_data,
            moveset=moveset,
            ability=ability,
            role_info=role_info,
            archetype=archetype,
            top_meta_items=top_meta_items,
            format_name=format_name
        )
        if p_score > -50.0:  # Exclude disqualified / impossible items
            scored_items.append((it_cand, p_score))

    scored_items.sort(key=lambda x: x[1], reverse=True)
    # Deduplicate normalized names preserving highest ranked instance
    seen_norm = set()
    deduped = []
    for it_cand, p_score in scored_items:
        norm = it_cand.lower().replace("-", "").replace(" ", "").replace("'", "")
        if norm not in seen_norm:
            seen_norm.add(norm)
            display_name = it_cand.replace("-", " ").title()
            if norm == "heavydutyboots": display_name = "Heavy-Duty Boots"
            elif norm == "lifeorb": display_name = "Life Orb"
            elif norm == "choicescarf": display_name = "Choice Scarf"
            elif norm == "choiceband": display_name = "Choice Band"
            elif norm == "choicespecs": display_name = "Choice Specs"
            elif norm == "focussash": display_name = "Focus Sash"
            elif norm == "assaultvest": display_name = "Assault Vest"
            elif norm == "rockyhelmet": display_name = "Rocky Helmet"
            elif norm == "loadeddice": display_name = "Loaded Dice"
            elif norm == "boosterenergy": display_name = "Booster Energy"
            elif norm == "damprock": display_name = "Damp Rock"
            elif norm == "heatrock": display_name = "Heat Rock"
            elif norm == "smoothrock": display_name = "Smooth Rock"
            elif norm == "icyrock": display_name = "Icy Rock"
            elif norm == "flameorb": display_name = "Flame Orb"
            elif norm == "toxicorb": display_name = "Toxic Orb"
            deduped.append(display_name)
    return deduped[:3]

def recommend_best_abilities(
    species_name: str,
    species_data: Dict[str, Any],
    moveset: Optional[List[Dict[str, Any]]] = None,
    archetype: str = "balance",
    role_info: Optional[Dict[str, Any]] = None,
    item: str = "",
    format_name: str = "gen9ou"
) -> List[Dict[str, Any]]:
    """
    Recommends and ranks legal abilities for a Pokémon based on moveset synergy, archetype, role, and mechanics.
    """
    raw_abilities = species_data.get("abilities", {})
    if not isinstance(raw_abilities, dict):
        return []
        
    moveset = moveset or []
    arch = str(archetype).strip().lower().replace(" ", "_")
    role_info = role_info or {}
    it = str(item).strip().lower().replace("-", "").replace(" ", "")
    base_stats = species_data.get("baseStats", {"hp": 80, "atk": 80, "def": 80, "spa": 80, "spd": 80, "spe": 80})
    bulk = base_stats.get("hp", 80) + base_stats.get("def", 80) + base_stats.get("spd", 80)
    is_doubles = "vgc" in format_name.lower() or "doubles" in format_name.lower()

    ranked = []
    
    for slot, ab_name in raw_abilities.items():
        ab_id = str(ab_name).strip().lower().replace("-", "").replace(" ", "")
        is_hidden = (slot == "H")
        score = 3.0  # Base viability score
        reasons = []

        # 1. Weather / Terrain Setter
        if arch in ["rain", "sun", "sand", "snow"]:
            if ab_id in WEATHER_SETTER_ABILITIES.get(arch, set()):
                score += 12.0
                reasons.append(f"Sets {arch.capitalize()} weather to power the entire team strategy")
            elif ab_id in WEATHER_ABUSER_ABILITIES.get(arch, set()):
                score += 8.5
                reasons.append(f"Directly activates speed or power boost under {arch.capitalize()}")
        elif ab_id in {"drizzle", "drought", "sandstream", "snowwarning"}:
            score += 5.0
            reasons.append("Sets battle weather on entry")

        # 2. Terrain Abilities
        if ab_id in {"electricsurge", "grassysurge", "psychicsurge", "hadronengine"}:
            score += 7.0
            reasons.append("Sets terrain on entry enhancing moves and team capabilities")

        # 3. Paradox Abilities (Protosynthesis / Quark Drive)
        if ab_id in ["protosynthesis", "quarkdrive"]:
            if arch in ["sun", "electric"] or it == "boosterenergy":
                score += 7.5
                reasons.append("Activates highest stat boost under active field or Booster Energy")
            else:
                score += 4.0
                reasons.append("Provides stat boost when powered by field or Booster Energy")

        # 4. Moveset-Dependent Synergies (Bi-directional synergy)
        # Tough Claws: contact moves (1.3x boost)
        contact_moves = [m.get("name") for m in moveset if m.get("flags", {}).get("contact") or m.get("id") in ["meteormash", "bulletpunch", "knockoff", "psychicfangs", "hammerarm", "icepunch", "thunderpunch", "firepunch", "drainpunch", "crunch", "playrough", "closecombat", "liquidation", "bravebird", "flareblitz"]]
        if ab_id == "toughclaws" and contact_moves:
            score += len(contact_moves) * 2.8
            reasons.append(f"Boosts contact attacks by 1.3x ({', '.join(contact_moves[:2])})")

        # Sharpness: slicing moves
        slicing_moves = [m.get("name") for m in moveset if m.get("id") in ["sacredsword", "bitterblade", "aquacutter", "slash", "nightslash", "aircutter", "leafblade", "ceaselessedge", "psychocut", "xscissor", "crosspoison", "aerialace", "furycutter", "stoneaxe", "kowtowcleave"]]
        if ab_id == "sharpness" and slicing_moves:
            score += len(slicing_moves) * 2.5
            reasons.append(f"Boosts slicing attacks by 1.5x ({', '.join(slicing_moves[:2])})")

        # Iron Fist: punching moves
        punching_moves = [m.get("name") for m in moveset if m.get("id") in ["drainpunch", "thunderpunch", "icepunch", "firepunch", "machpunch", "bulletpunch", "hammerarm", "jetpunch", "meteormash", "shadowpunch", "headlongrush", "ragefist", "surgingstrikes", "wickedblow", "dynamicpunch", "focuspunch"]]
        if ab_id == "ironfist" and punching_moves:
            score += len(punching_moves) * 2.2
            reasons.append(f"Boosts punch attacks by 1.2x ({', '.join(punching_moves[:2])})")

        # Strong Jaw: biting moves
        biting_moves = [m.get("name") for m in moveset if m.get("id") in ["crunch", "psychicfangs", "firefang", "icefang", "thunderfang", "fishiousrend", "bite", "poisonfang", "hyperfang"]]
        if ab_id == "strongjaw" and biting_moves:
            score += len(biting_moves) * 2.5
            reasons.append(f"Boosts biting attacks by 1.5x ({', '.join(biting_moves[:2])})")

        # Punk Rock: sound moves
        sound_moves = [m.get("name") for m in moveset if m.get("id") in ["hypervoice", "boomburst", "bugbuzz", "torchsong", "overdrive", "snarl", "alluringvoice"]]
        if ab_id == "punkrock" and sound_moves:
            score += len(sound_moves) * 2.5
            reasons.append(f"Boosts sound attacks by 1.3x and provides sound damage resistance")

        # Technician: moves <= 60 BP
        tech_moves = [m.get("name") for m in moveset if m.get("power", 0) > 0 and m.get("power", 0) <= 60]
        if ab_id == "technician" and tech_moves:
            score += len(tech_moves) * 2.2
            reasons.append(f"Boosts low-BP moves (<=60 BP) by 1.5x ({', '.join(tech_moves[:2])})")

        # Skill Link: multi-hit moves
        multihit_moves = [m.get("name") for m in moveset if m.get("id") in ["iciclespear", "bulletseed", "rockblast", "tailslap", "armthrust", "pinmissile", "scalehot", "populationbomb", "watershuriken"]]
        if ab_id == "skilllink" and multihit_moves:
            score += len(multihit_moves) * 3.5
            reasons.append(f"Guarantees multi-hit attacks strike the maximum 5 times ({', '.join(multihit_moves[:2])})")

        # Sheer Force: moves with secondary effects
        sf_moves = [m.get("name") for m in moveset if m.get("id") in ["ironhead", "fireblast", "icebeam", "thunderbolt", "earthpower", "sludgebomb", "flashcannon", "flamethrower", "energyball", "psychic", "crunch"]]
        if ab_id == "sheerforce" and sf_moves:
            score += len(sf_moves) * 2.2
            reasons.append(f"Boosts attacks with secondary effects by 1.3x")

        # Adaptability: STAB attacks
        user_types = [t.lower() for t in species_data.get("types", [])]
        stab_attacks = [m.get("name") for m in moveset if m.get("type", "").lower() in user_types and m.get("category") != "Status"]
        if ab_id == "adaptability" and stab_attacks:
            score += len(stab_attacks) * 2.5
            reasons.append(f"Increases STAB multiplier from 1.5x to 2.0x")

        # Guts / Poison Heal
        if ab_id == "guts":
            score += 7.0
            reasons.append("Grants 1.5x Attack boost when inflicted with status")
        elif ab_id == "poisonheal":
            score += 8.5
            reasons.append("Restores 1/8 max HP every turn when poisoned instead of taking damage")

        # Protean / Libero
        if ab_id in ["protean", "libero"]:
            score += 6.5
            reasons.append("Changes user typing to matching move granting STAB on all attacks")

        # 5. Universal Competitive & Defensive Staples
        if ab_id == "regenerator":
            score += 8.5 if bulk >= 250 else 5.0
            reasons.append("Restores 33% max HP upon switching out, ensuring high longevity")
        elif ab_id == "magicguard":
            score += 8.5
            reasons.append("Prevents all passive indirect damage (hazards, weather, Life Orb recoil)")
        elif ab_id in ["multiscale", "shadowshield"]:
            score += 8.5
            reasons.append("Halves damage taken when at full HP, preventing one-hit knockouts")
        elif ab_id == "supremeoverlord":
            score += 8.5
            reasons.append("Increases Attack by up to 50% for each defeated ally")
        elif ab_id in ["defiant", "competitive"]:
            stat_name = "Attack" if ab_id == "defiant" else "Sp. Atk"
            score += 7.0
            reasons.append(f"Raises {stat_name} by +2 whenever an opponent lowers any stat")
        elif ab_id == "unaware":
            score += 7.5
            reasons.append("Ignores opposing stat boosts during damage calculation")
        elif ab_id == "prankster":
            has_status = any(m.get("category") == "Status" for m in moveset)
            score += 8.0 if has_status else 3.0
            reasons.append("Grants +1 priority to non-damaging status and utility moves")
        elif ab_id == "intimidate":
            score += 9.0 if is_doubles else 7.5
            reasons.append("Lowers opponent Attack by 1 stage upon entry, reducing physical pressure")
        elif ab_id == "goodasgold":
            score += 9.0
            reasons.append("Provides total immunity to all opposing status moves")
        elif ab_id == "purifyingsalt":
            score += 8.0
            reasons.append("Grants immunity to all status conditions and halves Ghost-type damage taken")
        elif ab_id == "stamina":
            score += 7.5
            reasons.append("Raises Defense by +1 each time this Pokémon is hit by an attack")
        elif ab_id in ["hugepower", "purepower"]:
            score += 10.0
            reasons.append("Doubles the Pokémon's raw Attack stat")
        elif ab_id == "speedboost":
            score += 7.5
            reasons.append("Raises Speed by +1 at the end of every turn")
        elif ab_id in ["waterabsorb", "stormdrain", "voltabsorb", "lightningrod", "flashfire", "wellbakedbody", "levitate", "eartheater"]:
            score += 6.0
            reasons.append(f"Provides complete elemental immunity and utility against opposing attacks")
        elif ab_id == "naturalcure":
            score += 5.5
            reasons.append("Cures all status conditions upon switching out")

        # 6. Additional Ability Differentiation & Tie-Breaking
        # Primary competitive ability differentiation (e.g. Clear Body over Light Metal)
        if ab_id == "clearbody":
            score += 3.5
            reasons.append("Prevents opposing stat drops (Intimidate, Icy Wind, Sticky Web)")
        elif ab_id == "lightmetal":
            score -= 1.0  # Light Metal increases Low Kick / Grass Knot damage taken on heavy Pokémon
            reasons.append("Halves weight, which can slightly reduce damage taken from weight-based moves")
        elif ab_id == "levitate":
            score += 4.5
            reasons.append("Grants complete immunity to Ground-type attacks and Spikes hazards")
        elif ab_id == "thickfat":
            score += 3.0
            reasons.append("Halves Fire and Ice type damage taken")
        elif ab_id == "overcoat":
            score += 2.0
            reasons.append("Grants immunity to powder moves and weather damage")
        elif ab_id == "bulletproof":
            score += 3.0
            reasons.append("Grants immunity to ball and bomb moves (Shadow Ball, Sludge Bomb, Focus Blast)")
        elif ab_id == "filter" or ab_id == "solidrock" or ab_id == "prismarmor":
            score += 3.5
            reasons.append("Reduces super-effective damage taken by 25%")
        elif ab_id == "magicbounce":
            score += 5.0
            reasons.append("Reflects status, hazard, and stat-lowering moves back at the attacker")

        # Slot-based slight tie-breaker if scores remain identical (e.g., standard slot 1 vs hidden ability)
        if is_hidden:
            score -= 0.1  # Slight tie-breaker penalty if otherwise identical, favoring standard non-hidden abilities

        rationale = ". ".join(reasons) + "." if reasons else f"Standard competitive ability option for {species_name}."

        ranked.append({
            "name": ab_name,
            "is_hidden": is_hidden,
            "score": round(score, 2),
            "rationale": rationale
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked

