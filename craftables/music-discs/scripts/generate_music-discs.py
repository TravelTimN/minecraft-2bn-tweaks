import os
import json
from disc_recipes import DISCS_BY_PACK

# === Configuration === #
NAMESPACE = "music-discs"

# Recipe formats per version range
RECIPE_FORMATS = {
    "item": range(0, 48),       # pack < 48
    "id": range(48, 57),        # pack 48–56
    "flat": range(57, 999),     # pack 57+
}

# Simulated overlays for version formatting
SIMULATED_OVERLAYS = {
    57: ["legacy", 48],
}

# === Helpers === #
def get_recipe_format(pack):
    if pack == "legacy":
        return "item"
    for fmt, rng in RECIPE_FORMATS.items():
        if isinstance(pack, int) and pack in rng:
            return fmt
    raise ValueError(f"Unknown format for pack: {pack}")


def get_output_path(pack):
    if pack == "legacy" or (isinstance(pack, int) and pack < 48):
        folder = "recipes"
    else:
        folder = "recipe"

    if pack == "legacy":
        base = "data"
    else:
        base = f"overlay_{pack}/data"
    return os.path.join("..", base, NAMESPACE, folder)


# === Determine all packs to process === #
all_packs = set(DISCS_BY_PACK.keys())
all_packs.update(SIMULATED_OVERLAYS.keys())
all_packs = sorted(all_packs, key=lambda x: (0 if x == "legacy" else int(x)))


# === Recipe Generation === #
recipe_counts = {}
for pack in all_packs:
    fmt = get_recipe_format(pack)
    output_path = get_output_path(pack)
    os.makedirs(output_path, exist_ok=True)
    count = 0

    # Collect all disc recipes valid for this pack, avoiding duplicates
    if pack in SIMULATED_OVERLAYS:
        source_packs = SIMULATED_OVERLAYS[pack]
    else:
        source_packs = [p for p in all_packs if p == "legacy" or (isinstance(p, int) and isinstance(pack, int) and p <= pack)]

    seen_discs = set()
    recipes = []
    for source_pack in source_packs:
        for disc_def in DISCS_BY_PACK.get(source_pack, []):
            disc_id = disc_def["disc"]
            if disc_id not in seen_discs:
                seen_discs.add(disc_id)
                recipes.append(disc_def)

    for disc_def in recipes:
        disc_id = disc_def["disc"]
        pattern = disc_def["pattern"]
        ingredients = disc_def["ingredients"]
        result_count = disc_def.get("count", 1)

        if fmt == "flat":
            # Ingredients as flat string mappings
            key = {letter: f"minecraft:{item}" for letter, item in ingredients.items()}
            result = {
                "id": f"minecraft:{disc_id}",
                "count": result_count
            }
        else:
            # Use item or id in result and ingredients
            if fmt == "id":
                result_key = "id"
            else:
                result_key = "item"

            key = {
                letter: {"item": f"minecraft:{item}"}
                for letter, item in ingredients.items()
            }
            result = {
                result_key: f"minecraft:{disc_id}",
                "count": result_count
            }

        recipe = {
            "type": "minecraft:crafting_shaped",
            "group": "music_discs",
            "pattern": pattern,
            "key": key,
            "result": result
        }

        # Write JSON file
        filename = f"{disc_id}.json"
        filepath = os.path.join(output_path, filename)
        with open(filepath, "w") as f:
            json.dump(recipe, f, indent=2)
        count += 1

    recipe_counts[pack] = count

# === Summary Output === #
print("\n=== Music Disc Generation Summary ===")
for pack, cnt in recipe_counts.items():
    label = "Legacy" if pack == "legacy" else f"Overlay {pack}"
    print(f"  - {label:<12}: discs created = {cnt}")
