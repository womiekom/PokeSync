import os
import sys
import json
import urllib.request
import re

def to_canonical_id(name: str) -> str:
    """Normalizes a name to lowercase alphanumeric ID."""
    return re.sub(r'[^a-z0-9]', '', name.lower().strip())

def fetch_json(url: str, timeout=15):
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content = resp.read().decode('utf-8', errors='replace')
        return json.loads(content)

def ingest_meta():
    print("=== PokeSync Smogon Meta Ingestion ===")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(base_dir, "app", "data", "meta_data")
    os.makedirs(target_dir, exist_ok=True)

    # 1. Gen 9 OU (1825 high-ladder)
    ou_urls = [
        "https://www.smogon.com/stats/2026-07/chaos/gen9ou-1825.json",
        "https://www.smogon.com/stats/2024-12/chaos/gen9ou-1825.json",
        "https://www.smogon.com/stats/2024-06/chaos/gen9ou-1825.json"
    ]
    for u in ou_urls:
        try:
            print(f"Fetching OU telemetry from {u}...")
            raw_data = fetch_json(u)
            if raw_data and 'data' in raw_data:
                normalized_ou = {
                    "metagame": raw_data.get("info", {}).get("metagame", "gen9ou"),
                    "cutoff": raw_data.get("info", {}).get("cutoff", 1825),
                    "total_battles": raw_data.get("info", {}).get("number of battles", 0),
                    "pokemon": {}
                }
                for p_name, p_info in raw_data["data"].items():
                    c_id = to_canonical_id(p_name)
                    normalized_ou["pokemon"][c_id] = {
                        "name": p_name,
                        "usage": p_info.get("usage", 0.0),
                        "raw_count": p_info.get("Raw count", 0),
                        "moves": {to_canonical_id(k): v for k, v in p_info.get("Moves", {}).items()},
                        "items": {to_canonical_id(k): v for k, v in p_info.get("Items", {}).items()},
                        "abilities": {to_canonical_id(k): v for k, v in p_info.get("Abilities", {}).items()},
                        "spreads": p_info.get("Spreads", {}),
                        "teammates": {to_canonical_id(k): v for k, v in p_info.get("Teammates", {}).items()},
                        "tera_types": {k.lower(): v for k, v in p_info.get("Tera Types", {}).items()}
                    }
                out_ou = os.path.join(target_dir, "gen9ou.json")
                with open(out_ou, "w", encoding="utf-8") as f:
                    json.dump(normalized_ou, f, ensure_ascii=False, indent=2)
                print(f"Saved normalized gen9ou.json ({len(normalized_ou['pokemon'])} Pokémon) -> {out_ou}")
                break
        except Exception as e:
            print(f"Error fetching OU from {u}: {e}")

    # 2. Gen 9 VGC (1760 high-ladder)
    vgc_urls = [
        "https://www.smogon.com/stats/2023-06/chaos/gen9vgc2023regulationc-1760.json",
        "https://www.smogon.com/stats/2024-01/chaos/gen9vgc2024regf-1760.json",
        "https://www.smogon.com/stats/2024-06/chaos/gen9doublesou-1695.json",
        "https://www.smogon.com/stats/2026-07/chaos/gen9doublesou-1695.json"
    ]
    for u in vgc_urls:
        try:
            print(f"Fetching VGC telemetry from {u}...")
            raw_data = fetch_json(u)
            if raw_data and 'data' in raw_data:
                normalized_vgc = {
                    "metagame": raw_data.get("info", {}).get("metagame", "gen9vgc"),
                    "cutoff": raw_data.get("info", {}).get("cutoff", 1760),
                    "total_battles": raw_data.get("info", {}).get("number of battles", 0),
                    "pokemon": {}
                }
                for p_name, p_info in raw_data["data"].items():
                    c_id = to_canonical_id(p_name)
                    normalized_vgc["pokemon"][c_id] = {
                        "name": p_name,
                        "usage": p_info.get("usage", 0.0),
                        "raw_count": p_info.get("Raw count", 0),
                        "moves": {to_canonical_id(k): v for k, v in p_info.get("Moves", {}).items()},
                        "items": {to_canonical_id(k): v for k, v in p_info.get("Items", {}).items()},
                        "abilities": {to_canonical_id(k): v for k, v in p_info.get("Abilities", {}).items()},
                        "spreads": p_info.get("Spreads", {}),
                        "teammates": {to_canonical_id(k): v for k, v in p_info.get("Teammates", {}).items()},
                        "tera_types": {k.lower(): v for k, v in p_info.get("Tera Types", {}).items()}
                    }
                out_vgc = os.path.join(target_dir, "gen9vgc.json")
                with open(out_vgc, "w", encoding="utf-8") as f:
                    json.dump(normalized_vgc, f, ensure_ascii=False, indent=2)
                print(f"Saved normalized gen9vgc.json ({len(normalized_vgc['pokemon'])} Pokémon) -> {out_vgc}")
                break
        except Exception as e:
            print(f"Error fetching VGC from {u}: {e}")

    print("=== Meta Ingestion Complete ===")

if __name__ == "__main__":
    ingest_meta()
