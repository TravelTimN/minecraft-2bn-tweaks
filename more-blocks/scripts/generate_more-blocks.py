import json
import os
import pandas as pd
import re

# === pack.mcmeta config === #

PACK_DESCRIPTION = "§42§cB§6N§f-§eT§aw§be§9a§5k§ds §f> §eMore-Blocks"
BASE_PACK_FORMAT = 15
MAX_PACK_FORMAT = 107.1

# === Load CSV === #


def normalize_pack(pack):
    if pd.isna(pack):
        return None
    pack = str(pack).strip().lower()
    if pack == "legacy":
        return "legacy"
    try:
        number = float(pack)
    except ValueError:
        raise ValueError(f"Invalid pack value: {pack}")
    if number.is_integer():
        return int(number)
    return number


csv_url = "https://docs.google.com/spreadsheets/d/1t9lmXWqlyno15NTqfUDTYcuZuNVCAmxs4Pt4w9a5CPI/export?format=csv&gid=1434501916"
df = pd.read_csv(csv_url)

df["pack"] = df["pack"].apply(normalize_pack)
df = df.dropna(subset=["pack"])

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
    if isinstance(pack, (int, float)):
        for attr, rng in RECIPE_FORMATS.items():
            if pack in rng:
                return attr
        if pack >= 57:
            return "flat"
    raise ValueError(f"Unknown format for pack: {pack}")


def pack_folder_name(pack):
    if isinstance(pack, float) and not pack.is_integer():
        return str(pack).replace(".", "_")

    return str(int(pack)) if isinstance(pack, float) else str(pack)


def get_output_path(pack):
    """
    Return full directory path for a given pack.
    These are vanilla recipes, just overriding the quantity/count crafted, so they
    must go in the default "minecraft" vanilla folder, not a custom <namespace>.
    Also, no sub-category folders, just straight into the recipe(s) folder.
    """
    if pack == "legacy" or (isinstance(pack, (int, float)) and pack < 48):
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
        base = os.path.join("..", f"overlay_{pack_folder_name(pack)}", "data", "minecraft", folder)
    return base


# === Overlay Rules === #
"""
Some recipes require an overlay rebuild due to recipe format changes.
These are simulated overlays that don't exist in the CSV file.
"""
SIMULATED_OVERLAYS = {
    57: ["legacy", 48],  # simulated for Recipe#3 formatting
}


def pack_sort_key(pack):
    if pack == "legacy":
        return (0, 0)
    if isinstance(pack, (int, float)):
        return (1, pack)
    return (2, str(pack))


def max_format_before(pack):
    """Return the inclusive max format before the next overlay starts."""
    if isinstance(pack, float) and not pack.is_integer():
        return int(pack)
    return pack - 1


def build_overlay_entries(packs):
    overlay_packs = [
        pack for pack in packs
        if pack != "legacy" and isinstance(pack, (int, float)) and pack >= 48
    ]

    entries = []
    for index, pack in enumerate(overlay_packs):
        if index + 1 < len(overlay_packs):
            max_format = max_format_before(overlay_packs[index + 1])
        else:
            max_format = 2147483647

        entries.append({
            "directory": f"overlay_{pack_folder_name(pack)}",
            "min_format": pack,
            "max_format": max_format,
            "formats": [pack, max_format]
        })

    return entries


def write_pack_mcmeta(packs):
    pack_mcmeta = {
        "pack": {
            "description": PACK_DESCRIPTION,
            "pack_format": BASE_PACK_FORMAT,
            "min_format": BASE_PACK_FORMAT,
            "max_format": MAX_PACK_FORMAT,
            "supported_formats": [BASE_PACK_FORMAT, MAX_PACK_FORMAT]
        },
        "overlays": {
            "entries": build_overlay_entries(packs)
        }
    }

    filepath = os.path.join("..", "pack.mcmeta")
    text = json.dumps(pack_mcmeta, indent=4, ensure_ascii=False)
    text = re.sub(
        r"\[\n\s+(-?\d+(?:\.\d+)?),\n\s+(-?\d+(?:\.\d+)?)\n\s+\]",
        r"[\1, \2]",
        text
    )
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
        f.write("\n")


# Determine packs in CSV and convert digit strings to ints ("legacy" = 0)
all_csv_packs = sorted(df["pack"].unique(), key=pack_sort_key)

# Determine all packs including simulated ones ("legacy" = 0)
all_packs = sorted(
    set(all_csv_packs) | set(SIMULATED_OVERLAYS.keys()),
    key=pack_sort_key
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
        source_packs = [
            p for p in all_csv_packs
            if p != "legacy" and isinstance(p, (int, float)) and p <= pack
        ]
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


# generate the pack.mcmeta with overlays [where applicable]
write_pack_mcmeta(all_packs)


# === Summary === #
for pack, cnt in recipe_counts.items():
    # Printing results to terminal
    label = "Legacy" if pack == "legacy" else f"Overlay {pack}"
    print(f"  - {label:<14}: recipes generated = {cnt}")
