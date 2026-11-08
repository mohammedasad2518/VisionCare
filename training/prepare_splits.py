import os
import shutil
import json
import hashlib
from pathlib import Path
from sklearn.model_selection import train_test_split

DATASET_DIR = Path(__file__).resolve().parent / "dataset"
SPLITS_DIR = Path(__file__).resolve().parent / "data_splits"

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

def prepare_splits():
    print("Preparing reproducible stratified splits (70% Train, 15% Val, 15% Test)...")
    
    # 1. Collect all images and filter duplicates
    file_records = []
    seen_hashes = {}
    duplicates_removed = 0

    for folder_name, standard_name in CATEGORY_MAPPING.items():
        folder_path = DATASET_DIR / folder_name
        for img_path in folder_path.glob("*.*"):
            try:
                with open(img_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                if file_hash in seen_hashes:
                    duplicates_removed += 1
                    continue
                seen_hashes[file_hash] = img_path
                file_records.append({
                    "path": img_path,
                    "category": standard_name,
                    "label": CLASS_INDICES[standard_name]
                })
            except Exception:
                pass

    print(f"Total unique images retained: {len(file_records)} (removed {duplicates_removed} exact duplicates)")

    paths = [r["path"] for r in file_records]
    categories = [r["category"] for r in file_records]

    # 2. Stratified 70% Train / 30% (Val + Test)
    train_paths, val_test_paths, train_cats, val_test_cats = train_test_split(
        paths, categories, test_size=0.30, stratify=categories, random_state=42
    )

    # 3. Stratified 15% Val / 15% Test
    val_paths, test_paths, val_cats, test_cats = train_test_split(
        val_test_paths, val_test_cats, test_size=0.50, stratify=val_test_cats, random_state=42
    )

    splits = {
        "train": (train_paths, train_cats),
        "val": (val_paths, val_cats),
        "test": (test_paths, test_cats)
    }

    # 4. Create directory structure and copy files
    if SPLITS_DIR.exists():
        shutil.rmtree(SPLITS_DIR)

    summary = {}
    for split_name, (split_paths, split_categories) in splits.items():
        split_summary = {}
        for p, cat in zip(split_paths, split_categories):
            dest_dir = SPLITS_DIR / split_name / cat
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest_dir / p.name)
            split_summary[cat] = split_summary.get(cat, 0) + 1
        
        split_summary["total"] = len(split_paths)
        summary[split_name] = split_summary

    summary_file = Path(__file__).resolve().parent / "splits_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n--- SPLIT SUMMARY ---")
    for s_name, s_data in summary.items():
        print(f"{s_name.upper()} (Total: {s_data['total']}):")
        for cat, cnt in s_data.items():
            if cat != "total":
                print(f"  - {cat}: {cnt}")
    print(f"\nSplits directory ready at: {SPLITS_DIR}")
    print(f"Summary written to: {summary_file}")

if __name__ == "__main__":
    prepare_splits()

