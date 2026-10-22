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
israel_observations = load("israel_macro.json")
surprises = load("macro_surprises.json")
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

# Keep the daily note short: US macro, Israel macro, and investment interpretation.
# Observation dates are explicit; a daily run is not itself a fresh economic release.
try:
    updated = datetime.fromisoformat(market["updated_at"]).astimezone(TZ)
except (KeyError, ValueError, TypeError):
    updated = now - timedelta(days=9)
fresh = updated.date() == now.date() and updated <= now

def observation(key, source, max_days=100):
    row = source.get("indicators", {}).get(key, {})
    if row.get("status") != "ok" or not isinstance(row.get("value"), (int, float)):
        return None
    ref = row.get("observation_date") or row.get("observation_period")
    try:
        stamp = datetime.fromisoformat(ref + "-01" if len(ref) == 7 else ref).date()
        if not 0 <= (now.date() - stamp).days <= max_days:
            return None
    except (ValueError, TypeError):
        return None
    return row

def val(row, digits=1):
    return f'{row["value"]:.{digits}f}%' if row else None

sections = []
advisor = []
if fresh:
    cpi = observation("us_cpi", observations)
    unemployment = observation("us_unemployment", observations)
    lower = observation("us_fed_target_lower", observations, 14)
    upper = observation("us_fed_target_upper", observations, 14)
    us_text = []
    if cpi:
        us_text.append(f'אינפלציית CPI בארה״ב: {val(cpi)} (תקופה {cpi["observation_date"]})')
    if unemployment:
        us_text.append(f'אבטלה: {val(unemployment)} (תקופת ייחוס {unemployment["observation_date"]})')
    if lower and upper and lower["value"] <= upper["value"]:
        us_text.append(f'טווח ריבית הפד: {val(lower,2)}–{val(upper,2)}')
    treasury = market.get("treasury_10y", {})
    if quote_valid(treasury) and isinstance(treasury.get("change_bps"), (int, float)):
        change = treasury["change_bps"]
        context = ("עליית התשואה לעשר שנים מגדילה את הרגישות של אג״ח במח״מ ארוך." if change > 0.05
                   else "ירידת התשואה לעשר שנים עשויה לתמוך באג״ח במח״מ ארוך." if change < -0.05
                   else "תשואת אג״ח ארה״ב לעשר שנים כמעט לא השתנתה.")
    else:
        context = "כיוון התשואה הארוכה לא אומת בעדכון הנוכחי."
    sections.append(section("ארה״ב — אינפלציה, תעסוקה וריבית",
        ("; ".join(us_text) + ". " if us_text else "לא התקבלו נתוני מאקרו רשמיים עדכניים. ") +
        context + " אלה נתוני תקופות ייחוס, לא פרסומים חדשים מהבוקר; אין להסיק מהם לבדם מה גרם לתנועת המניות.",
        [{"label":"נתוני ארה״ב – FRED", "url":"https://fred.stlouisfed.org/"}]))

    il_cpi = observation("israel_cpi_yoy", israel_observations)
    il_unemployment = observation("israel_unemployment", israel_observations)
    israel_lines = []
    if il_cpi:
        israel_lines.append(f'אינפלציה שנתית: {val(il_cpi)} (תקופה {il_cpi["observation_period"]})')
    if il_unemployment:
        israel_lines.append(f'אבטלה: {val(il_unemployment,2)} (תקופה {il_unemployment["observation_period"]}; OECD מנוכה עונתיות)')
    decision_age = (now.date() - datetime(2026,10,21).date()).days
    if 0 <= decision_age <= 14:
        monetary = "ב־21.10.2026 הותיר בנק ישראל את הריבית על 3.25%; תחזית אוקטובר מציגה אינפלציה של 2.1% ב־2027. אלו החלטה ותחזית ממועד הפרסום, ולא הודעה חדשה היום."
    else:
        monetary = "לא אומתה החלטת ריבית חדשה; יש לבדוק את פרסום בנק ישראל האחרון לפני שיחה מקצועית."
    sections.append(section("ישראל — נתוני יסוד והמדיניות",
        ("; ".join(israel_lines) + ". " if israel_lines else "חלק מנתוני המאקרו אינם זמינים. ") +
        monetary + " המעקב הוא אחר אינפלציה, שער החליפין ופרמיית הסיכון.",
        [{"label":"הלמ״ס", "url":"https://www.cbs.gov.il/"},
         {"label":"בנק ישראל, החלטת 21.10", "url":"https://www.boi.org.il/publications/pressreleases/21-10-26b/"}]))

    oil = market.get("commodities", {}).get("WTI futures")
    oil_change = pct(oil)
    energy = ("עליית הנפט עשויה להוסיף לחץ לעלויות האנרגיה אם תימשך." if oil_change is not None and oil_change > 0
              else "ירידת הנפט עשויה למתן עלויות אנרגיה אם תימשך." if oil_change is not None and oil_change < 0
              else "אין שינוי נפט מאומת שאפשר לשלב בניתוח.")
    sections.append(section("המשמעות לשוק ההון",
        energy + " מבחינת אג״ח, יש לבחון את פערי התחזיות מול ציפיות הריבית בשוק ואת רגישות המח״מ. שינוי יומי במדד אינו הוכחה לגורם מאקרו מסוים.",
        [{"label":"ציטוטי שוק והתחזיות המקוריות", "url":"https://fred.stlouisfed.org/"}]))

    # Client conversation points: tie to today's verified market snapshot and
    # recent release surprises. Never assert that a macro release caused a move.
    advisor = []
    items = surprises.get("items", [])
    try:
        surprise_checked = datetime.fromisoformat(surprises.get("checked_at","")).astimezone(TZ)
        surprise_fresh = timedelta(0) <= now-surprise_checked <= timedelta(hours=36)
    except (ValueError,TypeError):
        surprise_fresh = False
    if surprise_fresh and isinstance(items,list):
        for event in items:
            if not isinstance(event,dict) or not isinstance(event.get("surprise_pp"),(int,float)):
                continue
            try:
                days=(now.date()-datetime.fromisoformat(event["released"]).date()).days
            except (KeyError,ValueError,TypeError):
                continue
            if days<0 or days>21:continue
            delta=event["surprise_pp"]
            if event.get("id")=="israel_cpi_yoy":
                advisor.append(
                    f'בישראל, האינפלציה הייתה {event["actual"]:.1f}% מול צפי {event["expected"]:.1f}% '
                    f'({delta:+.1f} נקודות אחוז). אפשר להסביר שזה עשוי להשפיע על ציפיות הריבית, '
                    'ולבדוק את רגישות האג״ח בתיק למח״מ ולשינוי בתשואות.')
            elif event.get("id")=="us_cpi":
                advisor.append(
                    f'בארה״ב, מדד המחירים היה {event["actual"]:.1f}% מול צפי {event["expected"]:.1f}% '
                    f'({delta:+.1f} נקודות אחוז). כדאי להבחין בין ציפיות לריבית הפד לבין '
                    'תנודתיות קצרת טווח במניות צמיחה ובאג״ח ארוכות.')
            elif event.get("id")=="us_unemployment":
                advisor.append(
                    f'שיעור האבטלה בארה״ב היה {event["actual"]:.1f}% מול צפי {event["expected"]:.1f}%. '
                    'זהו איתות אפשרי לגבי מצב התעסוקה, אך יש לבחון גם שכר ומשרות '
                    'לפני הסקת מסקנות על הריבית או החשיפה המנייתית.')
            if len(advisor)>=2:break
    # Third point anchored to a dated market quote rather than a generic template.
    dollar=market.get("usd_ils")
    usd_date=market.get("rate_date","")
    try:
        usd_stamp=datetime.fromisoformat(usd_date.replace("Z","+00:00")).astimezone(TZ)
        usd_fresh=timedelta(0)<=now-usd_stamp<=timedelta(days=3)
    except (ValueError,TypeError,AttributeError):
        usd_fresh=False
    if usd_fresh and isinstance(dollar,(float,int)) and market.get("status")=="ok":
        advisor.append(
            f'שער הדולר היציג האחרון: {dollar:.3f} ₪. בשיחה על חשיפה לחו״ל, '
            'כדאי לבדוק את משקל המט״ח מול צורכי הנזילות, אופק ההשקעה והגידור בתיק.')
    elif quote_valid(treasury) and isinstance(treasury.get("value"),(float,int)):
        advisor.append(
            f'תשואת אג״ח ארה״ב לעשר שנים: {treasury["value"]:.2f}%. '
            'זהו עוגן לשיחה על סיכון מח״מ, אך אינו קובע לבדו את התאמת האג״ח ללקוח.')
    fallbacks=[
        'על רקע ציפיות הריבית המשתנות, כדאי לבחון אם מח״מ האג״ח בתיק מתאים לאופק ההשקעה וליכולת הספיגה של הלקוח.',
        'במניות, יש להבחין בין תנועה יומית לבין שינוי יסודי בצמיחה וברווחיות, בלי להמליץ על שינוי חשיפה גורף.',
        'בחשיפה לחו״ל, חשוב לבדוק סיכון מטבעי, נזילות ופיזור בהתאם לצורכי הלקוח.'
    ]
    for point in fallbacks:
        if len(advisor)>=3:break
        advisor.append(point)
    advisor=advisor[:3]
    title = "סקירת מאקרו קצרה: ארה״ב, ישראל והמשמעות למשקיעים"
    takeaway = "השורה התחתונה: נתוני אינפלציה, תעסוקה וריבית משפיעים על ציפיות המדיניות המוניטרית; ההחלטות בתיק תלויות בפיזור, במח״מ ובאופק הלקוח."
    status = "automatic_conditional"
else:
    title = "סקירת המאקרו טרם עודכנה"
    takeaway = "לא התקבל קובץ נתוני שוק חדש להיום; אין להסתמך על סקירה קודמת כעל סקירת בוקר חדשה."
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
