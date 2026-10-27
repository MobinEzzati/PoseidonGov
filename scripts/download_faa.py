import requests
import zipfile
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
ZIP_PATH = RAW / "ReleasableAircraft.zip"
EXTRACT_DIR = RAW / "ReleasableAircraft"

URL = "https://registry.faa.gov/database/ReleasableAircraft.zip"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

print("Downloading FAA registry...")
resp = requests.get(URL, headers=headers, timeout=120)
resp.raise_for_status()

RAW.mkdir(parents=True, exist_ok=True)
with open(ZIP_PATH, "wb") as f:
    f.write(resp.content)

with zipfile.ZipFile(ZIP_PATH) as z:
    z.extractall(EXTRACT_DIR)

print(f"Done! Files extracted to {EXTRACT_DIR}")