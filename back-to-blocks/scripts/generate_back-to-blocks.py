import pandas as pd
import os
import json

# === Load CSV === #

csv_path = "2BN-Tweaks_Back-to-Blocks.csv"
df = pd.read_csv(csv_path)


# === Helpers === #

DO_NOT_PLURALIZE = {
    "glass", "miscellaneous", "quartz", "redstone",
    "resin", "sand", "stairs", "tuff"
}


def pluralize(category):
    """Return plural form unless explicitly skipped."""
    if category in DO_NOT_PLURALIZE:
        return category
    if category == "shelf":
        return "shelves"
    return f"{category}s"


RECIPE_FORMATS = {
    "item": range(0, 18),    # pack < 18
    "id": range(18, 57),     # pack 18–56
    "flat": range(57, 999),  # pack 57+
}


def get_recipe_format(pack):
    """Return recipe style: item, id, or flat."""
    if pack == "legacy":
        return "item"
    for attr, rng in RECIPE_FORMATS.items():
        if isinstance(pack, int) and pack in rng:
            return attr
    raise ValueError(f"Unknown format for pack: {pack}")


def get_output_path(pack):
    """Return full directory path for a given pack."""
    # 1.21 changed `recipes/` -> `recipe/` (pack 48+)
    folder = "recipes" if pack == "legacy" or (isinstance(pack, int) and pack < 48) else "recipe"
    if pack == "legacy":
        return os.path.join("..", "data", "back_to_blocks", folder)
    return os.path.join("..", f"overlay_{pack}", "data", "back_to_blocks", folder)


# === Overlay Rules === #

# Manual inflection points where recipe syntax changes significantly
SIMULATED_OVERLAYS = {
    57: ["legacy", 48],  # recipe format overhaul
    # 88: ["legacy", "48, "61", "88"],  # TODO: example, not legit
}

# Determine packs in CSV and convert digit strings to integers
all_csv_packs = sorted([
    int(p) if str(p).isdigit() else p
    for p in df["pack"].unique()
], key=lambda x: (999 if x == "legacy" else x))  # legacy always first

# Determine all packs including simulated ones
all_packs = sorted(
    set(all_csv_packs + list(SIMULATED_OVERLAYS.keys())),
    key=lambda x: (999 if x == "legacy" else x)
)


# === Recipe Generator === #

recipe_counts = {}

for pack in all_packs:
    if pack in SIMULATED_OVERLAYS:
        source_packs = SIMULATED_OVERLAYS[pack]
    elif pack == "legacy":
        source_packs = ["legacy"]
    else:
        # Automatically include all lower packs, up-to and including current
        source_packs = [
            p for p in all_csv_packs
            if p != "legacy" and isinstance(p, int) and p <= pack
        ]
        if "legacy" in all_csv_packs:
            source_packs.insert(0, "legacy")

    # Combine data for all source packs for this overlay
    pack_df = pd.concat([
        df[df["pack"].astype(str) == str(source)] for source in source_packs
    ])

    # Create the folder for specified pack.
    output_path = get_output_path(pack)
    os.makedirs(output_path, exist_ok=True)

    # Avoid duplicates
    existing_filenames = {}
    recipe_count = 0

    for _, row in pack_df.iterrows():
        category = row["category"].strip().lower()
        category_plural = pluralize(category)
        ingredient = row["ingredient_material"].strip().lower()
        result = row["recipe_result"].strip().lower()
        quantity = int(row["quantity"])
        count = int(row["count"])

        # Create folders for unique categories
        category_path = os.path.join(output_path, category_plural)
        os.makedirs(category_path, exist_ok=True)

        if category_plural not in existing_filenames:
            existing_filenames[category_plural] = {}

        # Avoid duplicate recipe.json files
        base_filename = f"{result}.json"
        if base_filename in existing_filenames[category_plural]:
            filename = f"{result}_from_{ingredient}.json"
        else:
            filename = base_filename
            existing_filenames[category_plural][base_filename] = True

        # Which recipe syntax to use?
        recipe_format = get_recipe_format(pack)

        if recipe_format == "item":
            # 1.20.0 - 1.20.6
            ingredients = [
                {
                    "item": f"minecraft:{ingredient}"
                } for _ in range(quantity)
            ]
            results = {
                "count": count,
                "item": f"minecraft:{result}"
            }
        elif recipe_format == "id":
            # 1.21.0 - 1.21.1
            ingredients = [
                {
                    "item": f"minecraft:{ingredient}"
                } for _ in range(quantity)
            ]
            results = {
                "count": count,
                "id": f"minecraft:{result}"
            }
        else:  # flat ingredients
            # 1.21.2+
            ingredients = [
                f"minecraft:{ingredient}"
            ] * quantity
            results = {
                "count": count,
                "id": f"minecraft:{result}"
            }

        # Build the Recipe
        recipe = {
            "type": "minecraft:crafting_shapeless",
            "group": f"{category_plural}_to_blocks",
            "ingredients": ingredients,
            "result": results
        }

        # Create the .json recipe
        filepath = os.path.join(category_path, filename)
        with open(filepath, "w") as f:
            json.dump(recipe, f, indent=4)

        recipe_count += 1

    recipe_counts[pack] = recipe_count


# === Summary Output === #

for pack in all_packs:
    if pack not in recipe_counts:
        continue
    label = "Legacy" if pack == "legacy" else f"Overlay {pack}"
    print(f"  - {label:<12}: recipes generated = {recipe_counts[pack]}")
