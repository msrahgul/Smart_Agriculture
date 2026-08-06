"""
Pull weather / rainfall data for Tamil Nadu from India Meteorological Department's
public API.

Reference docs (real, current as of July 2026): https://api.imd.gov.in/public/api_reference.html
  - AWS/ARG station data, state-filtered:  /api/v1/aws_data?sid=25   (25 = TAMIL_NADU)
  - District-wise rainfall (actual vs normal vs % departure vs category):
        /api/v1/districtrainfall?id=<district_obj_id>
  - District-wise nowcast / current weather / 7-day city forecast also documented.

HONEST CAVEAT (tested live during dataset build, July 2026):
  A direct unauthenticated call to `https://api.imd.gov.in/api/v1/aws_data?sid=25`
  returned HTTP 401 Unauthorized, even though the public reference page does not
  document any key/token requirement. This likely means IMD gates real traffic
  behind a token or IP allow-list not published on that page. Treat the endpoints
  below as *documented but access-unconfirmed* — you'll likely need to contact IMD
  (details on the reference page) to get a working credential, or find the header
  their own front-end (mausam.imd.gov.in) sends when it calls these same endpoints
  from a browser (check the Network tab in devtools while browsing
  https://mausam.imd.gov.in/responsive/rainfallinformation.php).

USAGE (once you have working access):
  python pull_imd_weather_rainfall.py --district-id 164 --out ../datasets/rainfall.csv
"""

import argparse
import csv
import json
import sys
import urllib.request

BASE = "https://api.imd.gov.in/api/v1"

RAINFALL_FIELDS = [
    "District", "Date", "Daily Actual", "Daily Normal", "Daily Departure Per",
    "Daily Category", "Weekly Actual", "Weekly Normal", "Weekly Departure Per",
    "Weekly Category", "Cumulative Actual", "Cumulative Normal",
    "Cumulative Departure Per", "Cumulative Category", "Monthly Actual",
    "Monthly Normal", "Monthly Departure Per", "Monthly Category",
]


def fetch(url: str, api_token: str | None):
    headers = {"User-Agent": "tn-smart-farming-dataset/1.0"}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--district-id", required=True,
                     help="IMD district Obj_id (find via mausam.imd.gov.in district map — "
                          "these are IMD-internal numeric codes, not the same as census codes)")
    ap.add_argument("--api-token", default=None,
                     help="Bearer token, if/when IMD issues one for your use case")
    ap.add_argument("--out", default="../datasets/rainfall.csv")
    args = ap.parse_args()

    url = f"{BASE}/districtrainfall?id={args.district_id}"
    try:
        data = fetch(url, args.api_token)
    except Exception as e:
        sys.exit(
            f"Request failed: {e}\n"
            "This is the known-401 endpoint — see the caveat in this script's docstring. "
            "Confirm the auth mechanism with IMD before assuming the script is broken."
        )

    records = data if isinstance(data, list) else [data]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RAINFALL_FIELDS)
        writer.writeheader()
        for r in records:
            writer.writerow({k: r.get(k, "") for k in RAINFALL_FIELDS})

    print(f"Wrote {len(records)} record(s) to {args.out}")


if __name__ == "__main__":
    main()
