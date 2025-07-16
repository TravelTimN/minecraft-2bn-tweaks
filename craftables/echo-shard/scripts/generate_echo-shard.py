import os
import json

# === Configuration === #
NAMESPACE = "echo-shard"
RECIPE_NAME = "echo_shard"
OUTPUT_ITEM = "minecraft:echo_shard"
OUTPUT_COUNT = 1

# Pattern and ingredients (common across all versions)
PATTERN = [
    "SDS",
    "DAD",
    "SDS"
]

INGREDIENTS = {
    "A": "amethyst_shard",
    "D": "deepslate",
    "S": "sculk"
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


# === Recipe Generation === #
print("\n=== Echo Shard Generation Summary ===")
for pack in PACKS:
    fmt = get_recipe_format(pack)
    output_path = get_output_path(pack)
    os.makedirs(output_path, exist_ok=True)

    # Build the recipe object
    if fmt == "flat":
        # >= 1.21.2 (flat string keys and result.id)
        key = {k: f"minecraft:{v}" for k, v in INGREDIENTS.items()}
        result = {
            "id": OUTPUT_ITEM,
            "count": OUTPUT_COUNT
        }
    else:
        # <= 1.21.1 (dict ingredients)
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

    # Write recipe to file
    filename = f"{RECIPE_NAME}.json"
    filepath = os.path.join(output_path, filename)
    with open(filepath, "w") as f:
        json.dump(recipe, f, indent=2)

    label = "Legacy" if pack == "legacy" else f"Overlay {pack}"
    print(f"  - {label:<12}: echo_shard created")
