import os
import sys
import json
import urllib.request
import re

def extract_data():
    print("=== PokeSync Game Data Extractor ===")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(base_dir, "app", "data", "game_data")
    os.makedirs(target_dir, exist_ok=True)

    headers = {'User-Agent': 'Mozilla/5.0'}

    # 1. Pokedex, Moves, Learnsets from Showdown
    primary_urls = {
        "pokedex.json": "https://play.pokemonshowdown.com/data/pokedex.json",
        "moves.json": "https://play.pokemonshowdown.com/data/moves.json",
        "learnsets.json": "https://play.pokemonshowdown.com/data/learnsets.json",
    }

    for filename, url in primary_urls.items():
        out_path = os.path.join(target_dir, filename)
        print(f"Fetching {filename} from {url}...")
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"Saved {filename} ({len(data)} entries) -> {out_path}")
        except Exception as e:
            print(f"Error fetching {filename}: {e}")

    # 2. Formats Data (Tiers)
    formats_ts_url = "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/formats-data.ts"
    try:
        print(f"Fetching formats-data from {formats_ts_url}...")
        req = urllib.request.Request(formats_ts_url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            ts_content = resp.read().decode('utf-8')
            formats_data = {}
            entries = re.findall(r'(\w+):\s*\{([^}]+)\}', ts_content)
            for key, body in entries:
                tier_match = re.search(r'tier:\s*["\']([^"\']+)["\']', body)
                doubles_tier = re.search(r'doublesTier:\s*["\']([^"\']+)["\']', body)
                is_nonstandard = re.search(r'isNonstandard:\s*["\']([^"\']+)["\']', body)
                formats_data[key] = {
                    "tier": tier_match.group(1) if tier_match else "Illegal",
                    "doublesTier": doubles_tier.group(1) if doubles_tier else "Illegal",
                    "isNonstandard": is_nonstandard.group(1) if is_nonstandard else None
                }
            
            formats_out = os.path.join(target_dir, "formats.json")
            with open(formats_out, "w", encoding="utf-8") as f:
                json.dump(formats_data, f, ensure_ascii=False, indent=2)
            print(f"Saved formats.json ({len(formats_data)} entries) -> {formats_out}")
    except Exception as e:
        print(f"Error extracting formats: {e}")

    # 3. Items & Abilities
    for asset_name in ["items", "abilities"]:
        url = f"https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/{asset_name}.ts"
        out_path = os.path.join(target_dir, f"{asset_name}.json")
        try:
            print(f"Fetching {asset_name} from {url}...")
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                ts_content = resp.read().decode('utf-8')
                asset_data = {}
                entries = re.findall(r'(\w+):\s*\{([^}]+)\}', ts_content)
                for key, body in entries:
                    name_match = re.search(r'name:\s*["\']([^"\']+)["\']', body)
                    desc_match = re.search(r'desc:\s*["\']([^"\']+)["\']', body)
                    short_desc = re.search(r'shortDesc:\s*["\']([^"\']+)["\']', body)
                    asset_data[key] = {
                        "name": name_match.group(1) if name_match else key,
                        "desc": desc_match.group(1) if desc_match else (short_desc.group(1) if short_desc else "")
                    }
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(asset_data, f, ensure_ascii=False, indent=2)
                print(f"Saved {asset_name}.json ({len(asset_data)} entries) -> {out_path}")
        except Exception as e:
            print(f"Error extracting {asset_name}: {e}")

    print("=== Extraction Complete ===")

if __name__ == "__main__":
    extract_data()
