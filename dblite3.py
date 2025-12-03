import requests
import sqlite3

URL = (
    "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"
    "?Authorization=CWA-6EB204DE-D527-40AA-9E85-8247C45C582E"
    "&downloadType=WEB"
    "&format=JSON"
)

DB_PATH = "sqlite data.db"  # file name with space, SQLite is fine with this


# -------------- Step 1: Fetch JSON from CWA -------------- #

def fetch_cwa_json(url: str = URL) -> dict:
    """Fetch JSON from CWA agricultural weekly forecast API."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CWA-Temp-Crawler/1.0)"
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


# -------------- Step 2: Extract temperature records -------------- #

def extract_temperature_records(data: dict):
    """
    Extract daily min/max temperatures per location.

    Returns a list of tuples:
        (location_name, date, min_temp_c, max_temp_c)
    """
    # Adjust this path if CWA changes JSON structure
    locations = (
        data["cwaopendata"]["resources"]["resource"]["data"]
        ["agrWeatherForecasts"]["weatherForecasts"]["location"]
    )

    records = []

    for loc in locations:
        loc_name = loc["locationName"]

        max_daily = loc["weatherElements"]["MaxT"]["daily"]
        min_daily = loc["weatherElements"]["MinT"]["daily"]

        # Assuming MaxT/MinT arrays are aligned by date
        for max_rec, min_rec in zip(max_daily, min_daily):
            date = max_rec["dataDate"]
            try:
                max_t = float(max_rec["temperature"])
            except (KeyError, TypeError, ValueError):
                max_t = None

            try:
                min_t = float(min_rec["temperature"])
            except (KeyError, TypeError, ValueError):
                min_t = None

            records.append(
                (loc_name, date, min_t, max_t)
            )

    return records


# -------------- Step 3: Database initialization -------------- #

def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Create/open SQLite database and ensure tables exist."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create locations table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS locations (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL UNIQUE
        );
        """
    )

    # Create temperatures table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS temperatures (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id  INTEGER NOT NULL,
            date         TEXT NOT NULL,
            min_temp_c   REAL,
            max_temp_c   REAL,
            FOREIGN KEY (location_id) REFERENCES locations(id),
            UNIQUE (location_id, date)
        );
        """
    )

    conn.commit()
    return conn


# -------------- Step 4: Helper for inserting / upserting -------------- #

def get_or_create_location_id(cur: sqlite3.Cursor, location_name: str) -> int:
    """
    Insert location into `locations` if not exists and return its id.
    """
    cur.execute(
        "INSERT OR IGNORE INTO locations(name) VALUES (?);",
        (location_name,),
    )
    cur.execute(
        "SELECT id FROM locations WHERE name = ?;",
        (location_name,),
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"Failed to get id for location: {location_name}")
    return row[0]


def insert_temperature_records(conn: sqlite3.Connection, records):
    """
    Insert or update temperature records.

    records: iterable of (location_name, date, min_temp_c, max_temp_c)
    """
    cur = conn.cursor()

    for loc_name, date, min_t, max_t in records:
        location_id = get_or_create_location_id(cur, loc_name)

        # UPSERT into temperatures (SQLite 3.24+)
        cur.execute(
            """
            INSERT INTO temperatures (location_id, date, min_temp_c, max_temp_c)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(location_id, date) DO UPDATE SET
                min_temp_c = excluded.min_temp_c,
                max_temp_c = excluded.max_temp_c;
            """,
            (location_id, date, min_t, max_t),
        )

    conn.commit()


# -------------- Step 5: Main -------------- #

def main():
    # 1) Fetch JSON
    data = fetch_cwa_json()

    # 2) Extract temperature records
    records = extract_temperature_records(data)

    # 3) Init DB and insert records
    conn = init_db(DB_PATH)
    insert_temperature_records(conn, records)

    # Optional: print a small preview from DB
    cur = conn.cursor()
    cur.execute(
        """
        SELECT l.name, t.date, t.min_temp_c, t.max_temp_c
        FROM temperatures t
        JOIN locations l ON t.location_id = l.id
        ORDER BY l.name, t.date
        LIMIT 10;
        """
    )
    rows = cur.fetchall()
    print("Sample data from database:")
    for r in rows:
        print(r)

    conn.close()


if __name__ == "__main__":
    main()
