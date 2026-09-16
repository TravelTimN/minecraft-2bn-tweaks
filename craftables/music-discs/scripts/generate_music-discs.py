import json
import os
import re
from disc_recipes import DISCS_BY_PACK

# === Configuration === #
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

NAMESPACE = "music-discs"
PACK_DESCRIPTION = "§42§cB§6N§f-§eT§aw§be§9a§5k§ds §f> §eCraftables §f: §bMusic-Discs"
BASE_PACK_FORMAT = 15
MAX_PACK_FORMAT = 121.0
DECIMAL_PACK_FORMAT_START = 82

RECIPE_FORMATS = {
    "item": range(0, 48),       # pack < 48
    "id": range(48, 57),        # pack 48-56
    "flat": range(57, 999),     # pack 57+
}

SIMULATED_OVERLAYS = {
    57: ["legacy", 48],
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


def get_source_packs(pack, all_packs, simulated_overlays):
    if pack in simulated_overlays:
        return simulated_overlays[pack]

    return [
        source_pack for source_pack in all_packs
        if source_pack == "legacy" or (
            isinstance(source_pack, (int, float))
            and isinstance(pack, (int, float))
            and source_pack <= pack
        )
    ]


def collect_recipes(source_packs, discs_by_pack):
    seen_discs = set()
    recipes = []
    for source_pack in source_packs:
        for disc_def in discs_by_pack.get(source_pack, []):
            disc_id = disc_def["disc"]
            if disc_id not in seen_discs:
                seen_discs.add(disc_id)
                recipes.append(disc_def)
    return recipes


def build_recipe(disc_def, fmt):
    disc_id = disc_def["disc"]
    result_count = disc_def.get("count", 1)

    if fmt == "flat":
        key = {
            letter: f"minecraft:{item}"
            for letter, item in disc_def["ingredients"].items()
        }
        result = {
            "id": f"minecraft:{disc_id}",
            "count": result_count
        }
    else:
        key = {
            letter: {"item": f"minecraft:{item}"}
            for letter, item in disc_def["ingredients"].items()
        }
        result_key = "id" if fmt == "id" else "item"
        result = {
            result_key: f"minecraft:{disc_id}",
            "count": result_count
        }

    return {
        "type": "minecraft:crafting_shaped",
        "group": "music_discs",
        "pattern": disc_def["pattern"],
        "key": key,
        "result": result
    }


# === Pack resolution === #
discs_by_pack = {
    normalize_pack(pack): discs
    for pack, discs in DISCS_BY_PACK.items()
}
simulated_overlays = {
    normalize_pack(pack): [normalize_pack(source) for source in sources]
    for pack, sources in SIMULATED_OVERLAYS.items()
}
all_packs = sorted(set(discs_by_pack.keys()) | set(simulated_overlays.keys()), key=pack_sort_key)


# === Recipe Generation === #
recipe_counts = {}
for pack in all_packs:
    fmt = get_recipe_format(pack)
    output_path = get_output_path(pack)
    os.makedirs(output_path, exist_ok=True)

    source_packs = get_source_packs(pack, all_packs, simulated_overlays)
    recipes = collect_recipes(source_packs, discs_by_pack)

    for disc_def in recipes:
        filepath = os.path.join(output_path, f"{disc_def['disc']}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(build_recipe(disc_def, fmt), f, indent=2)

    recipe_counts[pack] = len(recipes)


# Generate pack.mcmeta with current overlay ranges.
write_pack_mcmeta(all_packs)


# === Summary Output === #
print("\n=== Music Disc Generation Summary ===")
for pack, count in recipe_counts.items():
    label = "Legacy" if pack == "legacy" else f"Overlay {pack}"
    print(f"  - {label:<16}: discs created = {count}")
