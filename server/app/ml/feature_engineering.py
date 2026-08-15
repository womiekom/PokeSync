
import pandas as pd
from app.ml.strategies import STRATEGIES

def extract_team_features(team, df):
    team = [
        p.lower().replace(" ", "-")
        for p in team
    ]

    selected = df[
        df["name"].isin(team)
    ].copy()

    if len(selected) == 0:
        return None

    features = {}
    features["team_size"] = len(team)

    stats = [
        "hp", "attack", "defense", "sp_attack", "sp_defense", "speed", "base_stat_total"
    ]

    for stat in stats:
        features[f"avg_{stat}"] = selected[stat].mean()

    bulk_series = (
        selected["hp"] +
        selected["defense"] +
        selected["sp_defense"]
    )

    offense_series = (
        selected["attack"] +
        selected["sp_attack"]
    )

    features["avg_bulk"] = bulk_series.mean()
    features["avg_offense"] = offense_series.mean()

    features["fast_count"] = int(sum(selected["speed"] >= 100))
    features["slow_count"] = int(sum(selected["speed"] <= 60))
    features["very_slow_count"] = int(sum(selected["speed"] <= 40))
    features["speed_variance"] = selected["speed"].std()

    features["bulky_count"] = int(sum(bulk_series >= 300))
    features["very_bulky_count"] = int(sum(bulk_series >= 360))
    features["frail_count"] = int(sum(bulk_series <= 220))
    features["bulk_variance"] = bulk_series.std()

    physical_attackers = int(sum(selected["attack"] > selected["sp_attack"]))
    special_attackers = int(sum(selected["sp_attack"] > selected["attack"]))
    mixed_attackers = int(sum(abs(selected["attack"] - selected["sp_attack"]) <= 15))

    features["physical_attackers"] = physical_attackers
    features["special_attackers"] = special_attackers
    features["mixed_attackers"] = mixed_attackers

    features["offense_balance"] = abs(
        selected["attack"].mean() - selected["sp_attack"].mean()
    )

    features["defense_balance"] = abs(
        selected["defense"].mean() - selected["sp_defense"].mean()
    )

    for weather in ["rain", "sun", "sand", "snow"]:
        setter_abilities = set(STRATEGIES[weather]["weather_abilities"])
        abuser_abilities = set(STRATEGIES[weather]["weather_abuser_abilities"])

        setter_count = sum(
            any(a in setter_abilities for a in abilities)
            for abilities in selected["all_abilities"]
        )

        abuser_count = sum(
            any(a in abuser_abilities for a in abilities)
            for abilities in selected["all_abilities"]
        )

        features[f"{weather}_setter_count"] = setter_count
        features[f"{weather}_abuser_count"] = abuser_count
        features[f"{weather}_synergy"] = setter_count * 3 + abuser_count

    team_set = set(team)
    tr_setters = set(STRATEGIES["trick_room"]["setters"])
    tr_abusers = set(STRATEGIES["trick_room"]["abusers"])

    tr_setter_count = len(team_set & tr_setters)
    tr_abuser_count = len(team_set & tr_abusers)

    features["trick_room_setter_count"] = tr_setter_count
    features["trick_room_abuser_count"] = tr_abuser_count
    features["trick_room_synergy"] = tr_setter_count * 3 + tr_abuser_count

    features["stall_score"] = (
        features["very_bulky_count"] * 2 +
        features["bulky_count"] +
        features["slow_count"]
    )

    features["hyper_offense_score"] = (
        features["fast_count"] * 2 +
        features["frail_count"]
    )

    features["balance_score"] = abs(
        features["physical_attackers"] - features["special_attackers"]
    )

    return features
