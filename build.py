"""Scrape every board, merge with saved listings, and build the static site.

Usage:
    python build.py             # scrape all boards, then build site/
    python build.py --no-scrape # rebuild site/ from data/jobs.json only
"""
import argparse
import json
import sys
import traceback
from datetime import date, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).parent))
from scraper.classify import ROLES, classify
from scraper.sources import SOURCES

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "jobs.json"
SITE = ROOT / "site"
MAX_AGE_DAYS = 120

BOARDS = [
    {"name": "דרושים · עריכת דין", "url": "https://www.drushim.co.il/jobs/cat14/"},
    {"name": "מובטל · חוק ומשפט", "url": "https://www.muvtal.co.il/jobs?filter_categories=38"},
    {"name": "לשכת עוה״ד מחוז מרכז", "url": "https://merkazbar.org.il/%D7%99%D7%97%D7%99%D7%93%D7%AA-%D7%94%D7%A9%D7%9E%D7%94/%D7%93%D7%A8%D7%95%D7%A9%D7%99%D7%9D/"},
    {"name": "לשכת עוה״ד מחוז ירושלים", "url": "https://jerusalembar.org.il/mdrushim/"},
]


def load():
    if DATA.exists():
        return json.loads(DATA.read_text(encoding="utf-8"))
    return {"updated": None, "jobs": {}, "status": {}}


def scrape(store):
    today = date.today().isoformat()
    jobs = store["jobs"]
    for key, src in SOURCES.items():
        try:
            raw = src["fn"]()
        except Exception as e:  # keep yesterday's listings when a board is down
            traceback.print_exc()
            store["status"][key] = {"ok": False, "date": today, "error": str(e)[:200], "count": 0}
            print(f"[{key}] FAILED: {e}", file=sys.stderr)
            continue
        found = set()
        for r in raw:
            job = classify(r)
            old = jobs.get(job["id"], {})
            job["first_seen"] = old.get("first_seen", today)
            job["posted"] = job["posted"] or old.get("posted") or job["first_seen"]
            job["dated"] = bool(r.get("posted")) or old.get("dated", False)
            job["board"] = key
            jobs[job["id"]] = job
            found.add(job["id"])
        # on a board scraped in full, listings that disappeared are closed
        if src["complete"]:
            for jid in [j for j, v in jobs.items() if v.get("board") == key and j not in found]:
                del jobs[jid]
        store["status"][key] = {"ok": True, "date": today, "count": len(found)}
        print(f"[{key}] {len(found)} listings")
    for jid in [j for j, v in jobs.items()
                if v["posted"] < (date.today() - timedelta(days=SOURCES.get(v.get("board"), {}).get("max_age", 120))).isoformat()]:
        del jobs[jid]
    store["updated"] = today


def build(store):
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    jobs = sorted(store["jobs"].values(), key=lambda j: (j["posted"], j["id"]), reverse=True)
    html = env.get_template("index.html").render(
        payload={"updated": store["updated"], "jobs": jobs, "roles": ROLES},
        boards=BOARDS,
        total=len(jobs),
        updated=store["updated"],
    )
    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(html, encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built site/index.html with {len(jobs)} listings")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-scrape", action="store_true")
    args = ap.parse_args()
    store = load()
    if not args.no_scrape:
        scrape(store)
        DATA.parent.mkdir(exist_ok=True)
        DATA.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")
    build(store)


if __name__ == "__main__":
    main()
