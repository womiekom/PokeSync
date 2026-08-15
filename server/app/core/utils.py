
def get_sugimori_url(pokedex_number: int) -> str:
    """Returns the official Sugimori-style artwork URL for a given pokedex number."""
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{pokedex_number}.png"

def get_pokemon_data(team: list, df_pokemon):
    """Returns a list of pokemon data including names and sugimori URLs."""
    team_data = []
    normalized_names = [p.lower().replace(" ", "-") for p in team]
    
    # Use a dictionary to keep track of seen names to handle order and potential duplicates (though validation should catch them)
    selected = df_pokemon[df_pokemon["name"].isin(normalized_names)].copy()
    
    # Create a mapping for easy lookup
    mapping = {row["name"]: row for _, row in selected.iterrows()}
    
    for name in normalized_names:
        if name in mapping:
            row = mapping[name]
            team_data.append({
                "name": row["name"].capitalize(),
                "pokedex_number": int(row["pokedex_number"]),
                "image_url": get_sugimori_url(int(row["pokedex_number"])),
                "types": [row["type_1"], row["type_2"]] if row["type_2"] != "none" else [row["type_1"]]
            })
    return team_data
