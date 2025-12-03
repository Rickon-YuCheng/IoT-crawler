import json
import sqlite3

import pandas as pd
import requests
import streamlit as st

URL = (
    "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"
    "?Authorization=CWA-6EB204DE-D527-40AA-9E85-8247C45C582E"
    "&downloadType=WEB"
    "&format=JSON"
)
DB_PATH = "sqlite data.db"


@st.cache_data(ttl=3600)
def fetch_temperature_table(url: str = URL) -> pd.DataFrame:
    """Fetch CWA forecast JSON and return a tidy temperature table."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CWA-Temp-Streamlit/1.0)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    locations = (
        data["cwaopendata"]["resources"]["resource"]["data"]
        ["agrWeatherForecasts"]["weatherForecasts"]["location"]
    )

    rows = []
    for loc in locations:
        loc_name = loc["locationName"]
        max_daily = loc["weatherElements"]["MaxT"]["daily"]
        min_daily = loc["weatherElements"]["MinT"]["daily"]

        for max_rec, min_rec in zip(max_daily, min_daily):
            date = max_rec.get("dataDate")
            try:
                max_t = float(max_rec.get("temperature"))
            except (TypeError, ValueError):
                max_t = None

            try:
                min_t = float(min_rec.get("temperature"))
            except (TypeError, ValueError):
                min_t = None

            rows.append(
                {
                    "location": loc_name,
                    "date": date,
                    "min_temp_C": min_t,
                    "max_temp_C": max_t,
                }
            )

    df = pd.DataFrame(rows)
    df = df.sort_values(["location", "date"]).reset_index(drop=True)
    return df


@st.cache_data(ttl=300)
def load_db_temperature(db_path: str = DB_PATH) -> pd.DataFrame:
    """Load temperature data from local SQLite DB; empty DataFrame if not available."""
    try:
        conn = sqlite3.connect(db_path)
    except Exception:
        return pd.DataFrame(columns=["location", "date", "min_temp_C", "max_temp_C"])

    try:
        df = pd.read_sql(
            """
            SELECT l.name AS location,
                   t.date AS date,
                   t.min_temp_c AS min_temp_C,
                   t.max_temp_c AS max_temp_C
            FROM temperatures t
            JOIN locations l ON t.location_id = l.id
            ORDER BY t.date, l.name;
            """,
            conn,
        )
    except Exception:
        df = pd.DataFrame(columns=["location", "date", "min_temp_C", "max_temp_C"])
    finally:
        conn.close()

    if not df.empty:
        df["date"] = df["date"].astype(str)
        df = df.sort_values(["location", "date"]).reset_index(drop=True)
    return df


def main():
    st.set_page_config(
        page_title="CWA Temperature Viewer",
        layout="wide",
    )
    st.markdown(
        """
        <style>
        body { background-color: #f5f8ff; }
        .page-title { font-size: 32px; font-weight: 800; margin-bottom: 4px; }
        .subtitle { color: #5b6b7a; margin-bottom: 18px; }
        .badge {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 6px 10px; border-radius: 999px;
            background: #e8f1ff; color: #1d5cd6; font-weight: 600; font-size: 12px;
            border: 1px solid #d8e6ff;
        }
        .card {
            padding: 16px; border-radius: 12px; background: white;
            border: 1px solid #ebf0f6; box-shadow: 0 4px 14px rgba(26, 47, 98, 0.06);
        }
        .card h3 { margin: 0; font-size: 14px; color: #5b6b7a; }
        .temp { font-size: 32px; font-weight: 800; color: #e65100; margin: 4px 0; }
        .range { color: #748499; font-size: 13px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="page-title">地面觀測溫度</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">資料來源：氣象署農業氣象預報（F-A0010-001）</div>',
        unsafe_allow_html=True,
    )

    # Prefer local DB data; fallback to live API if DB is empty
    df_db = load_db_temperature(DB_PATH)
    if not df_db.empty:
        df = df_db
        source_label = "SQLite 資料庫"
    else:
        try:
            df = fetch_temperature_table()
            source_label = "CWA API（即時下載）"
        except Exception as exc:  # pragma: no cover - streamlit UI
            st.error(f"Failed to fetch data: {exc}")
            return

    st.caption(f"資料來源：{source_label}")

    # Controls
    locations = sorted(df["location"].unique())
    dates = sorted(df["date"].unique())
    col1, col2, col3 = st.columns([1.2, 1, 1])
    with col1:
        location_options = ["全部地區"] + locations
        chosen_loc = st.selectbox("地區", location_options, index=0)
    with col2:
        chosen_date = st.selectbox("日期", dates, index=0)
    with col3:
        st.markdown('<div class="badge">未來一週預報</div>', unsafe_allow_html=True)

    filtered = df[df["date"] == chosen_date]
    if chosen_loc != "全部地區":
        filtered = filtered[filtered["location"] == chosen_loc]

    # Summary
    today_view = filtered
    if not today_view.empty:
        max_row = today_view.loc[today_view["max_temp_C"].idxmax()]
        min_row = today_view.loc[today_view["min_temp_C"].idxmin()]
        avg_max = today_view["max_temp_C"].mean()
        avg_min = today_view["min_temp_C"].mean()
    else:
        max_row = min_row = None
        avg_max = avg_min = None

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h3>最高溫地區</h3>", unsafe_allow_html=True)
        if max_row is not None:
            st.markdown(f'<div class="temp">{max_row["max_temp_C"]:.1f}°C</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="range">{max_row["location"]}</div>', unsafe_allow_html=True)
        else:
            st.write("—")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h3>最低溫地區</h3>", unsafe_allow_html=True)
        if min_row is not None:
            st.markdown(f'<div class="temp">{min_row["min_temp_C"]:.1f}°C</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="range">{min_row["location"]}</div>', unsafe_allow_html=True)
        else:
            st.write("—")
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h3>平均區間</h3>", unsafe_allow_html=True)
        if avg_max is not None:
            st.markdown(
                f'<div class="temp">{avg_min:.1f}°C ~ {avg_max:.1f}°C</div>',
                unsafe_allow_html=True,
            )
            st.markdown(f'<div class="range">{len(today_view)} 個地區</div>', unsafe_allow_html=True)
        else:
            st.write("—")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### 各地區溫度列表")
    st.dataframe(
        today_view,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### 互動式台灣地圖")
    render_map_component(df, active_date=chosen_date)


def render_map_component(df: pd.DataFrame, active_date: str):
    """Render an HTML+JS map with Tailwind + Chart.js inside Streamlit."""
    # Define map positions (percentage of container) for region bubbles.
    coords = {
        "北部地區": {"x": 55, "y": 15},
        "東北部地區": {"x": 70, "y": 20},
        "中部地區": {"x": 52, "y": 35},
        "東部地區": {"x": 68, "y": 40},
        "南部地區": {"x": 50, "y": 60},
        "東南部地區": {"x": 66, "y": 63},
    }

    # Group data by location
    grouped = {}
    for loc, sub in df.groupby("location"):
        grouped[loc] = [
            {"date": r["date"], "min": r["min_temp_C"], "max": r["max_temp_C"]}
            for _, r in sub.sort_values("date").iterrows()
        ]

    # Active date values for chips on the map
    active_temp = {}
    if active_date:
        for loc, sub in df[df["date"] == active_date].groupby("location"):
            row = sub.iloc[0]
            active_temp[loc] = {
                "min": row["min_temp_C"],
                "max": row["max_temp_C"],
            }

    markers = []
    for loc in grouped.keys():
        pos = coords.get(loc, {"x": 50, "y": 50})
        active = active_temp.get(loc, {})
        min_v = active.get("min")
        max_v = active.get("max")
        min_disp = f"{min_v:.1f}" if min_v is not None else "—"
        max_disp = f"{max_v:.1f}" if max_v is not None else "—"
        markers.append(
            f"""
            <button data-loc="{loc}" class="no-pan group absolute -translate-x-1/2 -translate-y-1/2"
              style="left:{pos['x']}%; top:{pos['y']}%; pointer-events:auto; z-index:20;"
              onclick="handleSelect('{loc}')">
              <div class="flex items-center gap-3 rounded-full bg-white/95 border border-slate-200 px-3 py-2 shadow-md hover:shadow-lg transition">
                <div class="w-3.5 h-3.5 rounded-full bg-orange-500 group-hover:bg-orange-600 shadow-sm ring-2 ring-orange-200"></div>
                <div class="flex flex-col text-left leading-tight">
                  <div class="text-sm font-semibold text-slate-800">{loc}</div>
                  <div class="text-xs text-slate-600">{min_disp}° / {max_disp}°</div>
                </div>
              </div>
            </button>
            """
        )

    html = f"""
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
      .leaflet-container {{
        width: 100%;
        height: 100%;
      }}
      .marker-dot {{
        width: 14px; height: 14px; border-radius: 999px;
        background: #f97316; border: 2px solid #fff;
        box-shadow: 0 0 0 3px rgba(249,115,22,0.25);
      }}
      .marker-dot.active {{
        background: #16a34a; box-shadow: 0 0 0 3px rgba(74,222,128,0.35);
      }}
    </style>
    <div class="w-full rounded-2xl border border-slate-200 bg-white shadow-lg p-4">
      <div class="flex flex-col md:flex-row gap-4">
        <div class="md:w-2/3 w-full h-[520px] rounded-xl overflow-hidden border border-slate-200" id="leaflet-wrapper" style="height:520px;">
          <div id="map" class="h-full w-full" style="height:100%; width:100%;"></div>
        </div>
        <div class="md:w-1/3 w-full flex flex-col gap-3">
          <div class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
            <div class="text-xs uppercase tracking-wide text-slate-500 font-semibold">選取地區</div>
            <div id="selected-loc" class="text-2xl font-bold text-slate-900">請點選地區</div>
            <div id="selected-range" class="text-sm text-slate-600 mt-1">—</div>
          </div>
          <div class="rounded-xl border border-slate-200 bg-white px-4 py-4 shadow-sm" style="height: 320px;">
            <div class="flex items-center justify-between mb-2">
              <div class="text-sm font-semibold text-slate-700">溫度時間序列</div>
              <div id="legend" class="text-xs text-slate-500">最高 / 最低</div>
            </div>
            <canvas id="tempChart" class="w-full h-full" style="height: calc(100% - 32px); width: 100%;"></canvas>
          </div>
        </div>
      </div>
    </div>
    <script>
      const dataByLoc = {json.dumps(grouped)};
      const coords = {json.dumps({
        "北部地區": [25.03, 121.56],
        "東北部地區": [24.75, 121.76],
        "中部地區": [24.14, 120.67],
        "東部地區": [23.99, 121.60],
        "南部地區": [22.63, 120.30],
        "東南部地區": [22.66, 121.49],
      })};
      const defaultLoc = Object.keys(dataByLoc)[0];
      const ctx = document.getElementById('tempChart').getContext('2d');
      let chart;

      const map = L.map('map', {{
        zoomSnap: 0.1,
        zoomControl: true,
      }}).setView([23.7, 121], 7.2);
      L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        maxZoom: 18,
        attribution: '&copy; OpenStreetMap contributors'
      }}).addTo(map);

      const dotIcon = (active=false) => L.divIcon({{
        className: active ? 'marker-dot active' : 'marker-dot',
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      }});

      const markers = {{}};
      Object.entries(coords).forEach(([loc, latlng]) => {{
        const m = L.marker(latlng, {{ icon: dotIcon(loc === defaultLoc) }}).addTo(map);
        m.on('click', () => handleSelect(loc));
        markers[loc] = m;
      }});

      function formatRange(arr) {{
        if (!arr || arr.length === 0) return "—";
        const mins = arr.map(d => d.min).filter(n => n !== null);
        const maxs = arr.map(d => d.max).filter(n => n !== null);
        const minV = Math.min(...mins);
        const maxV = Math.max(...maxs);
        return '最低 ' + minV.toFixed(1) + '°C / 最高 ' + maxV.toFixed(1) + '°C';
      }}

      function render(loc) {{
        const records = dataByLoc[loc] || [];
        document.getElementById('selected-loc').innerText = loc;
        document.getElementById('selected-range').innerText = formatRange(records);
        const labels = records.map(r => r.date);
        const maxData = records.map(r => r.max);
        const minData = records.map(r => r.min);

        if (chart) chart.destroy();
        chart = new Chart(ctx, {{
          type: 'line',
          data: {{
            labels,
            datasets: [
              {{
                label: '最高溫 (°C)',
                data: maxData,
                borderColor: '#f97316',
                backgroundColor: 'rgba(249,115,22,0.12)',
                tension: 0.35,
                borderWidth: 2,
                fill: true,
              }},
              {{
                label: '最低溫 (°C)',
                data: minData,
                borderColor: '#0ea5e9',
                backgroundColor: 'rgba(14,165,233,0.12)',
                tension: 0.35,
                borderWidth: 2,
                fill: true,
              }}
            ]
          }},
          options: {{
            animation: false,
            interaction: {{
              mode: 'nearest',
              intersect: true,
            }},
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
              legend: {{
                display: false
              }},
              tooltip: {{
                backgroundColor: '#0f172a',
                titleColor: '#fff',
                bodyColor: '#e2e8f0',
              }}
            }},
            scales: {{
              x: {{
                ticks: {{ color: '#475569' }},
                grid: {{ display: false }}
              }},
              y: {{
                ticks: {{ color: '#475569' }},
                grid: {{ color: 'rgba(148,163,184,0.2)' }}
              }}
            }}
          }}
        }});
      }}

      function markActive(loc) {{
        Object.entries(markers).forEach(([k, m]) => {{
          m.setIcon(dotIcon(k === loc));
        }});
      }}

      function handleSelect(loc) {{
        render(loc);
        markActive(loc);
      }}

      render(defaultLoc);
      markActive(defaultLoc);
    </script>
    """
    st.components.v1.html(html, height=760, scrolling=False)


if __name__ == "__main__":
    main()
