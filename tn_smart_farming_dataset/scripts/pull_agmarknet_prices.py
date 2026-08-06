"""
Pull daily mandi (market) prices for Tamil Nadu from the real Agmarknet dataset
mirrored on data.gov.in (Ministry of Agriculture & Farmers Welfare, Directorate of
Marketing and Inspection).

Dataset:  "Variety-wise Daily Market Prices of Commodity"
Catalog page: https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi
Verified resource_id: 9ef84268-d588-465a-a308-a864a43d0070
  (cross-checked against multiple independent published integrations of this exact
  dataset — this is a real, stable ID, not a placeholder.)

SETUP (you have to do this part — Claude cannot register on your behalf):
  1. Go to https://data.gov.in, click Sign Up, verify your email.
  2. Go to "My Account" -> "API Key" and copy your key.
  3. Set it as an environment variable:  export DATA_GOV_IN_API_KEY="your-key-here"
     (or paste it directly into API_KEY below for a quick local test — don't commit it).

USAGE:
  pip install -r requirements.txt
  python pull_agmarknet_prices.py --state "Tamil Nadu" --limit 5000 --out ../datasets/market_prices.csv
"""

import argparse
import csv
import os
import sys
import time
import urllib.parse
import urllib.request
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
    # also try loading .env from root project directory if running from scripts/
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
except ImportError:
    pass

RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

# Commonly published column names for this resource (state, district, market,
# commodity, variety, grade, arrival_date, min/max/modal price). I could not make a
# live authenticated call myself to double-check these against the current schema
# (no API key), so the script prints the *actual* keys it gets back — run with
# --inspect first and adjust FIELDNAMES below if the API has renamed anything.
FIELDNAMES = [
    "state", "district", "market", "commodity", "variety", "grade",
    "arrival_date", "min_price", "max_price", "modal_price",
]


def fetch_page(api_key: str, state: str, offset: int, limit: int) -> dict:
    params = {
        "api-key": api_key,
        "format": "json",
        "offset": offset,
        "limit": limit,
        "filters[state]": state,
    }
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "tn-smart-farming-dataset/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="Tamil Nadu")
    ap.add_argument("--limit", type=int, default=1000, help="records per page (data.gov.in caps this, try 1000-5000)")
    ap.add_argument("--max-records", type=int, default=20000, help="stop after this many total records")
    ap.add_argument("--out", default="../datasets/market_prices.csv")
    ap.add_argument("--inspect", action="store_true",
                    help="fetch 1 record, print its raw keys, and exit (run this first)")
    args = ap.parse_args()

    api_key = os.environ.get("DATA_GOV_IN_API_KEY")
    if not api_key:
        sys.exit(
            "Missing API key. Set DATA_GOV_IN_API_KEY (see the setup notes at the top "
            "of this script) — register free at https://data.gov.in"
        )

    if args.inspect:
        payload = fetch_page(api_key, args.state, 0, 1)
        print(json.dumps(payload.get("records", []), indent=2))
        print("\nActual field names returned above ^ — update FIELDNAMES if these differ.")
        return

    offset = 0
    total_written = 0
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        while total_written < args.max_records:
            try:
                payload = fetch_page(api_key, args.state, offset, args.limit)
            except Exception as e:
                print(f"Request failed at offset {offset}: {e}", file=sys.stderr)
                break

            records = payload.get("records", [])
            if not records:
                break

            for r in records:
                writer.writerow({k: r.get(k, "") for k in FIELDNAMES})
            total_written += len(records)
            offset += args.limit
            print(f"Fetched {total_written} records so far...")
            time.sleep(0.5)  # be polite to the API

    print(f"Done. Wrote {total_written} records to {args.out}")


if __name__ == "__main__":
    main()
