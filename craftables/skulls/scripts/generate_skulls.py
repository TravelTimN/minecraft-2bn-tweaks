import os
import json

# === Configuration === #
NAMESPACE = "skulls"

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
    # 83: [
    #     {"mob": "illusioner", "item": "sculk", "dye": "blue", "suffix": "head"}  # future-proof example of different pack numbers
    # ]
}


# === Helpers === #
def get_recipe_format(pack):
    if pack == "legacy":
        return "item"
    for fmt, rng in RECIPE_FORMATS.items():
        if isinstance(pack, int) and pack in rng:
            return fmt
    raise ValueError(f"Unknown format for pack: {pack}")


def get_output_path(pack):
    if pack == "legacy" or (isinstance(pack, int) and pack < 48):
        folder = "recipes"
    else:
        folder = "recipe"

    if pack == "legacy":
        base = "data"
    else:
        base = f"overlay_{pack}/data"
    return os.path.join("..", base, NAMESPACE, folder)


# === Determine all packs === #
all_packs = set(MOBS_BY_PACK.keys()) | set(SIMULATED_OVERLAYS.keys())
all_packs = sorted(all_packs, key=lambda x: (0 if x == "legacy" else int(x)))


# === Recipe Generation === #
recipe_counts = {}
for pack in all_packs:
    source_packs = SIMULATED_OVERLAYS.get(pack, [p for p in all_packs if p == "legacy" or (isinstance(p, int) and isinstance(pack, int) and p <= pack)])
    output_path = get_output_path(pack)
    os.makedirs(output_path, exist_ok=True)
    fmt = get_recipe_format(pack)
    count = 0

    for sp in source_packs:
        for mob_def in MOBS_BY_PACK.get(sp, []):
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
