import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

# All paths are relative to this script, so it can run from any directory.
PROJECT_DIR = Path(__file__).resolve().parent.parent
NAMESPACE = "custom_crafting"
RECIPE_NAME = "dead_bush"
BASE_PACK_FORMAT = 15  # Java 1.20.0 / 1.20.1
MAX_PACK_FORMAT = 121.0  # Preserve the decimal pack format for Java 26.3.
PACK_DESCRIPTION = "§42§cB§6N§f-§eT§aw§be§9a§5k§ds §f> §eCraftables §f: §bDead-Bush"
PATTERN = ["S S", " S ", " S "]  # Spaces are required empty slots.
INGREDIENTS = {"S": "minecraft:stick"}
OUTPUT_COUNT = 1
ARCHIVE_NAME = "2BN-Tweaks_Craftable_Dead-Bush.zip"


def build_recipe(pack):
    # Pack 48 changed result.item to result.id; pack 57 flattened ingredients.
    key = INGREDIENTS if pack == 57 else {
        symbol: {"item": item} for symbol, item in INGREDIENTS.items()
    }
    result_key = "item" if pack == "legacy" else "id"
    return {
        "type": "minecraft:crafting_shaped",
        "category": "building",
        "pattern": PATTERN,
        "key": key,
        "result": {result_key: f"minecraft:{RECIPE_NAME}", "count": OUTPUT_COUNT}
    }


def main():
    metadata = {
        "pack": {
            "description": PACK_DESCRIPTION,
            "pack_format": BASE_PACK_FORMAT,
            "min_format": BASE_PACK_FORMAT,
            "max_format": MAX_PACK_FORMAT,
            "supported_formats": [BASE_PACK_FORMAT, MAX_PACK_FORMAT]
        },
        "overlays": {
            "entries": [
                {"directory": "overlay_48", "min_format": 48,
                 "max_format": 56, "formats": [48, 56]},
                {"directory": "overlay_57", "min_format": 57,
                 "max_format": 2147483647, "formats": [57, 2147483647]}
            ]
        }
    }

    # Relocate the original 26.3-only recipe into the modern overlay.
    original_path = PROJECT_DIR / "data" / NAMESPACE / "recipe" / f"{RECIPE_NAME}.json"
    modern_path = PROJECT_DIR / "overlay_57" / "data" / NAMESPACE / "recipe" / original_path.name
    if original_path.exists():
        modern_path.parent.mkdir(parents=True, exist_ok=True)
        original_path.replace(modern_path)

    for pack in ("legacy", 48, 57):
        if pack == "legacy":
            recipe_dir = PROJECT_DIR / "data" / NAMESPACE / "recipes"
        else:
            recipe_dir = PROJECT_DIR / f"overlay_{pack}" / "data" / NAMESPACE / "recipe"
        recipe_dir.mkdir(parents=True, exist_ok=True)
        (recipe_dir / f"{RECIPE_NAME}.json").write_text(
            json.dumps(build_recipe(pack), indent=2) + "\n", encoding="utf-8"
        )
    (PROJECT_DIR / "pack.mcmeta").write_text(
        json.dumps(metadata, indent=4, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # Ship only metadata, the pack icon, and recipes; exclude screenshots and sources.
    payload = [PROJECT_DIR / "pack.mcmeta", PROJECT_DIR / "pack.png"]
    for directory in ("data", "overlay_48", "overlay_57"):
        payload.extend(sorted((PROJECT_DIR / directory).rglob("*.json")))
    with ZipFile(PROJECT_DIR / ARCHIVE_NAME, "w", compression=ZIP_DEFLATED) as archive:
        for path in payload:
            archive.write(path, path.relative_to(PROJECT_DIR).as_posix())
    print(f"Created {NAMESPACE}:{RECIPE_NAME} and {ARCHIVE_NAME} (Java 1.20.0 - 26.3+).")


if __name__ == "__main__":
    main()
