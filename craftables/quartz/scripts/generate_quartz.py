import json
import os
import zipfile

# === Configuration ===
# 26.2 only -> pack_format 107.1 == [107, 1]
PACK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAMESPACE = "quartz"
RECIPE_NAME = "raw_quartz"          # recipe id -> quartz:raw_quartz
OUTPUT_ITEM = "minecraft:quartz"    # Nether Quartz (raw)
OUTPUT_COUNT = 8
PACK_DESCRIPTION = "§42§cB§6N§f-§eT§aw§be§9a§5k§ds §f> §eCraftables §f: §bQuartz"
PACK_FORMAT = [107, 1]              # 26.2

# 3x3 shaped pattern: N B N / B M B / N B N
PATTERN = [
    "NBN",
    "BMB",
    "NBN"
]
INGREDIENTS = {
    "N": "minecraft:netherrack",
    "B": "minecraft:basalt",
    "M": "minecraft:magma_block",
}

ZIP_NAME = "2BN-Tweaks_Craftable_Quartz.zip"

# Paths that should NOT be bundled inside the installable zip
SKIP_FOR_ZIP = {"scripts", "notes.txt"}


def write_pack_mcmeta():
    pack_mcmeta = {
        "pack": {
            "description": PACK_DESCRIPTION,
            "min_format": PACK_FORMAT,
            "max_format": PACK_FORMAT,
        }
    }
    path = os.path.join(PACK_DIR, "pack.mcmeta")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pack_mcmeta, f, indent=4)
    print("  - pack.mcmeta written")


def write_recipe():
    recipe = {
        "type": "minecraft:crafting_shaped",
        "group": RECIPE_NAME,
        "pattern": PATTERN,
        # flat-method ingredients (array of item ids) - pack 57+
        "key": {k: [item] for k, item in INGREDIENTS.items()},
        "result": {
            "id": OUTPUT_ITEM,
            "count": OUTPUT_COUNT,
        },
    }
    # 26.2 uses the singular "recipe" directory
    rel = os.path.join("data", NAMESPACE, "recipe", f"{RECIPE_NAME}.json")
    path = os.path.join(PACK_DIR, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(recipe, f, indent=4)
    print(f"  - {rel} written")


def build_zip():
    zip_path = os.path.join(PACK_DIR, ZIP_NAME)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PACK_DIR):
            # don't descend into skipped directories
            dirs[:] = [d for d in dirs if d not in SKIP_FOR_ZIP and not d.startswith("__")]
            for fname in files:
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, PACK_DIR)
                if rel in SKIP_FOR_ZIP or rel == ZIP_NAME:
                    continue
                zf.write(full, arcname=rel)
    print(f"  - {ZIP_NAME} built")


if __name__ == "__main__":
    print("\n=== Quartz Generation Summary ===")
    write_pack_mcmeta()
    write_recipe()
    build_zip()
    print()
