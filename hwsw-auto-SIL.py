#!/usr/bin/env python3
import os
import subprocess
import yaml
from openpyxl import load_workbook

# --- CONFIGURATION ---
YAML_PATH = "images.yaml"
EXCEL_PATH = "HWSWList_04_25_2025-auto.xlsm" # TODO: Will need to update name of this file (can we do it automagically)
SHEET_NAME = "Software-SIL"

# Start writing from this row 8 (first 7 rows are HEADERS)
START_ROW = 8

# Columns to update
VERSION_COL_IDX = 5  # Column E (Version)
FULL_IMAGE_COL_IDX = 6  # Column F (Image Name)

# Run imagesync to extract images from cluster
# Replace {os.environ['HOME']}/.kube/config-prod-sil with location of cluster KUBECONFIG (default is .kube/config)
def run_imagesync():
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
        full_image_list.append(full_name)
        if ":" in full_name:
            raw_version = full_name.split(":")[-1]
            version = raw_version.split("-")[0]  # Truncate at first hyphen
            image_name = full_name.split("/")[-1].split(":")[0]
            image_versions[image_name] = version
    print(f"Extracted {len(full_image_list)} images.")
    return image_versions, full_image_list

# Update Software-SIL sheet of HWSWList spreadsheet with extracted image version to column E and image name to column F
def update_excel(image_versions, full_image_list):
    print(f"Updating Excel file: {EXCEL_PATH}")
    wb = load_workbook(EXCEL_PATH, keep_vba=True)
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

    wb.save(EXCEL_PATH)
    print(f"Update complete. {updated_count} rows written to columns E and F of '{SHEET_NAME}'.")


def main():
    run_imagesync()
    versions, image_list = extract_versions()
    update_excel(versions, image_list)

if __name__ == "__main__":
    main()
