import json
import requests

url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"


def pull_data_usaspending(max_pages=5):
    all_results = []
    page = 1

    while page <= max_pages:               # safety cap
        mypayload = {
            "subawards": False,
            "filters": {
                "award_type_codes": ["A", "B", "C", "D"],
                "naics_codes": ["481111"],
                "time_period": [{"start_date": "2023-01-01", "end_date": "2025-12-31"}],
            },
            "fields": [
                 "Award ID", "Recipient Name", "Award Amount",
                 "Awarding Agency", "Awarding Sub Agency",
                 "End Date",
            ],
            "limit": 100,                  # 100 per page (the max), not 10
            "page": page,                  # <-- this changes each loop
            "sort": "Award Amount",
            "order": "desc",
        }

        resp = requests.post(url, json=mypayload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        all_results.extend(data["results"])     # add this page's awards to the pile
        print(f"Page {page}: got {len(data['results'])} awards (total so far: {len(all_results)})")

        if not data["page_metadata"]["hasNext"]:   # API says no more pages
            break
        page += 1

    with open("awards_raw.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\nDone. Saved {len(all_results)} awards to awards_raw.json")

pull_data_usaspending()
