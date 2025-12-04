Adapted from Yen-Lung Lai's AI-Demo project:

[https://github.com/yenlung/AI-Demo/blob/master/【Demo04】用AISuite打造員瑛式思考生成器](https://github.com/yenlung/AI-Demo/blob/master/%E3%80%90Demo04b%E3%80%91%E5%93%A1%E7%91%9B%E5%BC%8F%E6%80%9D%E8%80%83%E7%94%9F%E6%88%90%E5%99%A8_Two_Stage_CoT_%E7%89%88.ipynb)


# IoT Crawler (CWA Temperature Viewer)

Streamlit app that fetches Taiwan CWA agricultural weekly forecasts (F-A0010-001), stores/reads temperatures from SQLite, and shows an interactive Leaflet map + time-series chart per region.

Live demo: https://iot-crawler-mhhrvab8s54ubdkv7ur562.streamlit.app/

## Features
- Fetch CWA forecast JSON (or reuse local SQLite if available).
- Leaflet map with clickable regional markers; charts update per region.
- Time-series for min/max temperatures, plus quick stats cards.
- CSV/JSON artifacts included for reference.

## Requirements
- Python 3.10+ (tested on 3.12)
- Packages in `requirements.txt`:
  - streamlit
  - pandas
  - requests

## Setup
```bash
# clone
git clone https://github.com/Rickon-YuCheng/IoT-crawler.git
cd IoT-crawler

# install deps (user scope)
python3 -m pip install --user -r requirements.txt
```

## Run
```bash
streamlit run streamlit_app.py
```

The app will fetch data from CWA; if `sqlite data.db` exists with `temperatures/locations` tables, it uses that data first. Map tiles load from OpenStreetMap CDN (requires internet).

## Files
- `streamlit_app.py` — main UI (Leaflet map + Chart.js).
- `crawler.py` / `crawler2.py` — data fetching/CSV pipeline.
- `dblite3.py` — SQLite ingest/preview.
- `cwa_F-A0010-001_*.json`, `cwa_temperature_table.csv`, `sqlite data.db` — sample artifacts.

## Notes
- If running in a sandboxed or offline environment, Leaflet/Chart.js CDNs may be blocked; switch to a networked environment or vendor local assets.
- For production, set a stronger `User-Agent` and rotate the CWA API key if rate-limited.
