
import pandas as pd
import os

def load_and_clean_data(pokemon_path: str, types_path: str):
    df_pokemon = pd.read_csv(pokemon_path)
    df_types = pd.read_csv(types_path)

    # Clean column names
    df_pokemon.columns = (
        df_pokemon.columns
        .str.lower()
        .str.strip()
        .str.replace(" ", "_")
    )

    df_types.columns = (
        df_types.columns
        .str.lower()
        .str.strip()
        .str.replace(" ", "_")
    )

    # Clean names and types
    df_pokemon["name"] = (
        df_pokemon["name"]
        .str.lower()
        .str.strip()
        .str.replace(" ", "-", regex=False)
    )

    for col in ["type_1", "type_2"]:
        df_pokemon[col] = (
            df_pokemon[col]
            .fillna("none")
            .str.lower()
            .str.strip()
            .str.replace(" ", "-", regex=False)
        )

    # Clean abilities
    df_pokemon["abilities"] = (
        df_pokemon["abilities"]
        .fillna("")
        .str.lower()
        .str.strip()
    )

    df_pokemon["hidden_ability"] = (
        df_pokemon["hidden_ability"]
        .fillna("")
        .str.lower()
        .str.strip()
    )

    def split_abilities(ability_string):
        if not ability_string:
            return []
        return [
            a.strip().replace(" ", "-")
            for a in ability_string.split("|")
        ]

    df_pokemon["ability_list"] = df_pokemon["abilities"].apply(split_abilities)
    df_pokemon["hidden_ability_list"] = df_pokemon["hidden_ability"].apply(split_abilities)
    
    df_pokemon["all_abilities"] = (
        df_pokemon["ability_list"] +
        df_pokemon["hidden_ability_list"]
    )

    return df_pokemon, df_types
