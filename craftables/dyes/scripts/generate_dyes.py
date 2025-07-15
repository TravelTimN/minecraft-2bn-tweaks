import os
import json

# === Configuration === #
NAMESPACE = "dyes"

SIMULATED_OVERLAYS = {
    48: ["legacy"],             # result.item -> result.id
    57: ["legacy", 48],         # ingredient.key = flat
}

RECIPE_FORMATS = {
    "item": range(0, 48),       # pack < 48
    "id": range(48, 57),        # pack 48–56
    "flat": range(57, 999),     # pack 57+
}

# === Dye alternates (by version) === #
DYES_BY_PACK = {
    "orange": {
        61: ["resin_clump"],
        # 83: ["copper_nugget"]  # sample only, will not be used
    },
    "green": {
        "legacy": ["kelp"]
    },
    "purple": {
        "legacy": ["amethyst_shard", "chorus_fruit"]
    },
    "black": {
        "legacy": ["coal", "charcoal"]
    }
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
        # 1.21.1 and below go into "recipes/" (plural)
        folder = "recipes"
    else:
        # 1.21.2+ go into "recipe/" (singular)
        folder = "recipe"

    if pack == "legacy":
        # Default top-level path for 1.20.0 - 1.20.1 goes to "data/"
        base = "data"
    else:
        # Overlays are top-level as well, starting from 1.20.2 (pack 18+)
        base = f"overlay_{pack}/data"
    return os.path.join("..", base, NAMESPACE, folder)


# === Determine all packs === #
all_packs = set()
for versions in DYES_BY_PACK.values():
    all_packs.update(versions.keys())
all_packs.update(SIMULATED_OVERLAYS.keys())
all_packs = sorted(all_packs, key=lambda x: (0 if x == "legacy" else int(x)))


# === Recipe Generation === #
recipe_counts = {}
for pack in all_packs:
    if pack in SIMULATED_OVERLAYS:
        source_packs = SIMULATED_OVERLAYS[pack]
    else:
        # Include all lower or equal packs (plus legacy)
        source_packs = [p for p in all_packs if p == "legacy" or (isinstance(p, int) and isinstance(pack, int) and p <= pack)]

    output_path = get_output_path(pack)
    os.makedirs(output_path, exist_ok=True)
    fmt = get_recipe_format(pack)
    count = 0

    for color, versions in DYES_BY_PACK.items():
        # Determine if this dye has entries valid for this pack
        valid = False
        ingredients = []
        for version, items in versions.items():
            if version == "legacy":
                version_num = 0
            else:
                version_num = int(version)

            if (pack == "legacy" and version == "legacy") or (isinstance(pack, int) and version_num <= pack):
                ingredients.extend(items)
                valid = True

        if not valid:
            continue

        # Build recipe JSON
        if fmt == "flat":
            # flat >= 1.21.2 (57+)
            if len(ingredients) > 1:
                # Ingredient accepts either||or values
                ingredient_entries = [[f"minecraft:{item}" for item in ingredients]]
            else:
                # Ingredient is standalone item
                ingredient_entries = [f"minecraft:{ingredients[0]}"]
            result_obj = {"id": f"minecraft:{color}_dye", "count": 1}
        else:
            # not flat <= 1.21.1 (older)
            if len(ingredients) > 1:
                # Ingredient accepts either||or values
                ingredient_entries = [[{"item": f"minecraft:{item}"} for item in ingredients]]
            else:
                # Ingredient is standalone item
                ingredient_entries = [{"item": f"minecraft:{ingredients[0]}"}]

            if fmt == "id":
                key = "id"
            else:
                key = "item"
            result_obj = {key: f"minecraft:{color}_dye", "count": 1}

        recipe = {
            "type": "minecraft:crafting_shapeless",
            "group": "dyes",
            "ingredients": ingredient_entries,
            "result": result_obj
        }

        # Write to file
        filename = f"{color}_dye.json"
        filepath = os.path.join(output_path, filename)
        with open(filepath, "w") as f:
            json.dump(recipe, f, indent=2)
        count += 1

    recipe_counts[pack] = count


# === Summary Output === #
print("\n=== Craftable Dyes Generation Summary ===")
for pack, cnt in recipe_counts.items():
    label = "Legacy" if pack == "legacy" else f"Overlay {pack}"
    print(f"  - {label:<12}: recipes created = {cnt}")
