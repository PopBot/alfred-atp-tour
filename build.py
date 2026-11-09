#!/usr/bin/env python3
"""
build.py — Builds the 'ATP Tour.alfredworkflow' archive.
Ensures official ATP Tour icon and 64x64 country flags are downloaded and packages all workflow files into a zip.
"""
import os
import zipfile

WORKFLOW_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(WORKFLOW_DIR, "ATP Tour.alfredworkflow")


def ensure_assets():
    flags_dir = os.path.join(WORKFLOW_DIR, "flags")
    icon_file = os.path.join(WORKFLOW_DIR, "icon.png")
    if not os.path.exists(icon_file) or not os.path.exists(flags_dir) or len(os.listdir(flags_dir)) < 50:
        print("Syncing ATP Tour icon and country flags...")
        import download_assets
        download_assets.download_all_assets()


def build_workflow():
    ensure_assets()

    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    top_level_files = [
        "atp.py",
        "atp_rankings.py",
        "atp_schedule.py",
        "atp_tournament.py",
        "atp_player.py",
        "utils.py",
        "image_utils.py",
        "info.plist",
        "icon.png",
        "README.md",
        "LICENSE",
        "requirements.txt",
    ]

    with zipfile.ZipFile(OUTPUT_FILE, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in top_level_files:
            fpath = os.path.join(WORKFLOW_DIR, fname)
            if os.path.exists(fpath):
                zf.write(fpath, arcname=fname)
                print(f"  + Added {fname}")

        # Add flags/
        flags_dir = os.path.join(WORKFLOW_DIR, "flags")
        flag_count = 0
        for root, _, files in os.walk(flags_dir):
            for file in files:
                if file.startswith("."):
                    continue
                fpath = os.path.join(root, file)
                rel_path = os.path.relpath(fpath, WORKFLOW_DIR)
                zf.write(fpath, arcname=rel_path)
                flag_count += 1
        print(f"  + Added {flag_count} country flags from flags/")

        # Add bundled lib/
        lib_dir = os.path.join(WORKFLOW_DIR, "lib")
        lib_count = 0
        for root, _, files in os.walk(lib_dir):
            for file in files:
                if file.endswith(".pyc") or "__pycache__" in root:
                    continue
                fpath = os.path.join(root, file)
                rel_path = os.path.relpath(fpath, WORKFLOW_DIR)
                zf.write(fpath, arcname=rel_path)
                lib_count += 1
        print(f"  + Added {lib_count} bundled library files from lib/")

    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"\n🎉 Successfully created: {OUTPUT_FILE} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    build_workflow()
