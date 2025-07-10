import pandas as pd
import os
import json

# === Configuration === #
CSV_PATH = "2BN-Tweaks_More-Blocks.csv"

# === Load CSV === #
df = pd.read_csv(CSV_PATH)

# === Helpers === #
DO_NOT_PLURALIZE = {
    "bark", "stairs", "bricks"
}


def pluralize(category):
    """Return plural form unless explicitly skipped."""
    return category if category in DO_NOT_PLURALIZE else f"{category}s"


RECIPE_FORMATS = {
    "item": range(0, 18),      # pack < 18
    "id": range(18, 57),       # pack 18–56
    "flat": range(57, 999),    # pack 57+
}

def get_recipe_format(pack):
    """Return recipe style: item, id, or flat."""
    if pack == "legacy":
        return "item"
    for fmt, rng in RECIPE_FORMATS.items():
        if isinstance(pack, int) and pack in rng:
            return fmt
    raise ValueError(f"Unknown recipe format for pack: {pack}")


def get_output_path(pack):
    """
    Return full directory path for a given pack.
    These are vanilla recipes, just overriding the quantity/count crafted, so they
    must go in the default "minecraft" vanilla folder, not a custom <namespace>.
    Also, no sub-category folders, just straight into the recipe(s) folder.
    """
    if pack == "legacy" or (isinstance(pack, int) and pack < 48):
        # 1.21.1 and below go into "recipes/" (plural)
        folder = "recipes"
    else:
        # 1.21.2+ go into "recipe/" (singular)
        folder = "recipe"

    if pack == "legacy":
        # Default top-level path for 1.20.0 - 1.20.1 goes to "data/"
        base = os.path.join("..", "data", "minecraft", folder)
    else:
        # Overlays are top-level as well, starting from 1.20.2 (pack 18+)
        base = os.path.join("..", f"overlay_{pack}", "data", "minecraft", folder)
    return base


# === Overlay Rules === #
"""
Some recipes require an overlay rebuild due to recipe format changes.
These are simulated overlays that don't exist in the CSV file.
"""
SIMULATED_OVERLAYS = {
    57: ["legacy", 48],  # simulated for Recipe#3 formatting
}

# Determine packs in CSV and convert digit strings to ints ("legacy" = 0)
all_csv_packs = sorted(
    [int(p) if str(p).isdigit() else p for p in df["pack"].unique()],
    key=lambda x: (0 if x == "legacy" else x)
)

# Determine all packs including simulated ones ("legacy" = 0)
all_packs = sorted(
    set(all_csv_packs) | set(SIMULATED_OVERLAYS.keys()),
    key=lambda x: (0 if x == "legacy" else x)
)

# === Recipe Generation === #
recipe_counts = {}

for pack in all_packs:
    # Determine which packs to pull recipes from.
    # Which recipe data is used as input for the current pack.
    if pack in SIMULATED_OVERLAYS:
        # Some overlays don't exist in the CSV but are built from other packs.
        # Eg: overlay_57 combines recipes from "legacy" and overlay_48.
        source_packs = SIMULATED_OVERLAYS[pack]
    elif pack == "legacy":
        # Legacy is self-contained. Only uses its own recipe data.
        source_packs = ["legacy"]
    else:
        # Include all previous numeric packs up to (and including) this one and legacy
        source_packs = [p for p in all_csv_packs if p != "legacy" and isinstance(p, int) and p <= pack]
        if "legacy" in all_csv_packs:
            source_packs.insert(0, "legacy")

    # Combine all recipe entries from the selected source packs into a single DataFrame.
    # Merge rows from the CSV that match each source pack ID.
    # Convert both the CSV "pack" values and source pack IDs to "strings" to ensure matching.
    # Result: `pack_df` contains all the recipes that this overlay should include.
    pack_df = pd.concat([
        df[df["pack"].astype(str) == str(src)] for src in source_packs
    ], ignore_index=True)

    # Prepare output directory (where to save the recipes)
    output_path = get_output_path(pack)
    os.makedirs(output_path, exist_ok=True)

    existing_filenames = set()
    count_recipes = 0

    # Loop over CSV rows
    for _, row in pack_df.iterrows():
        # Category
        category = row["category"].strip().lower()
        category_plural = pluralize(category)

        # Filename
        result_name = row["result"].strip().lower()
        filename = f"{result_name}.json"
        if filename in existing_filenames:
            # Avoid duplicate filenames, otherwise use "result_from_key.json"
            safe_key = row["key"].strip().replace('"', '').replace("'", "")
            filename = f"{result_name}_from_{safe_key}.json"
        existing_filenames.add(filename)

        # CSV pattern is tricky with the quotations.
        # Parse pattern JSON (strip outer quotes)
        raw_pattern = str(row["pattern"])
        clean_pattern = raw_pattern.strip().strip('"\'')
        pattern = json.loads(clean_pattern)

        # CSV key is tricky with the quotations.
        # Parse key JSON (strip outer quotes)
        raw_key = str(row["key"])
        clean_key = raw_key.strip().strip('"\'')
        key_def = json.loads(clean_key)

        # Build key mapping
        fmt = get_recipe_format(pack)
        key_mapping = {}
        for char, val in key_def.items():
            if isinstance(val, str):
                # Some recipes can use either|or ingredients
                options = val.split("|")
            elif isinstance(val, list):
                options = val
            else:
                raise ValueError(f"Unexpected key value type: {val}")

            if fmt in ("item", "id"):
                # How many times does the recipe item go into the recipe?
                objs = [{"item": f"minecraft:{opt}"} for opt in options]
                key_mapping[char] = objs if len(objs) > 1 else objs[0]
            else:
                # Flat ingredients, as of 1.21.2 (pack 57+)
                key_mapping[char] = [f"minecraft:{opt}" for opt in options]

        # Build result object
        count_val = int(row["count"])
        if fmt == "item":
            # Older syntax until 1.20.6 (pack 41) uses "item"
            result_obj = {"item": f"minecraft:{result_name}", "count": count_val}
        else:
            # Newer syntax from 1.21.0 (pack 48+) uses "id"
            result_obj = {"id": f"minecraft:{result_name}", "count": count_val}

        # Assemble the full recipe
        recipe = {
            "type": "minecraft:crafting_shaped",
            "group": category,
            "pattern": pattern,
            "key": key_mapping,
            "result": result_obj
        }

        # Write .json file to respective path directory
        filepath = os.path.join(output_path, filename)
        with open(filepath, "w") as f:
            json.dump(recipe, f, indent=2)

        count_recipes += 1

    recipe_counts[pack] = count_recipes


# === Summary === #
for pack, cnt in recipe_counts.items():
    # Printing results to terminal
    label = "Legacy" if pack == "legacy" else f"Overlay {pack}"
    print(f"  - {label:<12}: recipes generated = {cnt}")
