# דרושים במשפט

A public board of every legal job in Israel: lawyers, interns (מתמחים), law students and pre-interns, legal counsel, and legal secretaries.

A Python scraper collects listings from public job boards every morning, tags each one by role, practice area, city and experience, and builds a static Hebrew site that GitHub Pages hosts.

## Sources

| Board | What the scraper reads |
| --- | --- |
| Drushim, עריכת דין category | Newest ~25 listings each day; history builds up across runs |
| Muvtal, חוק ומשפט category | All pages |
| Israel Bar, Central district board | Full board, with posting dates |
| Israel Bar, Jerusalem district board | Full board (no dates) |

Add a board by writing a function in `scraper/sources.py` that returns raw job dicts and registering it in `SOURCES`.

## Run locally

```bash
pip install -r requirements.txt
python build.py              # scrape + build site/index.html
python build.py --no-scrape  # rebuild from data/jobs.json only
```

## How it updates

`.github/workflows/update.yml` runs daily at 04:00 UTC (and on every push to `main`). It scrapes, commits `data/jobs.json` so listing history survives between runs, and deploys `site/` to GitHub Pages.

Listings are removed when they disappear from a board that is scraped in full, or when they pass the board's maximum age (45 days for Drushim, 120 for the others).
