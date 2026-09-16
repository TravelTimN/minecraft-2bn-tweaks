import os
import json
import re

# === Configuration === #
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

NAMESPACE = "enchanted-golden-apple"
PACK_DESCRIPTION = "§42§cB§6N§f-§eT§aw§be§9a§5k§ds §f> §eCraftables §f: §bEnchanted-Golden-Apple"
BASE_PACK_FORMAT = 15
MAX_PACK_FORMAT = 121.0
DECIMAL_PACK_FORMAT_START = 82

RECIPE_NAME = "enchanted_golden_apple"
OUTPUT_ITEM = f"minecraft:{RECIPE_NAME}"
OUTPUT_COUNT = 1

# Common recipe pattern and ingredients
PATTERN = [
    "ATA",
    "TNT",
    "ATA"
]

INGREDIENTS = {
    "A": "golden_apple",
    "T": "totem_of_undying",
    "N": "netherite_ingot"
}

# Recipe formats by version range
RECIPE_FORMATS = {
    "item": range(0, 48),       # pack < 48
    "id": range(48, 57),        # pack 48–56
    "flat": range(57, 999),     # pack 57+
}

# Packs to generate
PACKS = ["legacy", 48, 57]


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
        folder = "recipes"
    else:
        folder = "recipe"

    if pack == "legacy":
        base = "data"
    else:
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


# === Recipe Generation === #
all_packs = sorted((normalize_pack(pack) for pack in PACKS), key=pack_sort_key)

print("\n=== Enchanted Golden Apple Generation Summary ===")
for pack in all_packs:
    fmt = get_recipe_format(pack)
    output_path = get_output_path(pack)
    os.makedirs(output_path, exist_ok=True)

    # Build the recipe object
    if fmt == "flat":
        key = {k: f"minecraft:{v}" for k, v in INGREDIENTS.items()}
        result = {
            "id": OUTPUT_ITEM,
            "count": OUTPUT_COUNT
        }
    else:
        key = {
            k: {"item": f"minecraft:{v}"}
            for k, v in INGREDIENTS.items()
        }
        if fmt == "id":
            result_key = "id"
        else:
            result_key = "item"
        result = {
            result_key: OUTPUT_ITEM,
            "count": OUTPUT_COUNT
        }

    recipe = {
        "type": "minecraft:crafting_shaped",
        "pattern": PATTERN,
        "key": key,
        "result": result
    }

    # Write to file
    filename = f"{RECIPE_NAME}.json"
    filepath = os.path.join(output_path, filename)
    with open(filepath, "w") as f:
        json.dump(recipe, f, indent=2)

    label = "Legacy" if pack == "legacy" else f"Overlay {pack}"
    print(f"  - {label:<12}: enchanted-golden-apple created")


# Generate pack.mcmeta with current overlay ranges.
write_pack_mcmeta(all_packs)
