import requests
import json
from datetime import datetime

URL = (
    "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"
    "?Authorization=CWA-6EB204DE-D527-40AA-9E85-8247C45C582E"
    "&downloadType=WEB"
    "&format=JSON"
)

def fetch_cwa_data(url: str = URL) -> dict:
    """Fetch JSON from CWA OpenData API and return as Python dict."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CWA-Data-Crawler/1.0)"
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()  # Raise error if status != 200
    return resp.json()

def save_json(data: dict, filename: str | None = None) -> str:
    """Save JSON data to a file and return the filename."""
    if filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cwa_F-A0010-001_{ts}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filename

if __name__ == "__main__":
    try:
        data = fetch_cwa_data()
        out_file = save_json(data)
        print(f"Downloaded and saved to: {out_file}")

        # If you just want to see part of the data:
        # print(json.dumps(data, ensure_ascii=False, indent=2))

    except requests.HTTPError as e:
        print(f"HTTP error: {e}")
    except requests.RequestException as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
