import os
import hashlib
from pathlib import Path
import json
from collections import Counter
from PIL import Image

DATASET_DIR = Path(__file__).resolve().parent / "dataset"

CATEGORY_MAPPING = {
    "cataract": "Cataract",
    "diabetic_retinopathy": "Diabetic Retinopathy",
    "glaucoma": "Glaucoma",
    "normal": "Normal"
}

CLASS_INDICES = {
    "Cataract": 0,
    "Diabetic Retinopathy": 1,
    "Glaucoma": 2,
    "Normal": 3
}

def audit():
    print(f"Auditing dataset at: {DATASET_DIR}")
    
    stats = {
        "categories": {},
        "total_images": 0,
        "valid_images": 0,
        "corrupted_images": 0,
        "formats": Counter(),
        "dimension_stats": {
            "min_width": 999999, "max_width": 0,
            "min_height": 999999, "max_height": 0,
            "dimensions_sample": []
        },
        "duplicates": []
    }

    seen_hashes = {}
    
    for folder_name, standard_name in CATEGORY_MAPPING.items():
        folder_path = DATASET_DIR / folder_name
        if not folder_path.exists():
            print(f"Warning: Folder {folder_name} not found!")
            continue

        images = list(folder_path.glob("*.*"))
        category_count = len(images)
        stats["categories"][standard_name] = {
            "folder": folder_name,
            "count": category_count,
            "valid": 0,
            "corrupted": 0
        }
        stats["total_images"] += category_count

        for img_path in images:
            # Check hash for duplicates
            try:
                with open(img_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                
                if file_hash in seen_hashes:
                    stats["duplicates"].append({
                        "original": str(seen_hashes[file_hash]),
                        "duplicate": str(img_path.relative_to(DATASET_DIR))
                    })
                else:
                    seen_hashes[file_hash] = img_path.relative_to(DATASET_DIR)
            except Exception as e:
                pass

            # Check Pillow readability and dimensions
            try:
                with Image.open(img_path) as img:
                    img.verify()
                
                # Reopen to get dimensions
                with Image.open(img_path) as img:
                    img.load()
                    w, h = img.size
                    fmt = img.format or "UNKNOWN"
                    stats["formats"][fmt] += 1
                    stats["valid_images"] += 1
                    stats["categories"][standard_name]["valid"] += 1

                    stats["dimension_stats"]["min_width"] = min(stats["dimension_stats"]["min_width"], w)
                    stats["dimension_stats"]["max_width"] = max(stats["dimension_stats"]["max_width"], w)
                    stats["dimension_stats"]["min_height"] = min(stats["dimension_stats"]["min_height"], h)
                    stats["dimension_stats"]["max_height"] = max(stats["dimension_stats"]["max_height"], h)
            except Exception as e:
                stats["corrupted_images"] += 1
                stats["categories"][standard_name]["corrupted"] += 1
                print(f"Corrupted image detected: {img_path} ({e})")

    stats["formats"] = dict(stats["formats"])
    stats["duplicate_count"] = len(stats["duplicates"])
    
    print("\n--- DATASET AUDIT SUMMARY ---")
    print(f"Total Images: {stats['total_images']}")
    print(f"Valid Images: {stats['valid_images']}")
    print(f"Corrupted Images: {stats['corrupted_images']}")
    print(f"Duplicates Detected: {stats['duplicate_count']}")
    print("\nCategory Distribution:")
    for cat, data in stats["categories"].items():
        print(f"  - {cat}: {data['valid']} valid images ({data['folder']})")
    print("\nImage Formats:", stats["formats"])
    print(f"Dimensions: Width range [{stats['dimension_stats']['min_width']}, {stats['dimension_stats']['max_width']}], "
          f"Height range [{stats['dimension_stats']['min_height']}, {stats['dimension_stats']['max_height']}]")

    output_file = Path(__file__).resolve().parent / "dataset_audit.json"
    with open(output_file, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"\nAudit saved to {output_file}")

if __name__ == "__main__":
    audit()

