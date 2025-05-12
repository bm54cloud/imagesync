#!/usr/bin/env python3
# Script to update SIL sheet of HWSW list file
# Connect to VPN
# Script should be run from root of forked imagesync repo https://github.com/bm54cloud/imagesync
# Script should be run from a
# Update run_imagesync function to point to the kube config of the cluster you want to run against
# Run script in a python environment
# python3 -m venv ~/pyvmomi-env
# source ~/pyvmomi-env/bin/activate
# --input argument is required and should be the path of the most recent HWSWList file (ex: ./hwsw-auto-SIL.py --input HWSWList_05_02_2025-auto.xlsm")

import os
import subprocess
import yaml
from openpyxl import load_workbook
from datetime import datetime, timedelta
import argparse

# --- CONFIGURATION ---
YAML_PATH = "images.yaml"
SHEET_NAME = "Software-SIL"
START_ROW = 8 # Start writing from this row 8 (first 7 rows are HEADERS)
VERSION_COL_IDX = 5  # Update column E (Version)
FULL_IMAGE_COL_IDX = 6  # Update column F (Image Name)

# Prep images.yaml
def prepare_images_yaml(path):
    yaml_template = {
        "collection": [],
        "cosign_verifiers": [],
        "destination": {
            "registry": "127.0.0.1:5000"
        },
        "exclude": [],
        "images": [],
        "include": [],
        "source": {
            "insecure": False
        }
    }

    # Check if file exists and is non-empty
    if not os.path.exists(path) or os.stat(path).st_size == 0:
        print(f"Creating or replacing {path} with default content...")
        with open(path, "w") as f:
            yaml.dump(yaml_template, f)
    else:
        print(f"{path} already exists and is not empty.")

# Run imagesync to extract images from cluster
# Replace os.environ['HOME']}/.kube/config-prod-sil with location of cluster KUBECONFIG (default is .kube/config)
def run_imagesync():
    prepare_images_yaml(YAML_PATH)

    print("Running imagesync docker container...")
    cmd = [
        "docker", "run",
        "-v", f"{os.environ['HOME']}/.docker/:/home/python/.docker/",
        "-v", f"{os.environ['HOME']}/.kube/config-prod-sil:/home/python/.kube/config",
        "-v", f"{os.getcwd()}/{YAML_PATH}:/app/images.yaml",
        "--rm", "docker.io/chaospuppy/imagesync:v1.6.0",
        "-f", "/app/images.yaml", "tidy"
    ]
    subprocess.run(cmd, check=True)
    print("imagesync completed.")

# Extract image versions from image name
def extract_versions():
    print(f"Reading versions from {YAML_PATH}...")
    with open(YAML_PATH, "r") as f:
        data = yaml.safe_load(f)

    image_versions = {}
    full_image_list = []

    for image_entry in data.get("images", []):
        full_name = image_entry["name"]
        if "RELEASE" in full_name:
            print(f"Skipping image with RELEASE tag: {full_name}")
            continue
        full_image_list.append(full_name)
        if ":" in full_name:
            raw_version = full_name.split(":")[-1]
            version = raw_version.split("-")[0]  # Truncate at first hyphen
            image_name = full_name.split("/")[-1].split(":")[0]
            image_versions[image_name] = version
    print(f"Extracted {len(full_image_list)} images (excluding RELEASE entries).")
    return image_versions, full_image_list

# Get Friday's date for HWSWList file name
def get_friday_filename():
    today = datetime.today()
    days_until_friday = (4 - today.weekday()) % 7  # Monday=0, Sunday=6
    this_friday = today + timedelta(days=days_until_friday)
    formatted_date = this_friday.strftime("%m_%d_%Y")
    return f"HWSWList_{formatted_date}-auto.xlsm"

# Update Software-SIL sheet of HWSWList spreadsheet with extracted image version to column E and image name to column F
def update_excel(image_versions, full_image_list, input_path):
    print(f"Opening Excel file: {input_path}")
    wb = load_workbook(input_path, keep_vba=True)
    ws = wb[SHEET_NAME]

    updated_count = 0
    row = START_ROW

    for full_image in full_image_list:
        if ":" in full_image:
            raw_version = full_image.split(":")[-1]
            version = raw_version.split("-")[0]  # Truncate at first hyphen
        else:
            version = ""

        ws.cell(row=row, column=VERSION_COL_IDX, value=version)
        ws.cell(row=row, column=FULL_IMAGE_COL_IDX, value=full_image)

        updated_count += 1
        row += 1

    # Save as new file with Friday's date
    new_filename = get_friday_filename()
    wb.save(new_filename)
    print(f"Update complete. {updated_count} rows written to columns E and F of '{SHEET_NAME}'.")
    print(f"Workbook saved as: {new_filename}")

def main():
    parser = argparse.ArgumentParser(description="Update HWSW Excel sheet with image versions.")
    parser.add_argument("--input", required=True, help="Path to existing HWSW Excel file")
    args = parser.parse_args()

    run_imagesync()
    versions, image_list = extract_versions()
    update_excel(versions, image_list, args.input)


if __name__ == "__main__":
    main()

# TODO: Problems to solve
# 1. Script writes to specific columns but doesn't match Software Name to Image Name, so you can have situations where the Version is written in order, but becomes out of sync with Software Name
# 2. Gitlab Runner image doesn't have version in image name
# 3. Low fruit, but is there an option where after it writes all the new lines, it sorts them alphabetically via the Software Name column
