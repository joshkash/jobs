"""Turn raw scraped ads into tagged student listings: field, city, hours, study year."""
import re

# Order matters: an ad gets at most two fields, the first ones that match.
FIELDS = {
    "הייטק ותוכנה": [r"תוכנה", r"פיתוח", r"מפתח", r"\bQA\b", r"בדיקות תוכנה", r"דאטה", r"\bdata\b", r"\bIT\b",
                     r"סייבר", r"devops", r"אלגוריתם", r"software", r"developer", r"python", r"full ?stack", r"הייטק"],
    "הנדסה": [r"הנדס", r"חומרה", r"hardware", r"אדריכל", r"שרטוט", r"מכונות", r"חשמל", r"בנייה", r"אלקטרוניקה"],
    "כספים וכלכלה": [r"כספים", r"חשבונא", r"הנהלת חשבונות", r"כלכל", r"בנק", r"ביטוח", r"תקציב", r"שוק ההון",
                      r"פיננס", r"finance", r"ראיית חשבון", r"רואה חשבון", r"\bCPA\b", r"audit", r"ביקורת"],
    "משפטים": [r"משפט", r"עו[\"״]ד", r"עור[כך](/?ת)?[\s-]?דין", r"עורכי[\s-]?דין", r"מתמח", r"legal", r"lawyer"],
    "מדעים ומחקר": [r"מחקר", r"מעבדה", r"ביולוג", r"כימי", r"ביוטק", r"מדעי", r"research", r"\blab\b"],
    "שיווק ומכירות": [r"שיווק", r"מכירות", r"\bsales\b", r"marketing", r"דיגיטל", r"סושיאל", r"קופירייט", r"תוכן"],
    "שירות לקוחות": [r"שירות לקוחות", r"מוקד", r"נציג", r"טלפוני", r"call center", r"תמיכה"],
    "אדמיניסטרציה": [r"אדמיניסטר", r"מזכיר", r"פקיד", r"רכז", r"back office", r"בק אופיס", r"הקלדה", r"משאבי אנוש",
                      r"גיוס", r"\bHR\b", r"קליטה", r"רכש", r"לוגיסטיקה"],
    "חינוך והדרכה": [r"מורה", r"הוראה", r"חינוך", r"מדריכ", r"הדרכה", r"שיעורים", r"צהרון", r"תגבור", r"חונכ", r"מתרגל"],
    "בריאות ורווחה": [r"רפוא", r"אחות", r"אחים", r"סיעוד", r"פסיכולוג", r"סוציאל", r"רווחה", r"מטפל", r"בית חולים", r"קליני"],
    "שירות ציבורי": [r"משרד ה\S+", r"עיריי", r"רשות ה", r"ממשל", r"כנסת", r"מבקר המדינה", r"פרקליטות", r"בית המשפט", r"בתי המשפט"],
    "מסחר, אירוח ושטח": [r"מלצר", r"קופאי", r"מחסן", r"שליח", r"אבטחה", r"מאבטח", r"מוקדן", r"בריסטה", r"מסעד", r"חנות", r"סדרן"],
}
FIELD_PATTERNS = {name: re.compile("|".join(words), re.I) for name, words in FIELDS.items()}

CITIES = [
    "תל אביב", "ירושלים", "חיפה", "רמת גן", "גבעתיים", "פתח תקווה", "פתח תקוה", "ראשון לציון",
    "חולון", "בת ים", "בני ברק", "הרצליה", "רעננה", "כפר סבא", "הוד השרון", "נתניה", "חדרה",
    "רחובות", "נס ציונה", "יבנה", "אשדוד", "אשקלון", "באר שבע", "מודיעין", "בית שמש", "לוד",
    "רמלה", "קריית אונו", "קרית אונו", "אור יהודה", "ראש העין", "יהוד", "נצרת", "עפולה",
    "טבריה", "כרמיאל", "עכו", "נהריה", "קריית שמונה", "קרית שמונה", "אילת", "קריית גת",
    "אריאל", "מעלה אדומים", "רמת השרון", "זכרון יעקב", "קיסריה", "יקנעם", "שוהם", "אלעד",
    "חיפה", "קריית אתא", "נשר", "טירת כרמל", "גבעת שמואל", "קריית מוצקין", "מגדל העמק",
]
CITY_NORMAL = {"פתח תקוה": "פתח תקווה", "קרית אונו": "קריית אונו", "קרית שמונה": "קריית שמונה"}

STUDENT = re.compile(r"סטודנט|טרום[\s-]?מתמח|קדם[\s-]?מתמח|\bstudents?\b|\bintern(ship)?\b|לתואר (ראשון|שני)", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)0\d{1,2}[-\s]?\d{3}[-\s]?\d{4}(?!\d)|(?<!\d)05\d[-\s]?\d{7}(?!\d)")
YEARS = {"א": 1, "ב": 2, "ג": 3, "ד": 4}


# jobs that serve students rather than employ them (dorm maintenance, student-affairs staff)
ABOUT_STUDENTS = re.compile(r"מעונות (ה)?סטודנטים|(מינהל|ליווי|דיקנט|שירותי|רכז/?ת?) (ה)?סטודנטים")


def is_student_job(raw):
    """True when the ad is meant for (or open to) students."""
    if raw.get("student_board"):
        return True
    return bool(STUDENT.search(ABOUT_STUDENTS.sub(" ", raw["title"] + " " + raw["text"][:600])))


def fields_for(raw):
    if raw.get("field"):
        return [raw["field"]]
    found = [name for name, pat in FIELD_PATTERNS.items() if pat.search(raw["title"])]
    if not found:
        found = [name for name, pat in FIELD_PATTERNS.items() if pat.search(raw["text"][:400])]
    return found[:2] or ["כללי"]


def study_year(full):
    """Minimum study year the ad asks for (1-4), or None."""
    m = re.search(r"שנה\s*([אבגד])['׳]", full)
    if m:
        return YEARS[m.group(1)]
    m = re.search(r"(first|second|third|1st|2nd|3rd)[- ]year", full, re.I)
    if m:
        return {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3}[m.group(1).lower()]
    return None


def classify(raw):
    full = " ".join([raw["title"], raw.get("employer", ""), raw["text"], " ".join(raw.get("meta", []))])
    cities = list(raw.get("cities") or [])
    for c in CITIES:
        if c in full:
            c = CITY_NORMAL.get(c, c)
            if c not in cities:
                cities.append(c)

    perks = []
    if re.search(r"משרה חלקית|חלקית|part[- ]time|\d+\s*שעות (חודשיות|בחודש|שבועיות)", full, re.I):
        perks.append("משרה חלקית")
    if re.search(r"שעות גמישות|גמישות בשעות|התאמה ללימודים|בהתאם (ל)?מערכת", full):
        perks.append("שעות גמישות")
    if re.search(r"מהבית|היברידי|hybrid|remote|מרחוק", full, re.I):
        perks.append("היברידי / מהבית")
    if re.search(r"ללא (ה)?(נסיון|ניסיון)|לא נדרש (נסיון|ניסיון)|אין צורך ב(נסיון|ניסיון)", full):
        perks.append("ללא ניסיון")
    if re.search(r"ערב|משמרות", full):
        perks.append("משמרות / ערב")

    excerpt = PHONE.sub("", EMAIL.sub("", raw["text"]))
    excerpt = re.sub(r"https?://\S+", "", excerpt)
    excerpt = re.sub(r"\s+", " ", excerpt).strip()
    if len(excerpt) > 320:
        excerpt = excerpt[:320].rsplit(" ", 1)[0] + "…"

    return {
        "id": raw["id"],
        "source": raw["source"],
        "url": raw["url"],
        "title": raw["title"],
        "employer": raw.get("employer", ""),
        "cities": cities[:4],
        "fields": fields_for(raw),
        "perks": perks,
        "year": study_year(full),
        "excerpt": excerpt,
        "posted": raw.get("posted"),
    }
