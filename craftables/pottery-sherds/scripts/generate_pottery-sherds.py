import os
import json
import re

# === Configuration === #
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

NAMESPACE = "pottery_sherds"
PACK_DESCRIPTION = "§42§cB§6N§f-§eT§aw§be§9a§5k§ds §f> §eCraftables §f: §bPottery-Sherds"
BASE_PACK_FORMAT = 15
MAX_PACK_FORMAT = 121.0
DECIMAL_PACK_FORMAT_START = 82

SIMULATED_OVERLAYS = {
    57: ["legacy", 48],    # key -> flat
}

RECIPE_FORMATS = {
    "item": range(0, 48),       # pack < 48
    "id": range(48, 57),        # pack 48–56
    "flat": range(57, 999),     # pack 57+
}

# === Sherd definitions (by version) === #
SHERDS_BY_PACK = {
    "legacy": [
        "angler", "archer", "arms_up", "blade", "brewer", "burn", "danger",
        "explorer", "friend", "heart", "heartbreak", "howl", "miner",
        "mourner", "plenty", "prize", "sheaf", "shelter", "skull", "snort"
    ],
    48: ["flow", "guster", "scrape"]
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
        return os.path.join(PROJECT_DIR, "data", NAMESPACE, folder)
    return os.path.join(PROJECT_DIR, f"overlay_{pack_folder_name(pack)}", "data", NAMESPACE, folder)


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


# === Pack resolution === #
sherds_by_pack = {
    normalize_pack(pack): sherds
    for pack, sherds in SHERDS_BY_PACK.items()
}
simulated_overlays = {
    normalize_pack(pack): [normalize_pack(source) for source in sources]
    for pack, sources in SIMULATED_OVERLAYS.items()
}
all_packs = sorted(set(sherds_by_pack.keys()) | set(simulated_overlays.keys()), key=pack_sort_key)


# === Recipe Generation === #
recipe_counts = {}
for pack in all_packs:

    if pack in simulated_overlays:
        # Only simulated recipes no introducing new sherds
        source_packs = simulated_overlays[pack]
    else:
        # New pack recipes should include all lower pack recipes + self
        source_packs = [
            p for p in all_packs
            if p == "legacy" or (
                isinstance(p, (int, float))
                and isinstance(pack, (int, float))
                and p <= pack
            )
        ]

    all_sherds = []
    for src in source_packs:
        all_sherds.extend(sherds_by_pack.get(src, []))

    output_path = get_output_path(pack)
    os.makedirs(output_path, exist_ok=True)
    count = 0

    fmt = get_recipe_format(pack)
    for sherd in sorted(set(all_sherds)):
        # Name of JSON file
        filename = f"{sherd}_pottery_sherd.json"
        filepath = os.path.join(output_path, filename)

        # Pattern
        pattern = ["BSB", "BTB", "BBB"]

        # Ingredients key
        if fmt == "flat":
            key = {
                "B": "minecraft:brick",
                "T": "minecraft:terracotta",
                "S": f"minecraft:{sherd}_pottery_sherd"
            }
        else:
            key = {
                "B": {"item": "minecraft:brick"},
                "T": {"item": "minecraft:terracotta"},
                "S": {"item": f"minecraft:{sherd}_pottery_sherd"}
            }

        # Result key definition
        if fmt in ("id", "flat"):
            result_key = "id"
        else:
            result_key = "item"

        result_obj = {
            result_key: f"minecraft:{sherd}_pottery_sherd",
            "count": 4
        }

        # Recipe compiled
        recipe = {
            "type": "minecraft:crafting_shaped",
            "group": "pottery_sherds",
            "pattern": pattern,
            "key": key,
            "result": result_obj
        }

        # Create Recipe JSON
        with open(filepath, "w") as f:
            json.dump(recipe, f, indent=2)
        count += 1

    recipe_counts[pack] = count


# === Summary Output === #
print("\n=== Pottery Sherd Generation Summary ===")
for pack, cnt in recipe_counts.items():
    label = "Legacy" if pack == "legacy" else f"Overlay {pack}"
    print(f"  - {label:<12}: sherds created = {cnt}")


# Generate pack.mcmeta with current overlay ranges.
write_pack_mcmeta(all_packs)
