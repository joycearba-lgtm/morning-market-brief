"""Produce a concise, dated, evidence-limited Hebrew macro market note.
No LLM, no inference of an event from a headline, and no fabricated new releases.
"""
import json
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Jerusalem")
now = datetime.now(TZ)
date = now.date().isoformat()

def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

market = load("market_data.json")
news = load("news_data.json")
observations = load("macro_indicators.json")
prior = load("macro_brief.json")

def quote_valid(item, age_days=4):
    if not isinstance(item, dict) or item.get("status") != "ok":
        return False
    stamp = item.get("market_time")
    if not isinstance(stamp, (int, float)):
        return False
    ts = datetime.fromtimestamp(stamp, TZ)
    return timedelta(0) <= now - ts <= timedelta(days=age_days)

def pct(item):
    if not isinstance(item, dict) or not quote_valid(item):
        return None
    return item.get("change_percent") if isinstance(item.get("change_percent"), (float, int)) else None

def section(heading, text, sources=None):
    return {"heading": heading, "text": text, "sources": sources or []}

# Confirm the data file is from this morning, otherwise do not publish a fresh note.
try:
    updated = datetime.fromisoformat(market["updated_at"]).astimezone(TZ)
except (KeyError, ValueError, TypeError):
    updated = now - timedelta(days=9)
fresh = updated.date() == now.date() and updated <= now

sections = []
advisor = []
if fresh:
    us = market.get("indices", {})
    sp = pct(us.get("S&P 500"))
    nq = pct(us.get("Nasdaq Composite"))
    if sp is not None and nq is not None:
        if sp > 0 and nq > 0:
            market_read = "המגמה במדדי המניות המרכזיים הייתה חיובית."
        elif sp < 0 and nq < 0:
            market_read = "במדדי המניות המרכזיים נרשמה חולשה."
        else:
            market_read = "הביצועים בין מדדי המניות המרכזיים היו מעורבים."
        market_read += " לא ניתן לקבוע מהנתונים בלבד אם המהלך נבע מציפיות ריבית, מרווחיות או מאירוע חדשותי."
    else:
        market_read = "נתוני מדדי ארה״ב אינם מלאים ולכן לא נקבעה מגמה."

    treasury = market.get("treasury_10y", {})
    # Yahoo quote for 10y is a yield, not a price. We report direction only, never invented causation.
    if quote_valid(treasury) and isinstance(treasury.get("change_bps"), (float, int)):
        bp = treasury["change_bps"]
        if bp > 0.05:
            yield_read = "תשואת אג״ח ארה״ב לעשר שנים עלתה; הדבר עשוי להכביד על תמחור אג״ח במח״מ ארוך ועל נכסים הרגישים לריבית."
        elif bp < -0.05:
            yield_read = "תשואת אג״ח ארה״ב לעשר שנים ירדה; הדבר עשוי לתמוך במחירי אג״ח קיימות, במיוחד במח״מ ארוך."
        else:
            yield_read = "התשואה לעשר שנים נותרה כמעט ללא שינוי לפי הציטוט האחרון."
    else:
        yield_read = "אין נתון תשואה חדש ומאומת לעשר שנים."

    # Real official macro observations, with their reference periods.
    official = observations.get("indicators", {})
    us_lines = []
    for key, label, maximum_age in [
        ("us_cpi", "אינפלציית CPI שנתית", 95),
        ("us_unemployment", "שיעור האבטלה", 95),
        ("us_real_gdp", "צמיחת תוצר ריאלי, קצב שנתי", 160),
        ("us_effective_fed_funds", "ריבית אפקטיבית בפועל", 15),
    ]:
        entry = official.get(key, {})
        if entry.get("status") != "ok":
            continue
        try:
            age = (now.date() - datetime.fromisoformat(entry["observation_date"]).date()).days
        except (TypeError, KeyError, ValueError):
            continue
        if not 0 <= age <= maximum_age:
            continue
        value = entry.get("value")
        if not isinstance(value, (int, float)):
            continue
        us_lines.append(f'{label}: {value:.2f}% (חודש/תקופת ייחוס עד {entry["observation_date"]})')
    if us_lines:
        sections.append(section("ארה״ב — נתוני המאקרו הרשמיים האחרונים",
           ". ".join(us_lines) + ". אלו תאריכי תצפית, לא מועדי הפרסום. הנתונים אינם משמשים בפני עצמם לחיזוי החלטת הריבית.",
           [{"label": "FRED — מאגר סדרות כלכליות", "url": "https://fred.stlouisfed.org/"}]))
    sections.append(section("ארה״ב — ריבית, אג״ח ומניות",
        yield_read + " " + market_read + " המבחן המאקרו־כלכלי הוא האם נתוני האינפלציה והתעסוקה הבאים ישנו את ציפיות הריבית.",
        [{"label": "מקור נתוני שוק: Cboe / Yahoo Finance", "url": "https://finance.yahoo.com/quote/%5ETNX/"}]))

    oil = market.get("commodities", {}).get("WTI futures", {})
    oil_change = pct(oil)
    if oil_change is not None and oil_change > 0:
        energy = "חוזי הנפט התחזקו; אם המהלך יימשך, הוא עשוי להגביר סיכון ללחצי מחירים מצד האנרגיה."
    elif oil_change is not None and oil_change < 0:
        energy = "חוזי הנפט נחלשו; אם המהלך יימשך, הוא עשוי למתן חלק מלחצי המחירים מצד האנרגיה."
    else:
        energy = "לא התקבל ציטוט נפט עדכני; אין להסיק שינוי בסביבת המחירים."
    sections.append(section("אינפלציה — סיכוני אנרגיה לעומת הנתונים הרשמיים",
        energy + " שינוי יומי בנפט אינו מחליף נתון CPI או PCE. תחזיות הפד מספטמבר 2026 הן תחזיות במועד פרסומן ואינן מתעדכנות מדי יום.",
        [{"label": "תחזיות הפד (ספטמבר 2026)", "url": "https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260916.htm"}]))

    sections.append(section("ישראל — מדיניות מוניטרית וגורמי סיכון",
        "בהחלטת 21 באוקטובר הותיר בנק ישראל את הריבית על 3.25%. בתחזית אוקטובר צפה הבנק אינפלציה של 2.1% ב־2027 וריבית ממוצעת של 3.0% ברבעון השלישי של 2027. אלו תחזיות ישנות ביחס למועד הסקירה, ולא החלטה חדשה היום. יש לעקוב אחר השקל, אנרגיה ופרמיית הסיכון.",
        [{"label": "החלטת בנק ישראל (21.10)", "url": "https://www.boi.org.il/publications/pressreleases/21-10-26b/"},
         {"label": "תחזית בנק ישראל (21.10)", "url": "https://www.boi.org.il/publications/pressreleases/21-10-26a/"}]))

    advisor = [
      "אפשר לומר: ״כיוון הריבית עדיין תלוי בנתוני האינפלציה והפעילות; נבחן האם המח״מ מתאים לאופק ההשקעה שלך גם אם התוואי ישתנה.״",
      "אפשר לומר: ״תזוזה בתשואות האג״ח משפיעה במיוחד על אג״ח במח״מ ארוך. נבדוק יחד את רגישות התיק לתרחישים שונים.״",
      "אפשר לומר: ״בהשקעות בחו״ל חשוב להביא בחשבון גם את החשיפה לדולר ואת צורכי הנזילות בשקלים.״"
    ]
    title = "תמונת מאקרו לבוקר: תשואות, אינפלציה ומדיניות ריבית"
    takeaway = "המיקוד הבוקר: להבחין בין תנועת שוק לבין נתון כלכלי חדש; לבדוק את ציפיות הריבית ביחס לתחזיות הבנקים המרכזיים ולהקפיד על מח״מ וחשיפה מטבעית מתאימים."
    status = "automatic_conditional"
else:
    title = "הסקירה לא עודכנה"
    takeaway = "קובץ נתוני השוק לא עודכן היום, ולכן לא הופקה סקירת מאקרו חדשה."
    status = "unavailable"

brief = {
    "date": date, "valid_until": datetime.combine(now.date() + timedelta(days=1), time(hour=9), tzinfo=TZ).isoformat(),
    "title": title, "status": status,
    "methodology": "אוטומציה מבוססת כללים ונתונים; אינה תחקיר עצמאי או סקירת פרסומים מלאה.",
    "sections": sections, "takeaway": takeaway, "advisor": advisor
}
Path("macro_brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

# Keep the displayed editorial snapshot in sync with the published JSON.
try:
    page = Path("index.html")
    if page.exists():
        html = page.read_text(encoding="utf-8")
        start = "<!-- EDITORIAL_MACRO_START -->"
        end = "<!-- EDITORIAL_MACRO_END -->"
        if start in html and end in html:
            json_payload = json.dumps(brief, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
            new_snapshot = start + '\n<script id="editorial-macro" type="application/json">' + json_payload + '</script>\n' + end
            prefix, rest = html.split(start, 1)
            _, suffix = rest.split(end, 1)
            page.write_text(prefix + new_snapshot + suffix, encoding="utf-8")
except Exception as error:
    print("Warning: could not embed macro note:", type(error).__name__)

print(f"Macro note {date}: {status}, {len(sections)} sections")
