
import random
import pandas as pd
from app.ml.strategies import STRATEGIES
from app.ml.feature_engineering import extract_team_features

def get_pokemon_with_ability(df, abilities):
    abilities = set(abilities)
    result = df[
        df["all_abilities"].apply(
            lambda x: any(a in abilities for a in x)
        )
    ]
    return list(result["name"])

def random_pokemon(df, exclude=[]):
    pool = list(set(df["name"]) - set(exclude))
    return random.choice(pool)

def build_team(core_pokemon, df, size=6):
    team = core_pokemon.copy()
    while len(team) < size:
        mon = random_pokemon(df, exclude=team)
        team.append(mon)
    return team

def generate_weather_team(df, weather):
    setters = get_pokemon_with_ability(df, STRATEGIES[weather]["weather_abilities"])
    abusers = get_pokemon_with_ability(df, STRATEGIES[weather]["weather_abuser_abilities"])

    if not setters or not abusers:
        return None

    setter = random.choice(setters)
    selected_abusers = random.sample(abusers, k=min(2, len(abusers)))

    core = [setter] + selected_abusers
    while len(core) < 4:
        extra = random.choice(abusers)
        if extra not in core:
            core.append(extra)
    return build_team(core, df)

def generate_rain_team(df): return generate_weather_team(df, "rain")
def generate_sun_team(df): return generate_weather_team(df, "sun")
def generate_sand_team(df): return generate_weather_team(df, "sand")
def generate_snow_team(df): return generate_weather_team(df, "snow")

def generate_trick_room_team(df):
    setter = random.choice(STRATEGIES["trick_room"]["setters"])
    abusers = random.sample(
        STRATEGIES["trick_room"]["abusers"], 
        k=min(3, len(STRATEGIES["trick_room"]["abusers"]))
    )
    core = [setter] + abusers
    slow_pool = df[df["speed"] <= 60]
    while len(core) < 6:
        mon = random.choice(list(slow_pool["name"]))
        if mon not in core:
            core.append(mon)
    return core

def generate_hyper_offense_team(df, all_setters):
    offensive_pool = df[
        (df["speed"] >= 100) & ((df["attack"] + df["sp_attack"]) >= 230)
    ]
    offensive_pool = offensive_pool[~offensive_pool["name"].isin(all_setters)]
    if len(offensive_pool) < 6: return None
    return random.sample(list(offensive_pool["name"]), 6)

def generate_stall_team(df, all_setters):
    bulky_pool = df[
        (df["hp"] + df["defense"] + df["sp_defense"]) >= 320
    ]
    bulky_pool = bulky_pool[bulky_pool["speed"] <= 85]
    bulky_pool = bulky_pool[~bulky_pool["name"].isin(all_setters)]
    if len(bulky_pool) < 6: return None
    return random.sample(list(bulky_pool["name"]), 6)

def generate_balance_team(df, all_setters):
    balance_pool = df[
        ((df["attack"] + df["sp_attack"]) >= 170) & 
        ((df["hp"] + df["defense"] + df["sp_defense"]) >= 240) & 
        (df["speed"] >= 65) & (df["speed"] <= 100)
    ]
    balance_pool = balance_pool[~balance_pool["name"].isin(all_setters)]
    if len(balance_pool) < 6: return None
    return random.sample(list(balance_pool["name"]), 6)

TEAM_GENERATORS = {
    "rain": generate_rain_team,
    "sun": generate_sun_team,
    "sand": generate_sand_team,
    "snow": generate_snow_team,
    "trick_room": generate_trick_room_team,
    "hyper_offense": generate_hyper_offense_team,
    "stall": generate_stall_team,
    "balance": generate_balance_team
}

def build_dataset(df, samples_per_class=500):
    all_weather_setters = set()
    for weather in ["rain", "sun", "sand", "snow"]:
        setters = get_pokemon_with_ability(df, STRATEGIES[weather]["weather_abilities"])
        all_weather_setters.update(setters)
    
    all_setters = all_weather_setters | set(STRATEGIES["trick_room"]["setters"])

    X = []
    y = []

    for label, generator in TEAM_GENERATORS.items():
        print(f"Generating {label} teams...")
        generated = 0
        while generated < samples_per_class:
            try:
                if label in ["hyper_offense", "stall", "balance"]:
                    team = generator(df, all_setters)
                else:
                    team = generator(df)
                
                if team is None: continue

                features = extract_team_features(team, df)
                if features is None: continue

                X.append(features)
                y.append(label)
                generated += 1
            except Exception as e:
                print(f"Error in {label}: {e}")

    X_df = pd.DataFrame(X)
    X_df = X_df.apply(pd.to_numeric, errors="coerce").fillna(0)
    return X_df, y
