"""Scrape every board, merge with saved listings, and build the static site.

Usage:
    python build.py             # scrape all boards, then build site/
    python build.py --no-scrape # rebuild site/ from data/jobs.json only
"""
import argparse
import json
import sys
import time
import traceback
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).parent))
from scraper.classify import FIELDS, classify, is_student_job
from scraper.sources import SOURCES

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "jobs.json"
SITE = ROOT / "site"

BOARDS = [
    {"name": "דרושים · משרות סטודנט", "url": "https://www.drushim.co.il/jobs/subcat/88/"},
    {"name": "ג'ובמאסטר · עבודה לסטודנטים", "url": "https://www.jobmaster.co.il/jobs/q-%D7%A1%D7%98%D7%95%D7%93%D7%A0%D7%98/"},
    {"name": "mploy · משרות סטודנט בשירות הציבורי", "url": "https://www.mploy.co.il/job/tagged/%D7%A1%D7%98%D7%95%D7%93%D7%A0%D7%98%D7%99%D7%9D-%D7%9E%D7%A9%D7%A4%D7%98%D7%99%D7%9D"},
    {"name": "מובטל · סטודנטים למשפטים", "url": "https://www.muvtal.co.il/jobs?filter_profession=530"},
    {"name": "לשכת עוה״ד מחוז מרכז", "url": "https://merkazbar.org.il/%D7%99%D7%97%D7%99%D7%93%D7%AA-%D7%94%D7%A9%D7%9E%D7%94/%D7%93%D7%A8%D7%95%D7%A9%D7%99%D7%9D/"},
    {"name": "לשכת עוה״ד מחוז ירושלים", "url": "https://jerusalembar.org.il/mdrushim/"},
    {"name": "LegalAlphabet · Israel", "url": "https://legalalphabet.com/israel/jobs"},
]

# Facebook groups can't be read automatically (they need a login, and Facebook forbids scraping),
# so the site links to Facebook's own group search for the most useful terms.
FACEBOOK = [
    {"name": "דרושים סטודנטים", "q": "דרושים סטודנטים"},
    {"name": "משרות סטודנט", "q": "משרות סטודנט"},
    {"name": "סטודנטים תל אביב והמרכז", "q": "דרושים סטודנטים תל אביב"},
    {"name": "סטודנטים ירושלים", "q": "דרושים סטודנטים ירושלים"},
    {"name": "סטודנטים חיפה והצפון", "q": "דרושים סטודנטים חיפה"},
    {"name": "סטודנטים באר שבע והדרום", "q": "דרושים סטודנטים באר שבע"},
    {"name": "משרות סטודנט בהייטק", "q": "משרות סטודנט הייטק"},
    {"name": "סטודנטים למשפטים", "q": "דרושים סטודנטים למשפטים"},
]

# Law firms that recruit students and interns through standing programs rather than dated ads.
PROGRAMS = [
    {"name": "גורניצקי", "what": "תוכנית מתמחים, פתוחה לסטודנטים", "url": "https://www.gornitzky.com/career-legal-interns/"},
    {"name": "גולדפרב גרוס זליגמן", "what": "מתמחים וסטודנטים", "url": "https://www.goldfarb.com/he/interns/"},
    {"name": "מיתר", "what": "משרות פתוחות ומתמחים", "url": "https://meitar.com/careers/"},
    {"name": "הרצוג פוקס נאמן", "what": "קריירה והגשת קורות חיים", "url": "https://herzoglaw.co.il/en/careers/"},
    {"name": "ברנע ג׳פה לנדה", "what": "התמחות", "url": "https://barlaw.co.il/internship/"},
    {"name": "שיבולת", "what": "מתמחים", "url": "https://www.shibolet.com/%d7%94%d7%97%d7%99%d7%99%d7%9d-%d7%91%d7%a9%d7%91%d7%9c%d7%aa/%d7%9e%d7%aa%d7%9e%d7%97%d7%99%d7%9d-%d7%91%d7%a9%d7%91%d7%9c%d7%aa/"},
]


def load():
    if DATA.exists():
        store = json.loads(DATA.read_text(encoding="utf-8"))
        # listings saved before the site covered student jobs only have no "fields"; drop them
        store["jobs"] = {k: v for k, v in store["jobs"].items() if "fields" in v}
        return store
    return {"updated": None, "jobs": {}, "status": {}}


def scrape(store):
    today = date.today().isoformat()
    jobs = store["jobs"]
    detail_budget = 200  # job pages read per run; the rest wait for tomorrow
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
            if not is_student_job(r):
                jobs.pop(r["id"], None)
                continue
            old = jobs.get(r["id"], {})
            if src.get("detail") and not r.get("body"):
                r["body"] = old.get("raw_body")
                if r["body"] is None and detail_budget > 0:  # each job page is read once, then kept
                    detail_budget -= 1
                    try:
                        r["body"] = src["detail"](r["url"])
                        time.sleep(1)
                    except Exception as e:
                        print(f"[{key}] could not read {r['url']}: {e}", file=sys.stderr)
            job = classify(r)
            if r.get("body") is not None:
                job["raw_body"] = r["body"]
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
    jobs = sorted(({k: v for k, v in j.items() if k != "raw_body"} for j in store["jobs"].values()),
                  key=lambda j: (j["posted"], j["id"]), reverse=True)
    html = env.get_template("index.html").render(
        payload={"updated": store["updated"], "jobs": jobs, "fields": list(FIELDS) + ["כללי"]},
        boards=BOARDS,
        programs=PROGRAMS,
        facebook=[{**f, "url": "https://www.facebook.com/search/groups/?q=" + quote(f["q"])} for f in FACEBOOK],
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
