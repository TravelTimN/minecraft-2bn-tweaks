
import os
import json
import pandas as pd

# === Configuration === #
CSV_PATH = "2BN-Tweaks_Universal-Dyeing.csv"
NAMESPACE = "universal_dyeing"

# === Color & Dye Alternates (version-aware) === #
DYE_COLORS = [
    "red", "orange", "yellow", "lime", "green", "cyan", "light_blue", "blue",
    "magenta", "purple", "pink", "brown", "black", "gray", "light_gray", "white"
]

DYE_ALTERNATES = {
    "red": {
        "legacy": ["beetroot", "poppy", "red_tulip", "rose_bush", "red_dye"]
    },
    "orange": {
        "legacy": ["orange_tulip", "torchflower", "orange_dye"],
        61: ["open_eyeblossom", "resin_clump"]
    },
    "yellow": {
        "legacy": ["dandelion", "sunflower", "yellow_dye"]
    },
    "lime": {
        "legacy": ["sea_pickle", "lime_dye"]
    },
    "green": {
        "legacy": ["cactus", "green_dye", "kelp"]
    },
    "cyan": {
        "legacy": ["pitcher_plant", "cyan_dye"]
    },
    "light_blue": {
        "legacy": ["blue_orchid", "light_blue_dye"]
    },
    "blue": {
        "legacy": ["lapis_lazuli", "cornflower", "blue_dye"]
    },
    "magenta": {
        "legacy": ["allium", "lilac", "magenta_dye"]
    },
    "purple": {
        "legacy": ["amethyst_shard", "chorus_fruit", "purple_dye"]
    },
    "pink": {
        "legacy": ["peony", "pink_petals", "pink_tulip", "pink_dye"],
        71: ["cactus_flower"]
    },
    "brown": {
        "legacy": ["cocoa_beans", "brown_dye"]
    },
    "black": {
        "legacy": ["coal", "charcoal", "ink_sac", "wither_rose", "black_dye"]
    },
    "gray": {
        "legacy": ["gray_dye"],
        61: ["closed_eyeblossom"]
    },
    "light_gray": {
        "legacy": ["azure_bluet", "oxeye_daisy", "white_tulip", "light_gray_dye"]
    },
    "white": {
        "legacy": ["bone_meal", "lily_of_the_valley", "white_dye"]
    }
}

# === Helpers === #
RECIPE_FORMATS = {
    "item": range(0, 18),          # up to 1.20.2
    "id": range(18, 57),           # 1.20.2 - 1.21.3
    "flat": range(57, 999)         # 1.21.4+
}

SIMULATED_OVERLAYS = {
    48: ["legacy"],                # Recipe format switch: (item -> id)
    57: ["legacy", 48],            # Format switch: (id -> flat)
    61: ["legacy", 48, 57],        # Dye alt: closed_eyeblossom (gray), open_eyeblossom (orange), resin_clump (orange)
    71: ["legacy", 48, 57, 61],    # Dye alt: cactus_flower (pink)
}


def get_recipe_format(pack):
    """
    Return the recipe format type (`item`, `id`, or `flat`)
    based on the given pack number or `legacy`.
    """
    if pack == "legacy":
        return "item"
    for fmt, rng in RECIPE_FORMATS.items():
        if isinstance(pack, int) and pack in rng:
            return fmt
    raise ValueError(f"Unknown recipe format for pack: {pack}")


def get_output_path(pack):
    """
    Return full directory path for a given pack.
    """
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


# === Helpers === #
def get_tag_output_path(pack):
    """
    Return full directory path for a tag (item, dyes).
    - packs <= 1.20.x -> tags/items/
    - packs >= 1.21.0 -> tags/item/
    """
    is_legacy = (pack == "legacy")
    is_pre_48 = (isinstance(pack, int) and pack < 48)

    if is_legacy:
        base = "data"
    else:
        base = f"overlay_{pack}/data"

    # Before pack 48 -> "items" (plural) / after -> "item" (singular)
    if is_legacy or is_pre_48:
        tag_dir = "items"
    else:
        tag_dir = "item"

    return os.path.join("..", base, NAMESPACE, "tags", tag_dir)


def get_flat_ingredient(item_or_tag):
    """
    Return a valid flat JSON ingredient.
    If the input starts with `#`, return it as-is (tag reference).
    Otherwise, return a dictionary with `item` key.
    """
    if item_or_tag.startswith("#"):
        return item_or_tag
    else:
        return {"item": item_or_tag}


def get_dye_tag_values(color, pack):
    """
    Return a list of dye item values for a given color and pack version.
    Includes version-aware alternates, with support for legacy and overlay-specific additions.
    """
    sources = DYE_ALTERNATES.get(color, {})
    values = []
    for version_key, items in sources.items():
        if version_key == "legacy":
            version_num = 0
        else:
            version_num = int(version_key)

        if version_key == "legacy" or (isinstance(pack, int) and pack >= version_num):
            values.extend(items)

    return sorted(set(f"minecraft:{item}" for item in values))


def safe_tag_filename(name):
    """
    Minecraft tag identifiers use a namespace:path format ("minecraft:wool"),
    but colons are not allowed in filenames.
    Strip namespace and return only the actual path ("wool").
    """
    return name.split(":")[-1] if ":" in name else name


# === Load CSV and determine all packs === #
"""
Load the CSV recipe source file into a DataFrame.
Replace all `0` values in the `pack` column with the string `legacy` for consistency.
    all_csv_packs = every unique pack explicitly declared in the CSV, sorted with `legacy` always first.
    all_packs = the union of all CSV packs and any simulated overlays (48, 57, etc).
This ensures all recipe/tag content is generated for both real and simulated overlays.
"""
df = pd.read_csv(CSV_PATH)
df["pack"] = df["pack"].replace(0, "legacy")
all_csv_packs = sorted(set(df["pack"]), key=lambda x: 0 if x == "legacy" else int(x))
all_packs = sorted(set(all_csv_packs).union(SIMULATED_OVERLAYS.keys()), key=lambda x: 0 if x == "legacy" else int(x))


# === Tag Construction === #
"""
For each item category (`wool`, `glass`, etc), collect all recipe results where use_tag is TRUE.
These are used to generate universal tag files (e.g. wool.json, concrete.json, etc).
"""
tag_data = {}
df_filtered = df[df["use_tag"] == True]  # Only keep rows that use tags

for category in df_filtered["category"].unique():
    # Only include categories where use_tag is TRUE
    ingredient_items = df_filtered[df_filtered["category"] == category]["recipe_result"].tolist()
    values = sorted(set(f"minecraft:{item}" for item in ingredient_items))
    tag_data[safe_tag_filename(category)] = values


# === Recipe + Tag Generation === #
recipe_counts = {}
for pack in all_packs:
    if pack != "legacy":
        pack = int(pack)

    # Iterate through all packs, including both actual and simulated overlays (legacy, 48, 57, 61, 71, etc).
    output_path = get_output_path(pack)
    tag_path = get_tag_output_path(pack)
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(tag_path, exist_ok=True)

    # Includes all packs (real or simulated) that feed into the current pack's recipe/tag output.
    # Prevents missing data if a pack appears only in the overlay definitions.
    source_packs = SIMULATED_OVERLAYS.get(pack, [pack])
    if pack not in source_packs:
        source_packs += [pack]
    df_pack = pd.concat([df[df["pack"] == source] for source in source_packs])

    recipe_format = get_recipe_format(pack)
    use_id = recipe_format in ["id", "flat"]
    is_flat = recipe_format == "flat"

    recipe_count = 0
    dye_count = 0
    tag_count = 0

    # Iterate over every dyeable recipe defined for this pack.
    for _, row in df_pack.iterrows():
        # Clean and extract category, color, resulting item, and recipe output count.
        category = row["category"].strip()
        color = row["color"].strip()
        result_item = row["recipe_result"].strip()
        count = int(row["count"])

        # Ingredient: color/dye/ice
        if color == "ice":
            # ice
            if is_flat:
                # ice | flat >= 1.21.2 (57+)
                dye_entry = "minecraft:ice"
            else:
                # ice | not flat <= 1.21.1 (older)
                dye_entry = {"item": "minecraft:ice"}
        else:
            # standard color (not ice)
            tag_path_dye = f"{NAMESPACE}:dyes/{color}_dye"
            if is_flat:
                # color | flat >= 1.21.2 (57+)
                dye_entry = f"#{tag_path_dye}"
            else:
                # color | not flat <= 1.21.1 (older)
                dye_entry = {"tag": tag_path_dye}

        # Ingredient: block material/category
        use_tag = bool(row.get("use_tag", True))  # Default to True if column is missing

        if use_tag:
            # Uses a universal tag (wool, concrete, etc)
            tag_namespace_path = f"{NAMESPACE}:{category}"
            if is_flat:
                # flat >= 1.21.2 (57+)
                tag_entry = f"#{tag_namespace_path}"
            else:
                # not flat <= 1.21.1 (older)
                tag_entry = {"tag": tag_namespace_path}
        else:
            # No tag, use vanilla recipe item (sand, sandstone, etc)
            ingredient_name = category.strip()
            if is_flat:
                # flat >= 1.21.2 (57+)
                tag_entry = f"minecraft:{ingredient_name}"
            else:
                # not flat <= 1.21.1 (older)
                tag_entry = {"item": f"minecraft:{ingredient_name}"}

        key = {
            "#": tag_entry,
            "O": dye_entry
        }

        # Recipe .json formatting
        recipe = {
            "type": "minecraft:crafting_shaped",
            "group": f"universal_dyeing_{category}",
            "pattern": ["###", "#O#", "###"],
            "key": key,
            "result": {
                ("id" if use_id else "item"): f"minecraft:{result_item}",
                "count": count
            }
        }

        # Create the recipe file.
        with open(os.path.join(output_path, f"{result_item}.json"), "w") as f:
            json.dump(recipe, f, indent=2)
        recipe_count += 1

    # Generate tag files (red_dye.json etc), using version-aware alternates.
    dye_dir = os.path.join(tag_path, "dyes")
    os.makedirs(dye_dir, exist_ok=True)
    for dye in DYE_COLORS:
        values = get_dye_tag_values(dye, pack)
        tag_json = {"replace": False, "values": values}
        with open(os.path.join(dye_dir, f"{dye}_dye.json"), "w") as f:
            json.dump(tag_json, f, indent=2)
        dye_count += 1

    # Create tags (candle.json, glass.json, etc) referencing all applicable variants.
    for category, values in tag_data.items():
        if not values:
            continue  # Skip writing empty tag files
        tag_json = {"replace": False, "values": values}
        category_filename = safe_tag_filename(category)
        with open(os.path.join(tag_path, f"{category_filename}.json"), "w") as f:
            json.dump(tag_json, f, indent=2)
        tag_count += 1

    # For print summary tracking
    recipe_counts[pack] = f"recipes = {recipe_count} | tag items = {tag_count} | dye tags = {dye_count}"


# === Summary Output === #
print("\n=== Universal Dyeing Generation Summary ===")
for pack, count in recipe_counts.items():
    label = "Legacy" if pack == "legacy" else f"Overlay {pack}"
    print(f"  - {label:<12}: {count}")
