import os
import json
import re

# === Configuration === #
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

NAMESPACE = "skulls"
PACK_DESCRIPTION = "§42§cB§6N§f-§eT§aw§be§9a§5k§ds §f> §eCraftables §f: §bSkulls"
BASE_PACK_FORMAT = 15
MAX_PACK_FORMAT = 121.0
DECIMAL_PACK_FORMAT_START = 82

SIMULATED_OVERLAYS = {
    48: ["legacy"],           # result.item -> result.id
    57: ["legacy", 48],       # flat keys
}

RECIPE_FORMATS = {
    "item": range(0, 48),       # pack < 48
    "id": range(48, 57),        # pack 48–56
    "flat": range(57, 999),     # pack 57+
}

# === Mob heads per version === #
MOBS_BY_PACK = {
    "legacy": [
        {"mob": "creeper", "item": "gunpowder", "dye": "lime", "suffix": "head"},
        {"mob": "dragon", "item": "dragon_breath", "dye": "black", "suffix": "head"},
        {"mob": "piglin", "item": "gold_ingot", "dye": "pink", "suffix": "head"},
        {"mob": "skeleton", "item": "bone", "dye": "light_gray", "suffix": "skull"},
        {"mob": "zombie", "item": "rotten_flesh", "dye": "green", "suffix": "head"},
    ]#,
    # 83.0: [
    #     {"mob": "illusioner", "item": "sculk", "dye": "blue", "suffix": "head"}  # decimal pack example -> overlay_83_0
    # ],
    # 107.0: [
    #     {"mob": "illusioner", "item": "sculk", "dye": "blue", "suffix": "head"}  # another decimal pack example -> overlay_107_0
    # ]
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


# === Determine all packs === #
mobs_by_pack = {
    normalize_pack(pack): mobs
    for pack, mobs in MOBS_BY_PACK.items()
}
simulated_overlays = {
    normalize_pack(pack): [normalize_pack(source) for source in sources]
    for pack, sources in SIMULATED_OVERLAYS.items()
}
all_packs = sorted(set(mobs_by_pack.keys()) | set(simulated_overlays.keys()), key=pack_sort_key)


# === Recipe Generation === #
recipe_counts = {}
for pack in all_packs:
    source_packs = simulated_overlays.get(pack, [
        p for p in all_packs
        if p == "legacy" or (
            isinstance(p, (int, float))
            and isinstance(pack, (int, float))
            and p <= pack
        )
    ])
    output_path = get_output_path(pack)
    os.makedirs(output_path, exist_ok=True)
    fmt = get_recipe_format(pack)
    count = 0

    for sp in source_packs:
        for mob_def in mobs_by_pack.get(sp, []):
            mob = mob_def["mob"]
            item = mob_def["item"]
            dye = mob_def["dye"]
            suffix = mob_def["suffix"]
            name = f"{mob}_{suffix}"

            # === Build recipe JSON === #
            if fmt == "flat":
                key_obj = {
                    "S": "minecraft:wither_skeleton_skull",
                    "I": f"minecraft:{item}",
                    "D": f"minecraft:{dye}_dye"
                }
            else:
                key_obj = {
                    "S": {"item": "minecraft:wither_skeleton_skull"},
                    "I": {"item": f"minecraft:{item}"},
                    "D": {"item": f"minecraft:{dye}_dye"}
                }

            if fmt != "item":
                result_key = "id"
            else:
                result_key = "item"
            result_obj = {result_key: f"minecraft:{name}", "count": 1}

            recipe = {
                "type": "minecraft:crafting_shaped",
                "group": "heads",
                "pattern": ["IDI", "DSD", "IDI"],
                "key": key_obj,
                "result": result_obj
            }

            filename = f"{name}.json"
            filepath = os.path.join(output_path, filename)
            with open(filepath, "w") as f:
                json.dump(recipe, f, indent=2)
            count += 1

    recipe_counts[pack] = count


# === Summary Output === #
print("\n=== Craftable Skulls Generation Summary ===")
for pack, cnt in recipe_counts.items():
    label = "Legacy" if pack == "legacy" else f"Overlay {pack}"
    print(f"  - {label:<12}: skulls generated = {cnt}")


# Generate pack.mcmeta with current overlay ranges.
write_pack_mcmeta(all_packs)
