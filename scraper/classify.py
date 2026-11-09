"""Turn raw scraped ads into tagged listings: role, practice areas, city, experience."""
import re

ROLES = [
    ("students", "סטודנטים וטרום התמחות"),
    ("interns", "מתמחים"),
    ("lawyers", "עורכי דין"),
    ("counsel", "יועצים משפטיים"),
    ("support", "מזכירות, פרלגל ומנהלה"),
    ("other", "אחר"),
]

AREAS = {
    "נדל״ן ומקרקעין": ["נדל\"ן", "נדל״ן", "מקרקעין", "התחדשות עירונית", "טאבו"],
    "תכנון ובנייה": ["תכנון ובנייה", "תכנון והבנייה"],
    "ליטיגציה": ["ליטיגציה", "כתבי טענות", "כתבי בי-דין", "כתבי בי דין"],
    "נזיקין ונזקי גוף": ["נזיקין", "נזקי גוף", "רשלנות רפואית", "תאונות"],
    "ביטוח": ["ביטוח"],
    "משפחה וירושה": ["דיני משפחה", "משפחה", "גירושין", "ירושה", "צוואות"],
    "פלילי": ["פלילי"],
    "מסחרי וחברות": ["מסחרי", "חברות", "תאגידי", "הסכמים", "עסקאות"],
    "הייטק וטכנולוגיה": ["הייטק", "טכנולוגי", "סטארט", "high-tech", "tech"],
    "קניין רוחני": ["קניין רוחני", "פטנט", "סימני מסחר"],
    "מיסוי": ["מיסוי", "מסים", "מיסים"],
    "דיני עבודה": ["דיני עבודה", "יחסי עבודה"],
    "חדלות פירעון והוצל״פ": ["חדלות פירעון", "הוצאה לפועל", "הוצל\"פ", "הוצל״פ", "גבייה", "גביה", "פשיטת רגל"],
    "מנהלי וציבורי": ["מנהלי", "רשויות מקומיות", "בג\"ץ", "בג״ץ", "משפט ציבורי"],
    "ביטוח לאומי וזכויות": ["ביטוח לאומי", "מיצוי זכויות"],
}

CITIES = [
    "תל אביב", "ירושלים", "חיפה", "רמת גן", "גבעתיים", "פתח תקווה", "פתח תקוה", "ראשון לציון",
    "חולון", "בת ים", "בני ברק", "הרצליה", "רעננה", "כפר סבא", "הוד השרון", "נתניה", "חדרה",
    "רחובות", "נס ציונה", "יבנה", "אשדוד", "אשקלון", "באר שבע", "מודיעין", "בית שמש", "לוד",
    "רמלה", "קריית אונו", "קרית אונו", "אור יהודה", "ראש העין", "יהוד", "נצרת", "עפולה",
    "טבריה", "כרמיאל", "עכו", "נהריה", "קריית שמונה", "קרית שמונה", "אילת", "קריית גת",
    "אריאל", "מעלה אדומים", "רמת השרון", "זכרון יעקב", "קיסריה", "יקנעם", "שוהם", "אלעד",
]
CITY_NORMAL = {"פתח תקוה": "פתח תקווה", "קרית אונו": "קריית אונו", "קרית שמונה": "קריית שמונה"}

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)0\d{1,2}[-\s]?\d{3}[-\s]?\d{4}(?!\d)|(?<!\d)05\d[-\s]?\d{7}(?!\d)")
OFFICE_PHRASES = re.compile(r"(ל?משרד(י)? (ה)?עורכי ה?דין|ל?משרד עו[\"״]ד|ל?משרד עוה[\"״]ד|לשכת עורכי הדין)")


def _has(text, words):
    return any(w in text for w in words)


def roles_for(title, text):
    """Classify by title first; fall back to the opening of the ad text."""
    found = []
    for scope in (title, text[:260]):
        t = OFFICE_PHRASES.sub(" ", scope)
        if re.search(r"סטודנט|טרום[\s-]?מתמח|קדם[\s-]?מתמח", t):
            found.append("students")
        if re.search(r"(?<!טרום )(?<!טרום-)(?<!קדם )מתמח", t):
            found.append("interns")
        if re.search(r"עו[\"״]ד|עור[כך](/?ת)?[\s-]?דין|עורכי(/ות)?[\s-]?דין|lawyer|attorney", t, re.I):
            found.append("lawyers")
        if re.search(r"יוע[צץ](/?ת)? משפטי|יועמ[\"״]ש|legal counsel", t, re.I):
            found.append("counsel")
        if re.search(r"מזכיר|פרלגל|פרליגל|paralegal|מנהל(/?ת)? משרד|עוזר(/?ת)? משפטי|עוזרת משפטית|קלדנ|"
                     r"רכז(/?ת)? (משפטי|גבי)|בק אופיס|back office|פקיד|נציג|אדמיניסטר|מחתים|גבי(י)?ה", t, re.I):
            found.append("support")
        if found:
            break
    # ads for other roles that say they are open to law students also count as student jobs
    if re.search(r"סטודנט\S*\s+(ל)?משפטים|טרום[\s-]?מתמח|קדם[\s-]?מתמח", text):
        found.append("students")
    return list(dict.fromkeys(found)) or ["other"]


def classify(raw):
    full = " ".join([raw["title"], raw.get("employer", ""), raw["text"], " ".join(raw.get("meta", []))])
    cities = list(raw.get("cities") or [])
    for c in CITIES:
        if c in full:
            c = CITY_NORMAL.get(c, c)
            if c not in cities:
                cities.append(c)
    areas = [name for name, words in AREAS.items() if _has(full, words)]

    meta = raw.get("meta", [])
    experience = next((m for m in meta if "נסיון" in m or "ניסיון" in m or "שנים" in m or "שנה" in m), "")
    if not experience:
        if re.search(r"ללא (ה)?(נסיון|ניסיון)|לא נדרש (נסיון|ניסיון)|אין צורך ב(נסיון|ניסיון)", full):
            experience = "ללא ניסיון"
        else:
            m = re.search(r"(\d+\s*[-–]\s*\d+|\d+)\s*שנות (נסיון|ניסיון|ותק)", full)
            if m:
                experience = m.group(0)
    scope = next((m for m in meta if "משרה" in m), "")
    if not scope:
        if "משרה חלקית" in full:
            scope = "משרה חלקית"
        elif "משרה מלאה" in full:
            scope = "משרה מלאה"

    excerpt = PHONE.sub("", EMAIL.sub("", raw["text"]))
    excerpt = re.sub(r"https?://\S+", "", excerpt)
    excerpt = re.sub(r"\s+", " ", excerpt).strip()
    if len(excerpt) > 260:
        excerpt = excerpt[:260].rsplit(" ", 1)[0] + "…"

    return {
        "id": raw["id"],
        "source": raw["source"],
        "url": raw["url"],
        "title": raw["title"],
        "employer": raw.get("employer", ""),
        "cities": cities[:4],
        "roles": roles_for(raw["title"], raw["text"]),
        "areas": areas[:4],
        "experience": experience,
        "scope": scope,
        "excerpt": excerpt,
        "posted": raw.get("posted"),
    }
