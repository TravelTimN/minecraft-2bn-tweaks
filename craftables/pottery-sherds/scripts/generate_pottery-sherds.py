import os
import json

# === Configuration === #
NAMESPACE = "pottery_sherds"

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
        return os.path.join("..", "data", NAMESPACE, folder)
    return os.path.join("..", f"overlay_{pack}", "data", NAMESPACE, folder)


# === Pack resolution === #
all_packs = sorted(set(SHERDS_BY_PACK.keys()) | set(SIMULATED_OVERLAYS.keys()), key=lambda x: (0 if x == "legacy" else int(x)))


# === Recipe Generation === #
recipe_counts = {}
for pack in all_packs:

    if pack in SIMULATED_OVERLAYS:
        # Only simulated recipes no introducing new sherds
        source_packs = SIMULATED_OVERLAYS[pack]
    else:
        # New pack recipes should include all lower pack recipes + self
        source_packs = [p for p in all_packs if p == "legacy" or (isinstance(p, int) and isinstance(pack, int) and p <= pack)]

    all_sherds = []
    for src in source_packs:
        all_sherds.extend(SHERDS_BY_PACK.get(src, []))

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
