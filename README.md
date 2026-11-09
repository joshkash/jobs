# עבודות לסטודנטים

A public board of student jobs in Israel, in every field: tech, engineering, finance, law, sciences, customer service, admin, education, public service and more.

A Python scraper collects student listings from public job boards every morning, tags each by field, city, hours and study year, and builds a static Hebrew job-search site that GitHub Pages hosts.

## Sources

| Board | What the scraper reads |
| --- | --- |
| Drushim | Its 9 student categories (general, software, QA, hardware, engineering, construction, finance, sciences, law). Newest listings each day; history builds up across runs |
| JobMaster | First page of searches like סטודנט, משרת סטודנט, סטודנט תוכנה (later pages need a login) |
| mploy | Public-sector student jobs |
| Muvtal | Law-student category |
| Israel Bar, Central and Jerusalem districts | Student listings only |
| LegalAlphabet | Its public JSON feed, student and intern roles only |

Facebook groups are not scraped: they need a login and Facebook forbids automated collection. The site links to Facebook group searches instead.

A listing is kept only if it is meant for students: it sits in a student category, or its title or text mentions students (סטודנט, טרום מתמחה, student, intern).

Add a board by writing a function in `scraper/sources.py` that returns raw job dicts and registering it in `SOURCES`.

## Run locally

```bash
pip install -r requirements.txt
python build.py              # scrape + build site/index.html
python build.py --no-scrape  # rebuild from data/jobs.json only
```

## How it updates

`.github/workflows/update.yml` runs daily at 04:00 UTC (and on every push to `main`). It scrapes, commits `data/jobs.json` so listing history survives between runs, and deploys `site/` to GitHub Pages.
