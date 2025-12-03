import csv
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://ssr1.scrape.center"
OUTPUT = Path(__file__).resolve().parent / "movie.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MovieScraper/1.0; +https://example.com)"
}


def fetch_page(page: int) -> str:
    url = f"{BASE}/page/{page}" if page > 1 else BASE + "/"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_movies(html: str):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.el-card.item")
    for card in cards:
        title = card.select_one("a.name h2")
        title_text = title.get_text(strip=True) if title else ""

        categories = [btn.get_text(strip=True) for btn in card.select(".categories button span")]
        meta = [span.get_text(strip=True) for span in card.select(".info span")]
        publish = ""
        if len(meta) >= 3:
            publish = meta[-1]
        score_tag = card.select_one(".score")
        score = score_tag.get_text(strip=True) if score_tag else ""

        yield {
            "title": title_text,
            "categories": "|".join(categories),
            "meta": " ".join(meta),
            "publish": publish,
            "score": score,
        }


def main():
    rows = []
    for page in range(1, 11):
        html = fetch_page(page)
        rows.extend(parse_movies(html))
        time.sleep(0.5)  # be gentle

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["title", "categories", "meta", "publish", "score"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} movies to {OUTPUT}")


if __name__ == "__main__":
    main()
