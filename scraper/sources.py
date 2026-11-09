"""One scraper function per job board. Each returns a list of raw job dicts.

Raw job keys: id, source, url, title, employer, cities (list), text,
posted (YYYY-MM-DD or None), meta (list of short strings from the board).
"""
import json
import re
import time
from datetime import date, timedelta
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept-Language": "he-IL,he;q=0.9"})

MERKAZ_URL = "https://merkazbar.org.il/%D7%99%D7%97%D7%99%D7%93%D7%AA-%D7%94%D7%A9%D7%9E%D7%94/%D7%93%D7%A8%D7%95%D7%A9%D7%99%D7%9D/"
JLM_URL = "https://jerusalembar.org.il/mdrushim/"
DRUSHIM_URLS = [
    "https://www.drushim.co.il/jobs/cat14/",  # עריכת דין, all roles
    # legal subcategories: counsel, interns, lawyers, legal secretaries, contracts, law students, enforcement
    *[f"https://www.drushim.co.il/jobs/subcat/{n}/" for n in (125, 126, 127, 440, 692, 697, 707)],
]
MUVTAL_URL = "https://www.muvtal.co.il/jobs?filter_categories=38&page={page}"
# later result pages require signing in, so only the first page of each search is read
JOBMASTER_URL = "https://www.jobmaster.co.il/jobs/q-{query}/"
JOBMASTER_QUERIES = ["סטודנט-למשפטים", "טרום-מתמחה", "מתמחה-משפטים", "עורך-דין", "מזכירה-משפטית", "יועץ-משפטי"]
MPLOY_URL = "https://www.mploy.co.il/job/tagged/%D7%A1%D7%98%D7%95%D7%93%D7%A0%D7%98%D7%99%D7%9D-%D7%9E%D7%A9%D7%A4%D7%98%D7%99%D7%9D"

LEGALALPHABET_URL = "https://legalalphabet.com/api/jobs.php?country=IL&limit=100"
SHIBOLET_URL = "https://www.shibolet.com/careers/"
EN_CITIES = {"Tel Aviv": "תל אביב", "Jerusalem": "ירושלים", "Haifa": "חיפה", "Petah Tikva": "פתח תקווה",
             "Ra'anana": "רעננה", "Herzliya": "הרצליה", "Ramat Gan": "רמת גן", "Yokneam": "יקנעם",
             "Rehovot": "רחובות", "Netanya": "נתניה", "Be'er Sheva": "באר שבע"}

# general boards return some non-legal ads; keep an ad only if it mentions law
LEGAL_WORDS = re.compile(r"משפט|עו[\"״]ד|עור[כך](/?ת)?[\s-]?דין|עורכי[\s-]?דין|מתמח|legal|lawyer|attorney", re.I)


def fetch(url, tries=4):
    last = None
    for attempt in range(tries):
        try:
            r = session.get(url, timeout=45)
            r.raise_for_status()
            r.encoding = r.apparent_encoding if r.encoding in (None, "ISO-8859-1") else r.encoding
            return r.text
        except requests.RequestException as e:
            last = e
            time.sleep(2 + attempt * 3)
    raise last


def soup_text(html):
    s = BeautifulSoup(html, "html.parser")
    for t in s(["script", "style", "nav", "header", "footer", "noscript"]):
        t.decompose()
    return s, s.get_text("\n", strip=True)


def relative_date(text, today=None):
    """Turn Hebrew relative dates ("לפני 3 ימים") into an ISO date."""
    today = today or date.today()
    t = text.strip()
    if "דק" in t or "שע" in t or "היום" in t:
        return today.isoformat()
    if "אתמול" in t:
        return (today - timedelta(days=1)).isoformat()
    n = re.search(r"(\d+)", t)
    n = int(n.group(1)) if n else 1
    if "יום" in t or "ימים" in t:
        return (today - timedelta(days=n)).isoformat()
    if "שבוע" in t:
        return (today - timedelta(weeks=n)).isoformat()
    if "חודש" in t:
        return (today - timedelta(days=30 * n)).isoformat()
    return None


def first_line_title(lines, max_len=110):
    """Pick a readable title from the opening lines of a free-text ad."""
    for line in lines:
        clean = line.strip(" :!?.-–_*")
        if len(clean) >= 8 and not clean.startswith("http") and "@" not in clean:
            return clean[:max_len]
    return "משרה"


# ---------------------------------------------------------------- Drushim
def drushim():
    """Each public category page lists only its newest jobs; daily runs accumulate them."""
    jobs, seen = [], set()
    cards = []
    for url in DRUSHIM_URLS:
        cards += BeautifulSoup(fetch(url), "html.parser").select('article[class*="job-card-module"]')
        time.sleep(1.5)
    for c in cards:
        a = c.select_one('a[href^="/job/"]')
        if not a:
            continue
        m = re.match(r"/job/(\d+)/", a["href"])
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        title = c.select_one('[class*="__title"]')
        company = c.select_one('[class*="companyName"]')
        desc = c.select_one('p[class*="__description"]')
        meta = [e.get_text(" ", strip=True) for e in c.select('[class*="job-card-meta"][class*="__text"], [class*="tooltip"][class*="__item"]')]
        posted = next((relative_date(x) for x in meta if x.startswith("לפני") or x in ("היום", "אתמול")), None)
        jobs.append({
            "id": "drushim-" + m.group(1),
            "source": "דרושים",
            "url": "https://www.drushim.co.il" + a["href"],
            "title": title.get_text(" ", strip=True) if title else "משרה",
            "employer": company.get_text(" ", strip=True) if company else "",
            "cities": [],
            "text": desc.get_text(" ", strip=True) if desc else "",
            "posted": posted,
            "meta": [x for x in meta if not x.startswith("לפני")],
        })
    return jobs


# ---------------------------------------------------------------- Muvtal
def muvtal(max_pages=15):
    jobs, seen = [], set()
    for page in range(1, max_pages + 1):
        html = fetch(MUVTAL_URL.format(page=page))
        s = BeautifulSoup(html, "html.parser")
        new = 0
        for a in s.find_all("a", href=True):
            m = re.search(r"/jobs/[^/?#]*_(\d+)$", a["href"])
            if not m or m.group(1) in seen:
                continue
            # climb to the card that holds this job's full text
            card = a
            while card.parent is not None and len(card.get_text(strip=True)) < 120:
                card = card.parent
            parts = [p for p in card.get_text("\n", strip=True).split("\n") if p]
            if len(parts) < 3:
                continue
            seen.add(m.group(1))
            new += 1
            href = a["href"] if a["href"].startswith("http") else "https://www.muvtal.co.il" + a["href"]
            jobs.append({
                "id": "muvtal-" + m.group(1),
                "source": "מובטל",
                "url": href,
                "title": parts[0][:110],
                "employer": "",
                "cities": [],
                "text": " ".join(parts[1:40]),
                "posted": None,
                "meta": [],
            })
        if new == 0:
            break
        time.sleep(1.5)
    return jobs


# ---------------------------------------------------------------- JobMaster
def jobmaster():
    jobs, seen = [], set()
    for query in JOBMASTER_QUERIES:
        s = BeautifulSoup(fetch(JOBMASTER_URL.format(query=query)), "html.parser")
        for c in s.select("article.JobItem"):
            jid = (c.get("id") or "").replace("misra", "")
            if not jid.isdigit() or jid in seen:
                continue
            seen.add(jid)
            title = c.select_one("a.CardHeader")
            desc = c.select_one(".jobShortDescription")
            posted = c.find("span", class_="Gray", string=re.compile("פורסם"))
            employer = posted.find_next_sibling("span") if posted else None
            tags = [a.get_text(" ", strip=True) for a in c.select("a:not(.CardHeader)")]
            text = desc.get_text(" ", strip=True) if desc else ""
            title_text = title.get_text(" ", strip=True).rstrip(".") if title else "משרה"
            if not LEGAL_WORDS.search(title_text + " " + text):
                continue
            jobs.append({
                "id": "jobmaster-" + jid,
                "source": "ג'ובמאסטר",
                "url": "https://www.jobmaster.co.il/jobs/checknum.asp?key=" + jid,
                "title": title_text[:110],
                "employer": employer.get_text(" ", strip=True) if employer else "",
                "cities": [],
                "text": text,
                "posted": relative_date(posted.get_text(" ", strip=True).replace("פורסם", "")) if posted else None,
                "meta": [t for t in tags if "משרה" in t or "ניסיון" in t],
            })
        time.sleep(1.5)
    return jobs


# ---------------------------------------------------------------- mploy (public-sector student jobs)
def mploy():
    s = BeautifulSoup(fetch(MPLOY_URL), "html.parser")
    jobs, seen = [], set()
    for a in s.find_all("a", href=re.compile(r"job/details/\d+")):
        jid = re.search(r"details/(\d+)", a["href"]).group(1)
        if jid in seen:
            continue
        seen.add(jid)
        card = a
        while card.parent is not None and len(card.get_text(strip=True)) < 80:
            card = card.parent
        parts = [p for p in card.get_text("\n", strip=True).split("\n") if p and p != "קרא עוד"]
        if not LEGAL_WORDS.search(" ".join(parts)):
            continue
        when = next((p for p in parts if p.startswith("לפני")), None)
        jobs.append({
            "id": "mploy-" + jid,
            "source": "mploy",
            "url": "https://www.mploy.co.il/job/details/" + jid,
            "title": parts[0][:110],
            "employer": "",
            "cities": [],
            "text": " ".join(parts[1:]),
            "posted": relative_date(when) if when else None,
            "meta": [],
        })
    return jobs


# ---------------------------------------------------------------- Bar association, Central district
def merkaz():
    _, text = soup_text(fetch(MERKAZ_URL))
    pattern = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})\s*\n\s*משרה\s*(\d+)\s*\n")
    marks = list(pattern.finditer(text))
    jobs = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end].split("____")[0]
        lines = [l for l in body.split("\n") if l.strip()]
        if not lines:
            continue
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y = y + 2000 if y < 100 else y
        try:
            posted = date(y, mo, d).isoformat()
        except ValueError:
            posted = None
        link = re.search(r"https?://\S+", body)
        lines = [l for l in lines if l.strip() != "משרה"]
        jobs.append({
            "id": "merkaz-" + m.group(4),
            "source": "לשכת עוה״ד מחוז מרכז",
            "url": link.group(0).rstrip(".,)") if link else MERKAZ_URL,
            "title": first_line_title(lines),
            "employer": "",
            "cities": [],
            "text": " ".join(lines),
            "posted": posted,
            "meta": [],
        })
    return jobs


# ---------------------------------------------------------------- Bar association, Jerusalem district
def jerusalem():
    _, text = soup_text(fetch(JLM_URL))
    marks = list(re.finditer(r"^#(\d+)\s+(.*)$", text, re.M))
    jobs = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end]
        lines = [l for l in body.split("\n") if l.strip()]
        title = m.group(2).strip() or first_line_title(lines)
        jobs.append({
            "id": "jlm-" + m.group(1),
            "source": "לשכת עוה״ד מחוז ירושלים",
            "url": JLM_URL,
            "title": title[:110],
            "employer": "",
            "cities": [],
            "text": " ".join(lines),
            "posted": None,
            "meta": [],
        })
    return jobs


# ---------------------------------------------------------------- LegalAlphabet (public JSON feed)
def legalalphabet():
    """LegalAlphabet publishes a free read-only feed and asks to be read through it, not scraped."""
    data = json.loads(fetch(LEGALALPHABET_URL))
    jobs = []
    for x in data.get("jobs") or data.get("results") or []:
        loc = (x.get("location") or {}).get("display", "")
        jobs.append({
            "id": f"la-{x['id']}",
            "source": "LegalAlphabet",
            "url": x.get("url") or f"https://legalalphabet.com/{x.get('type', 'job')}/{x.get('slug', x['id'])}",
            "title": x.get("title", "")[:110],
            "employer": (x.get("company") or {}).get("name", ""),
            "cities": [he for en, he in EN_CITIES.items() if en in loc],
            "text": re.sub(r"\s+", " ", x.get("description") or "")[:600],
            "posted": (x.get("posted_at") or x.get("date_posted") or "")[:10] or None,
            "meta": ["עבודה מרחוק"] if (x.get("location") or {}).get("remote") else [],
        })
    return jobs


# ---------------------------------------------------------------- Shibolet (firm careers page)
def shibolet():
    s = BeautifulSoup(fetch(SHIBOLET_URL), "html.parser")
    jobs = []
    for a in s.find_all("a", string=lambda t: t and "למידע נוסף" in t):
        card = a
        while card.parent is not None and len(card.get_text(strip=True)) < 25:
            card = card.parent
        title = card.get_text(" | ", strip=True).split(" | ")[0]
        href = a.get("href", "")
        jobs.append({
            "id": "shibolet-" + re.sub(r"\W+", "-", unquote(href).rstrip("/").rsplit("/", 1)[-1])[:80],
            "source": "שיבולת עורכי דין",
            "url": href,
            "title": title[:110],
            "employer": "שיבולת ושות׳",
            "cities": ["תל אביב"],
            "text": "",
            "posted": None,
            "meta": [],
        })
    return jobs


# complete=True: the scrape sees the board's whole list, so a missing ad means it closed.
# complete=False: the scrape sees only the newest ads, so older ones expire by age instead.
# strict=True: a general board; drop ads that match no legal role (guards at "משרד המשפטים", translators...).
SOURCES = {
    "drushim": {"fn": drushim, "complete": False, "max_age": 45},
    "muvtal": {"fn": muvtal, "complete": True, "max_age": 120},
    "jobmaster": {"fn": jobmaster, "complete": False, "max_age": 60, "strict": True},
    "mploy": {"fn": mploy, "complete": False, "max_age": 45, "strict": True},
    "merkaz": {"fn": merkaz, "complete": True, "max_age": 120},
    "jerusalem": {"fn": jerusalem, "complete": True, "max_age": 120},
    "legalalphabet": {"fn": legalalphabet, "complete": True, "max_age": 120, "strict": True},
    "shibolet": {"fn": shibolet, "complete": True, "max_age": 365},
}
