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
    us_analysis = (
        "מבחינת מדיניות: ריבית הפד משקפת את האיזון בין יציבות מחירים לתעסוקה. "
        "אינפלציה עיקשת עלולה לצמצם את מרחב ההפחתות; היחלשות מתמשכת בתעסוקה יכולה לפעול בכיוון ההפוך. "
        "לא די בנתון בודד כדי לגזור שינוי במסלול הריבית. "
        "בשוק האג״ח חשוב להבחין בין שינוי בריבית הצפויה לטווח קצר לבין פרמיית הטווח והתשואה לעשר שנים. "
    )
    us_quotes=[]
    for key,name in (("S&P 500","S&P 500"),("Nasdaq Composite","Nasdaq"),("Dow Jones","Dow Jones")):
        move=pct(market.get("indices",{}).get(key))
        if move is not None:
            us_quotes.append(f'{name} {move:+.2f}%')
    if us_quotes:
        us_analysis += ("בסגירה האמריקאית האחרונה: "+", ".join(us_quotes)+
            ". אלה ביצועי המדדים, לא הוכחה שסעיף המאקרו הוא שגרם להם. ")
    us_analysis += (
        context+" המשמעות לתיק: בחינת מח״מ, משקל מניות צמיחה וחשיפה לדולר בנפרד, "
        "תוך בדיקת תמחור וציפיות מגולמות בשוק. "
        "תאריכי נתוני התעסוקה והמחירים הם תקופות הייחוס, ולא בהכרח מועד הפרסום."
    )
    sections.append(section("ארה״ב — מה אומרים הנתונים על הפד והשווקים",
        ("תמונת הנתונים: "+"; ".join(us_text)+". " if us_text else "אין סדרת נתונים מלאה לבחינה. ")+us_analysis,
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
    il_moves=[]
    for key,label in (("TA-35","ת״א־35"),("TA-125","ת״א־125")):
        change=pct(market.get("indices",{}).get(key))
        if change is not None:
            il_moves.append(f'{label} {change:+.2f}%')
    il_analysis=(
        "הקריאה המאקרו־פיננסית: התמתנות האינפלציה יכולה לאפשר מדיניות מרחיבה יותר, "
        "אבל החלטת הריבית מושפעת גם משער השקל, מגירעון, מפרמיית הסיכון ומקצב הפעילות. "
        "באפיק השקלי יש להפריד בין אג״ח צמודות למדד לבין אג״ח לא־צמודות: הן חשופות באופן שונה "
        "להפתעות באינפלציה ולשינוי בציפיות הריבית. "
    )
    if il_moves:
        il_analysis += "במסחר המקומי: "+", ".join(il_moves)+". אלו ביצועי מדדים, לא ייחוס סיבתי לנתון בודד. "
    il_analysis += (
        "לשיחה עם לקוח: כדאי לבחון את שילוב ההצמדה, המח״מ והחשיפה המטבעית "
        "ביחס לצורכי הנזילות והיכולת לשאת תנודתיות."
    )
    sections.append(section("ישראל — ריבית, אינפלציה ורגישות התיק",
        ("תמונת הנתונים: "+"; ".join(israel_lines)+". " if israel_lines else "חלק מנתוני המאקרו אינם זמינים. ")+
        monetary+" "+il_analysis,
        [{"label":"הלמ״ס", "url":"https://www.cbs.gov.il/"},
         {"label":"בנק ישראל, החלטת 21.10", "url":"https://www.boi.org.il/publications/pressreleases/21-10-26b/"}]))

    oil = market.get("commodities", {}).get("WTI futures")
    oil_change = pct(oil)
    energy = ("עליית הנפט עשויה להוסיף לחץ לעלויות האנרגיה אם תימשך." if oil_change is not None and oil_change > 0
              else "ירידת הנפט עשויה למתן עלויות אנרגיה אם תימשך." if oil_change is not None and oil_change < 0
              else "אין שינוי נפט מאומת שאפשר לשלב בניתוח.")
    risk_view=(
        energy+
        " התרחיש החיובי לנכסי סיכון הוא התכנסות האינפלציה בלי פגיעה חדה בתעסוקה וברווחי החברות. "
        "התרחיש השלילי הוא שילוב של אינפלציה דביקה והיחלשות צמיחה, המקשה על הבנקים המרכזיים להפחית ריבית. "
        "לפני שינוי בתיק יש לבדוק שלושה דברים: האם ההפתעה כבר מגולמת בתמחור; "
        "כמה רגיש כל אפיק לתשואות ולמטבע; והאם השינוי מתאים לאופק הלקוח ולאסטרטגיית הפיזור. "
        "מה לעקוב בפרסום הבא: אינפלציית ליבה, שכר, נתוני תעסוקה וציפיות אינפלציה."
    )
    sections.append(section("תרחישים למשקיעים — מניות, אג״ח ומט״ח",
        risk_view,[{"label":"נתוני ריבית ואינפלציה – FRED", "url":"https://fred.stlouisfed.org/"}]))

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
    # Trading-desk format: succinct, event/data-led bullets, then a forward view.
    # No unsourced claim that news caused an index move.
    def movement(code, hebrew):
        item=market.get("indices",{}).get(code,{})
        change=pct(item)
        return f'{hebrew} {change:+.2f}%' if change is not None else None

    america=[movement("S&P 500","S&P 500"),
             movement("Nasdaq Composite","Nasdaq"),
             movement("Dow Jones","Dow Jones")]
    america=[v for v in america if v]
    israel_market=[movement("TA-35","ת״א־35"),movement("TA-125","ת״א־125")]
    israel_market=[v for v in israel_market if v]
    global_bullets=[]
    if america:
        global_bullets.append("מסחר בארה״ב: בסגירה האחרונה "+", ".join(america)+
          ". מדובר בביצועי שוק, ללא קביעה מה גרם לתנועה.")
    if cpi and unemployment:
        global_bullets.append(
           f'מאקרו אמריקאי: CPI שנתי {val(cpi)} ואבטלה {val(unemployment)} '
           f'(נתוני תקופת {cpi["observation_date"][:7]}). '
           'אינפלציה עיקשת והאטה בתעסוקה יוצרים משיכה בכיוונים שונים לציפיות הריבית.')
    elif lower and upper:
        global_bullets.append(
           f'מדיניות מוניטרית: טווח הריבית {val(lower,2)}–{val(upper,2)}. '
           'המסלול קדימה תלוי בעיקר באינפלציית ליבה, שכר ותעסוקה.')
    oil=market.get("commodities",{}).get("WTI futures",{})
    if quote_valid(oil) and isinstance(oil.get("change_percent"),(int,float)):
        global_bullets.append(
           f'אנרגיה: WTI {oil["change_percent"]:+.2f}% בציטוט האחרון. '
           'המשך התייקרות האנרגיה עלול לעכב ירידת אינפלציה ולחזק אי־ודאות בריבית.')
    if not global_bullets:
        global_bullets=["לא התקבלו הבוקר נתונים מאומתים המספיקים לסקירת מסחר גלובלית."]

    israel_bullets=[]
    if israel_market:
        israel_bullets.append("מניות בישראל: "+", ".join(israel_market)+
          " במסחר האחרון; אין להסיק מתנועת המדדים לבדה על סיבת השינוי.")
    if il_cpi:
        israel_bullets.append(
           f'אינפלציה בישראל: {val(il_cpi)} בשנה (תקופת {il_cpi["observation_period"]}). '
           'הנתון חשוב לציפיות הריבית ולפער בין אג״ח שקליות לצמודות.')
    if 0<=decision_age<=14:
        israel_bullets.append(
           'בנק ישראל: בהחלטת 21.10.2026 נשמרה ריבית 3.25%. '
           'המשך המדיניות תלוי גם בפרמיית הסיכון, בשקל ובמחירי האנרגיה.')
    if not israel_bullets:
        israel_bullets=["נתוני ישראל העדכניים אינם זמינים לאימות היום."]

    forward_bullets=[
        "גלובלי: אם לחצי האנרגיה והאינפלציה יימשכו, תשואות אג״ח עלולות להישאר גבוהות "
        "גם אם הצמיחה תתמתן. המבחן הבא יהיה פרסומי המחירים והתעסוקה.",
        "ישראל: ירידה עקבית באינפלציה עשויה לתמוך בהפחתת ריבית, "
        "אך התפתחויות ביטחוניות, שער החליפין ועלויות מימון ממשלתיות עשויים לשנות את התמונה.",
        "בתיקים: לבחון רגישות מח״מ, חשיפה מטבעית ואיכות האשראי. "
        "זו הערכת סיכונים מותנית, לא תחזית ודאית או המלצת השקעה."
    ]
    sections=[
        {"heading":"גלובלי", "bullets":global_bullets[:3],
         "sources":[{"label":"נתוני שוק ומאקרו","url":"https://fred.stlouisfed.org/"}]},
        {"heading":"ישראל", "bullets":israel_bullets[:3],
         "sources":[{"label":"בנק ישראל","url":"https://www.boi.org.il/"},
                    {"label":"הלמ״ס","url":"https://www.cbs.gov.il/"}]},
        {"heading":"כיוון להמשך", "bullets":forward_bullets,
         "sources":[]}
    ]
    title = "סקירת בוקר | אירועים, שווקים וכיוון להמשך"
    takeaway = "עיקר המעקב: אנרגיה, אינפלציה, תעסוקה וציפיות הריבית. הערכות קדימה הן תרחישים ולא עובדות."
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
