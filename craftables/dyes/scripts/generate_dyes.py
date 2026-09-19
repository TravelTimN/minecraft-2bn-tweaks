import os
import json
import re

# === Configuration === #
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

NAMESPACE = "dyes"
PACK_DESCRIPTION = "§42§cB§6N§f-§eT§aw§be§9a§5k§ds §f> §eCraftables §f: §bDyes"
BASE_PACK_FORMAT = 15
MAX_PACK_FORMAT = 121.0
DECIMAL_PACK_FORMAT_START = 82

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
        # 88: ["copper_nugget"]  # sample only, will not be used
    },
    "green": {
        "legacy": ["kelp"]
    },
    "light_blue": {
        "legacy": ["prismarine_crystals"]
    },
    "cyan": {
        "legacy": ["prismarine_shard"]
    },
    "blue": {
        "legacy": ["sculk_vein"]
    },
    "purple": {
        "legacy": ["amethyst_shard", "chorus_fruit"]
    },
    "black": {
        "legacy": ["coal", "charcoal"]
    },
    "light_gray": {
        "legacy": ["clay_ball"]
    }
}


# === Helpers === #
def normalize_pack(pack):
    if pack == "legacy":
        return "legacy"
    number = float(str(pack).strip())
    if number >= DECIMAL_PACK_FORMAT_START:
        return number
    if number.is_integer():
        return int(number)
    return number


def get_recipe_format(pack):
    if pack == "legacy":
        return "item"
    for fmt, rng in RECIPE_FORMATS.items():
        if isinstance(pack, (int, float)) and pack in rng:
            return fmt
    if isinstance(pack, (int, float)) and pack >= 57:
        return "flat"
    raise ValueError(f"Unknown format for pack: {pack}")


def pack_folder_name(pack):
    if isinstance(pack, float):
        return str(pack).replace(".", "_")
    return str(pack)


def get_output_path(pack):
    if pack == "legacy" or (isinstance(pack, (int, float)) and pack < 48):
        # 1.21.1 and below go into "recipes/" (plural)
        folder = "recipes"
    else:
        # 1.21.0+ go into "recipe/" (singular)
        folder = "recipe"

    if pack == "legacy":
        # Default top-level path for 1.20.0 - 1.20.1 goes to "data/"
        base = "data"
    else:
        # Overlays are top-level as well, starting from 1.20.2 (pack 18+)
        base = os.path.join(f"overlay_{pack_folder_name(pack)}", "data")
    return os.path.join(PROJECT_DIR, base, NAMESPACE, folder)


def pack_sort_key(pack):
    if pack == "legacy":
        return (0, 0)
    if isinstance(pack, (int, float)):
        return (1, pack)
    return (2, str(pack))


def max_format_before(pack):
    """Return the inclusive max format before the next overlay starts."""
    if isinstance(pack, float):
        major, minor = str(pack).split(".")
        if int(minor) > 0:
            return float(f"{major}.{int(minor) - 1}")
        return float(int(major) - 1)
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

    text = json.dumps(pack_mcmeta, indent=4, ensure_ascii=False)
    text = re.sub(
        r"\[\n\s+(-?\d+(?:\.\d+)?),\n\s+(-?\d+(?:\.\d+)?)\n\s+\]",
        r"[\1, \2]",
        text
    )

    with open(os.path.join(PROJECT_DIR, "pack.mcmeta"), "w", encoding="utf-8") as f:
        f.write(text)
        f.write("\n")


# === Determine all packs === #
all_packs = set()
for versions in DYES_BY_PACK.values():
    all_packs.update(normalize_pack(version) for version in versions.keys())
all_packs.update(SIMULATED_OVERLAYS.keys())
all_packs = sorted(all_packs, key=pack_sort_key)


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
            version_pack = normalize_pack(version)

            if (
                (pack == "legacy" and version_pack == "legacy")
                or (
                    isinstance(pack, (int, float))
                    and (
                        version_pack == "legacy"
                        or (isinstance(version_pack, (int, float)) and version_pack <= pack)
                    )
                )
            ):
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


# Generate pack.mcmeta with current overlay ranges.
write_pack_mcmeta(all_packs)


# === Summary Output === #
print("\n=== Craftable Dyes Generation Summary ===")
for pack, cnt in recipe_counts.items():
    label = "Legacy" if pack == "legacy" else f"Overlay {pack}"
    print(f"  - {label:<14}: recipes created = {cnt}")
