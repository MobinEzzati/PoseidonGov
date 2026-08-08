import json

import requests
import os
from dotenv import load_dotenv

load_dotenv()


URL = "https://api.sam.gov/opportunities/v2/search"


def fetch_SamData():
    sam_api_key = os.environ.get("SAM_GOV_API", "NOT FOUND")

    # Guard: catch a missing key BEFORE calling the API
    if sam_api_key == "NOT FOUND":
        print("❌ Key not loaded — check your .env file and variable name")
        return


    params = {
        "api_key": sam_api_key,
        "postedFrom": "01/01/2025",
        "postedTo": "01/01/2026",
        "ncode": "481111",
        "limit": 100,
        }

    resp = requests.get(URL, params=params, timeout=60)
    if resp.status_code != 200:
        print("Error:", resp.text)
        return
    data = resp.json()
    opportunities = data.get("opportunitiesData", [])
    print(f"Got {len(opportunities)} opportunities\n")

    for opp in opportunities[:5]:

        print(f"- {opp.get('title', 'no title')}  ({opp.get('postedDate', '')})")

    with open("sam_raw.json", "w") as f:
        json.dump(opportunities, f, indent=2)


fetch_SamData()