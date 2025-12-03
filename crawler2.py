import requests
import pandas as pd

URL = (
    "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"
    "?Authorization=CWA-6EB204DE-D527-40AA-9E85-8247C45C582E"
    "&downloadType=WEB"
    "&format=JSON"
)

def fetch_cwa_json(url: str = URL) -> dict:
    """Fetch JSON from CWA agricultural weekly forecast API."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CWA-Temp-Crawler/1.0)"
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()

def extract_temperature_table(data: dict) -> pd.DataFrame:
    """
    Extract daily min/max temperatures per location and
    return as a pandas DataFrame.
    """
    # Path based on actual JSON structure:
    # cwaopendata -> resources -> resource -> data -> agrWeatherForecasts
    # -> weatherForecasts -> location[] :contentReference[oaicite:0]{index=0}
    locations = (
        data["cwaopendata"]["resources"]["resource"]["data"]
        ["agrWeatherForecasts"]["weatherForecasts"]["location"]
    )

    rows = []
    for loc in locations:
        loc_name = loc["locationName"]

        max_daily = loc["weatherElements"]["MaxT"]["daily"]
        min_daily = loc["weatherElements"]["MinT"]["daily"]

        # MaxT/MinT arrays are aligned by date
        for max_rec, min_rec in zip(max_daily, min_daily):
            date = max_rec["dataDate"]
            max_t = float(max_rec["temperature"])
            min_t = float(min_rec["temperature"])

            rows.append(
                {
                    "location": loc_name,
                    "date": date,
                    "min_temp_C": min_t,
                    "max_temp_C": max_t,
                }
            )

    df = pd.DataFrame(rows)
    return df

def main():
    data = fetch_cwa_json()
    df = extract_temperature_table(data)

    # Print table to console
    print(df)

    # Also save as CSV
    df.to_csv("cwa_temperature_table.csv", index=False)
    print("Saved temperature table to cwa_temperature_table.csv")

if __name__ == "__main__":
    main()
