import json
import os
import pandas as pd
import re

# === pack.mcmeta config === #

PACK_DESCRIPTION = "§42§cB§6N§f-§eT§aw§be§9a§5k§ds §f> §eBack-to-Blocks"
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


csv_url = "https://docs.google.com/spreadsheets/d/1t9lmXWqlyno15NTqfUDTYcuZuNVCAmxs4Pt4w9a5CPI/export?format=csv&gid=0"
df = pd.read_csv(csv_url)

df["pack"] = df["pack"].apply(normalize_pack)
df = df.dropna(subset=["pack"])


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
    """Return full directory path for a given pack."""
    # 1.21 changed `recipes/` -> `recipe/` (pack 48+)
    folder = "recipes" if pack == "legacy" or (isinstance(pack, (int, float)) and pack < 48) else "recipe"
    if pack == "legacy":
        return os.path.join("..", "data", "back_to_blocks", folder)
    return os.path.join("..", f"overlay_{pack_folder_name(pack)}", "data", "back_to_blocks", folder)


# === Overlay Rules === #

# Manual inflection points where recipe syntax changes significantly
SIMULATED_OVERLAYS = {
    57: ["legacy", 48],  # recipe format overhaul
    # 88: ["legacy", "48, "61", "88"],  # NOTE: example, not legit
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


# Determine packs in CSV and convert digit strings to integers
all_csv_packs = sorted(df["pack"].unique(), key=pack_sort_key)

# Determine all packs including simulated ones
all_packs = sorted(
    set(all_csv_packs + list(SIMULATED_OVERLAYS.keys())),
    key=pack_sort_key
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
            if p != "legacy" and isinstance(p, (int, float)) and p <= pack
        ]
        if "legacy" in all_csv_packs:
            source_packs.insert(0, "legacy")

    # Combine data for all source packs for this overlay
    pack_df = pd.concat([
        df[df["pack"] == source] for source in source_packs
    ])

    # Create the folder for specified pack.
    output_path = get_output_path(pack)
    os.makedirs(output_path, exist_ok=True)

    # Avoid duplicates
    existing_filenames = {}
    recipe_count = 0

    for _, row in pack_df.iterrows():
        category = str(row["category"]).strip().lower()
        category_plural = pluralize(category)
        ingredient = str(row["ingredient_material"]).strip().lower()
        result = str(row["recipe_result"]).strip().lower()
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


# generate the pack.mcmeta with overlays [where applicable]
write_pack_mcmeta(all_packs)


# === Summary Output === #

for pack in all_packs:
    if pack not in recipe_counts:
        continue
    label = "Legacy" if pack == "legacy" else f"Overlay {pack}"
    print(f"  - {label:<14}: recipes generated = {recipe_counts[pack]}")
