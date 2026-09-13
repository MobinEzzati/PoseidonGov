import requests
import zipfile

URL = "https://registry.faa.gov/database/ReleasableAircraft.zip"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

print("Downloading FAA registry...")
resp = requests.get(URL, headers=headers, timeout=120)
resp.raise_for_status()

with open("ReleasableAircraft.zip", "wb") as f:
    f.write(resp.content)

with zipfile.ZipFile("ReleasableAircraft.zip") as z:
    z.extractall("faa_data")

print("Done! Files extracted to faa_data/")