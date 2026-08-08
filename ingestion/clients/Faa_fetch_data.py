import zipfile
import requests
import pandas as pd

URL = "https://registry.faa.gov/database/ReleasableAircraft.zip"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}



def download_faa():
    print("Downloading FAA registry (~60MB, give it a moment)...")
    resp = requests.get(URL, timeout=120,headers=headers)
    resp.raise_for_status()

    # "wb" = write BINARY — a zip is not text, so plain "w" would corrupt it
    with open("ReleasableAircraft.zip", "wb") as f:
        f.write(resp.content)

    with zipfile.ZipFile("ReleasableAircraft.zip") as z:
        print("\nFiles inside the zip:")
        for name in z.namelist():
            print(f"  {name}")
        z.extractall("faa_data")
    print("\nExtracted to faa_data/")


def explore_master():
    master = pd.read_csv("faa_data/MASTER.txt", dtype=str)
    master.columns = master.columns.str.strip()

    # Strip trailing spaces from the NAME values themselves (not just headers)
    master["NAME"] = master["NAME"].str.strip()

    print(f"Total registered aircraft: {len(master):,}\n")

    # Try the real legal name
    for term in ["FEDERAL EXPRESS", "UNITED AIR", "SOUTHWEST AIR", "DELTA AIR"]:
        hits = master[master["NAME"].str.contains(term, case=False, na=False)]
        print(f"{term:20} {len(hits):>6} aircraft")

    # Peek at the biggest fleet owners so you SEE the real name formats
    print("\nTop 15 registrants by fleet size:")
    print(master["NAME"].value_counts().head(15))


# download_faa()
explore_master()

