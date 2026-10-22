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

    # Advisor-facing short client language, portfolio consequence, and a concrete review.
    advisor=[]
    if observation("israel_cpi_yoy",israel_observations):
        advisor.append({
            "title":"אג״ח: לא להמר על הורדת ריבית קרובה",
            "insight":"המדד התמתן, אבל הריבית לא ירדה בהחלטה האחרונה. לכן לא נכון להניח שמח״מ ארוך ירוויח מיד מהפחתה.",
            "client_impact":"באג״ח במח״מ חמש, עליית תשואה של נקודת אחוז עלולה לגרום בקירוב לירידת מחיר של כ־5% לפני קופונים וקמירות. זו המחשה, לא תחזית.",
            "question":"לבדוק מח״מ משוקלל, מועדי פדיון וכסף שיידרש בשנתיים הקרובות; להשוות חלופות קצרות וארוכות בהתאם לצרכים.",
            "reference":"החלטת בנק ישראל ומדד ספטמבר 2026"
        })
    if observation("us_cpi",observations):
        advisor.append({
            "title":"מניות חו״ל: הסיכון הוא גם ריכוזיות",
            "insight":"גם אם הלקוח מחזיק כמה קרנות, חלקן עשויות להחזיק את אותן מניות טכנולוגיה גדולות. גיוון שמות הקרנות אינו בהכרח גיוון סיכונים.",
            "client_impact":"אם רכיב הטכנולוגיה מתקן בחדות, כמה קרנות עלולות לרדת יחד, במיוחד כשציפיות הריבית עולות.",
            "question":"לרכז את עשר ההחזקות הגדולות מכל הקרנות, לחשב חשיפה חופפת ולבדוק התאמה לתקרת הסיכון של הלקוח.",
            "reference":"ניתוח סיכוני ריכוזיות על רקע סביבת ריבית בארה״ב"
        })
    usd_stamp=market.get("rate_date","")
    try:
        usd_age=now-datetime.fromisoformat(usd_stamp.replace("Z","+00:00")).astimezone(TZ)
    except (ValueError,TypeError,AttributeError):
        usd_age=timedelta(days=99)
    if timedelta(0)<=usd_age<=timedelta(days=3):
        advisor.append({
            "title":"מט״ח: תשואה דולרית אינה תשואה שקלית",
            "insight":"עלייה של 5% בנכס דולרי לצד היחלשות של 5% בדולר מול השקל משמעה תשואה שקלית של כ־0.25%−, לפני עלויות.",
            "client_impact":"לקוח עם הוצאות קרובות בשקלים עשוי להיות חשוף להפסד מטבעי גם כאשר ההשקעה עצמה עולה.",
            "question":"למפות הוצאות והתחייבויות לפי מטבע, לחשב חשיפה לא־מגודרת ולבחון האם גידור מתאים לאחר עלויות.",
            "reference":"המחשה חישובית והנתון היציג האחרון של בנק ישראל"
        })
    fallback=[
       {"title":"אג״ח: להבין את רגישות המח״מ","insight":"רווח ממחיר אג״ח תלוי בשינוי התשואות, לא רק בגובה הריבית הנוכחית.","client_impact":"באג״ח במח״מ חמש, שינוי תשואה של נקודת אחוז משנה את המחיר בקירוב בכ־5% בכיוון ההפוך.","question":"לחשב מח״מ והפסד תרחישי ולבחון התאמה לנזילות.","reference":"המחשה פיננסית"},
       {"title":"מניות: לבדוק חפיפה בקרנות","insight":"קרנות מדד שונות עשויות להחזיק את אותן מניות מובילות.","client_impact":"קורלציה גבוהה יכולה ליצור ריכוזיות לא מתוכננת.","question":"לחשב חפיפה ועשר החזקות גדולות בתיק המאוחד.","reference":"המחשה פיננסית"},
       {"title":"מט״ח: לבחון מטבע מול התחייבויות","insight":"תשואת ההשקעה בשקלים תלויה גם בשער החליפין.","client_impact":"לקוח שמוציא שקלים עלול לחוות תנודתיות מטבעית משמעותית.","question":"למפות הוצאות לפי מטבע ולבדוק רמת גידור רצויה.","reference":"המחשה פיננסית"}
    ]
    for row in fallback:
        if len(advisor)>=3:break
        advisor.append(row)
    advisor=advisor[:3]
    # Insight-only trading-desk note. Market quotations and macro levels are already
    # displayed elsewhere on the page. No duplicate numbers or invented events.
    global_bullets=[]
    nas=pct(market.get("indices",{}).get("Nasdaq Composite"))
    sp=pct(market.get("indices",{}).get("S&P 500"))
    if nas is not None and sp is not None:
        if nas-sp>0.35:
            global_bullets.append(
                "מניות ארה״ב: סקטור הטכנולוגיה הוביל את המדד הרחב במסחר האחרון. "
                "השאלה קדימה היא האם ההובלה תתרחב גם לסקטורים מחזוריים, "
                "או תישאר מרוכזת בחברות צמיחה גדולות.")
        elif sp-nas>0.35:
            global_bullets.append(
                "מניות ארה״ב: המדד הרחב הפגין עוצמה יחסית לטכנולוגיה. "
                "כדאי לעקוב האם מתפתחת רוטציה לסקטורים מסורתיים, "
                "בלי לקבוע שהתרחשה רוטציה על סמך יום אחד.")
        else:
            global_bullets.append(
                "מניות ארה״ב: התנועה במדדים הרחבים ובטכנולוגיה הייתה דומה. "
                "מוקד הבדיקה הוא רוחב ההשתתפות בעליות או בירידות, "
                "ולא רק ביצועי המדדים המשוקללים.")
    oil=market.get("commodities",{}).get("WTI futures",{})
    oil_change=pct(oil)
    if oil_change is not None and oil_change>1:
        global_bullets.append(
            "אנרגיה ואינפלציה: עלייה חדה יחסית בחוזי הנפט עלולה להקשות "
            "על ההתכנסות ליעדי האינפלציה אם תתמשך. "
            "השלכה אפשרית: תשואות אג״ח רגישות יותר לתמחור ריבית לאורך זמן.")
    elif oil_change is not None and oil_change< -1:
        global_bullets.append(
            "אנרגיה: ירידה חדה יחסית בנפט עשויה למתן לחצי מחירים, "
            "אך חשוב להבחין בין ירידת מחירים בגלל שיפור בהיצע "
            "לבין ירידה שמקורה בחולשה בביקוש העולמי.")
    if cpi and unemployment:
        global_bullets.append(
            "לקראת החלטת הפד: המתח המרכזי הוא בין אינפלציה שמגבילה "
            "מרחב להפחתות לבין סימני התרופפות בתעסוקה. "
            "דגש מיוחד לפרסומי ליבה, שכר ורכיבי התעסוקה, "
            "ולשאלה מה כבר מגולם בחוזים.")
    if not global_bullets:
        global_bullets=["לא זוהתה התפתחות חדשה ומאומתת שניתן לנתח ללא חזרה על טבלת הנתונים."]

    israel_bullets=[]
    il35=pct(market.get("indices",{}).get("TA-35"))
    il125=pct(market.get("indices",{}).get("TA-125"))
    if il35 is not None and il125 is not None:
        if il35<0 and il125<0:
            israel_bullets.append(
                "מניות ישראל: החולשה במסחר האחרון הייתה משותפת לשני המדדים המובילים. "
                "כדי לבחון אם מדובר במגמה יש לבדוק רוחב ירידות, מחזורי מסחר "
                "והשפעת הבנקים והנדל״ן, ולא רק את מדדי הכותרת.")
        elif il35>0 and il125>0:
            israel_bullets.append(
                "מניות ישראל: העליות הופיעו בשני המדדים המובילים. "
                "המבחן להמשכיות הוא השתתפות ענפית רחבה "
                "והאם פרמיית הסיכון והציפיות לריבית תומכות בתמחור.")
        else:
            israel_bullets.append(
                "מניות ישראל: התמונה במדדים מעורבת. "
                "נדרשת בדיקת תרומת הסקטורים והחברות הכבדות לפני הסקת מסקנה על כיוון השוק.")
    if 0<=decision_age<=14:
        israel_bullets.append(
            "מדיניות בנק ישראל: על אף התמתנות האינפלציה, "
            "ההחלטה האחרונה מדגישה שאין קשר אוטומטי בין מדד נמוך להפחתה מיידית. "
            "מוקדי המעקב הם השקל, סיכוני ההיצע ופרמיית הסיכון.")
    if not israel_bullets:
        israel_bullets=["אין כרגע אירוע ישראלי חדש ומאומת שמוסיף מידע מעבר למדדים המוצגים באתר."]

    forward_bullets=[
        "גלובלי: התמדה במחירי האנרגיה לצד חולשה בתעסוקה תיצור דילמה לפד. "
        "מומלץ לעקוב אחר שינוי בציפיות לריבית ובתשואות הארוכות ולא להסיק מנתון בודד.",
        "ישראל: כיוון האג״ח המקומיות יושפע משילוב של תוואי הריבית, "
        "האינפלציה הגלומה, מצב התקציב והשקל. יש להבחין בין תרחיש בסיס לסיכוני קיצון."
    ]
    sections=[
        {"heading":"גלובלי","bullets":global_bullets[:3],
         "sources":[{"label":"FRED","url":"https://fred.stlouisfed.org/"}]},
        {"heading":"ישראל","bullets":israel_bullets[:2],
         "sources":[{"label":"בנק ישראל","url":"https://www.boi.org.il/"}]},
        {"heading":"כיוון להמשך","bullets":forward_bullets,
         "sources":[]}
    ]
    # Refresh every morning from dated coverage, not a hard-coded historical news digest.
    # Political/security/election developments get their own source-backed Israel context.
    approved=("ביזפורטל","כלכליסט","calcalist","גלובס","globes","reuters",
              "bloomberg","cnbc","financial times","themarker","stonex","הארץ","ynet")
    def recent_stories(region,limit=3):
        selected=[]
        for entry in (news.get("israel_focus",[]) if region=="ישראל" else news.get("items",[])):
            if not isinstance(entry,dict):continue
            if region!="ישראל" and entry.get("region")!="חו״ל":continue
            src=entry.get("source","")
            if not any(name in src.lower() for name in approved):continue
            try: published=datetime.fromisoformat(entry["published_at"]).astimezone(TZ)
            except (KeyError,ValueError,TypeError):continue
            if not timedelta(0)<=now-published<=timedelta(hours=36):continue
            link=entry.get("link","")
            headline=entry.get("title","").rsplit(" - ",1)[0].strip()
            if not headline or not isinstance(link,str) or not link.startswith("https://"):continue
            selected.append({"title":headline,"source":src,"url":link,
                             "published_at":published.isoformat(),
                             "region":entry.get("region","")})
        # Add verified, relevant general business coverage only when less than three
        if region=="ישראל" and len(selected)<limit:
            for entry in news.get("items",[]):
                if not isinstance(entry,dict) or entry.get("region")!="ישראל":continue
                src=entry.get("source","")
                if not any(name in src.lower() for name in approved):continue
                try: published=datetime.fromisoformat(entry["published_at"]).astimezone(TZ)
                except (KeyError,ValueError,TypeError):continue
                if not timedelta(0)<=now-published<=timedelta(hours=36):continue
                headline=entry.get("title","").rsplit(" - ",1)[0].strip()
                link=entry.get("link","")
                if headline and isinstance(link,str) and link.startswith("https://"):
                    selected.append({"title":headline,"source":src,"url":link,
                                     "published_at":published.isoformat(),"region":"שוק"})
        seen=set()
        ordered=[]
        priority={"בחירות":0,"ביטחון":1,"פיסקלי":2,"שוק":3}
        selected.sort(key=lambda x:(priority.get(x["region"],4),-datetime.fromisoformat(x["published_at"]).timestamp()))
        for entry in selected:
            key=entry["title"].casefold()[:90]
            if key in seen:continue
            seen.add(key);ordered.append(entry)
            if len(ordered)>=limit:break
        return ordered

    def implication(topic):
        if topic=="בחירות":
            return ("המשמעות: הרכב הממשלה והחלטותיה לגבי תקציב ומסים עלולים "
                    "לשנות את מסלול הגירעון, את פרמיית הסיכון ואת תשואות האג״ח.")
        if topic=="ביטחון":
            return ("המשמעות: שינוי בעצימות הלחימה עלול להשפיע על הוצאות ביטחון, "
                    "מגבלות היצע, מחירי אנרגיה והשקל. אין להסיק תגובת שוק בלי נתוני מסחר.")
        if topic=="פיסקלי":
            return ("המשמעות: גירעון גבוה מהמתוכנן עלול להגביר צורכי גיוס ממשלתיים "
                    "ולהשפיע על תשואות ומרווחי אשראי.")
        return ("המשמעות לתיק תלויה במידה שבה האירוע משנה ציפיות ריבית, "
                "רווחיות או פרמיית סיכון, ולא רק בכותרת.")

    israel_stories=recent_stories("ישראל",3)
    israel_bullets=[]
    israel_sources=[]
    covered=set()
    for story in israel_stories:
        topic=story["region"]
        covered.add(topic)
        israel_bullets.append(
            f'{topic if topic!="שוק" else "שוק מקומי"} — לפי {story["source"]}: '
            f'{story["title"]}. '+implication(topic))
        israel_sources.append({"label":story["source"]+" · "+topic,"url":story["url"]})

    # A new official bank risk assessment may supply non-news background for up to
    # 14 days. Mark as last published assessment; never pass it off as new today.
    bank_age=(now.date()-datetime(2026,10,21).date()).days
    if 0<=bank_age<=14:
        if "בחירות" not in covered:
            israel_bullets.append(
                "בחירות — בהערכת בנק ישראל מ־21.10.2026: סיכון לאי־הכרעה "
                "פוליטית לאחר הבחירות והחלטות ממשלה בנושא התקציב. "
                "השפעה אפשרית: תנודתיות בפרמיית הסיכון ובשוק האג״ח; "
                "זו הערכת סיכון מתוארכת ולא ידיעה חדשה מהיום.")
        if "ביטחון" not in covered:
            israel_bullets.append(
                "מצב ביטחוני — על פי תחזית בנק ישראל מ־21.10.2026: "
                "התעצמות לחימה מחודשת עשויה להגדיל גיוס מילואים והוצאות ביטחון, "
                "להחריף מגבלות היצע ולהפעיל לחץ על האינפלציה. "
                "התחזית מניחה עצימות לחימה נמוכה יחסית; זו הנחת תרחיש, לא אימות לאירוע חדש.")
        if "פיסקלי" not in covered:
            israel_bullets.append(
                "תקציב הביטחון והגירעון — תחזית בנק ישראל מ־21.10.2026 "
                "מציגה גירעון של 4.4% תוצר ב־2026 ושל 4.6% ב־2027, "
                "בהנחה שהוצאות הביטחון לא יחרגו מהרזרבה בתקציב. "
                "חריגה עשויה להגדיל את צורכי המימון ולהכביד על תשואות האג״ח.")
        israel_sources.extend([
            {"label":"בנק ישראל — החלטת 21.10","url":"https://www.boi.org.il/publications/pressreleases/21-10-26b/"},
            {"label":"בנק ישראל — תחזית סיכונים","url":"https://www.boi.org.il/publications/pressreleases/21-10-26a/"}])
    if not israel_bullets:
        israel_bullets=["לא אותרו היום התפתחויות מאומתות בבחירות, בביטחון או בתקציב "
                        "ממקורות החדשות המחוברים. אין להציג מידע ישן כאירוע חדש."]

    world_stories=recent_stories("חו״ל",3)
    world=[]
    world_sources=[]
    for story in world_stories[:3]:
        world.append(f'לפי {story["source"]}: {story["title"]}. '
                     "זו כותרת מתוארכת; לפני ייחוס תנועת מדד לאירוע נדרש אימות נוסף. "
                     "ההשלכות האפשריות הן דרך רווחיות החברות, ציפיות הריבית או מחירי האנרגיה, בהתאם לאירוע.")
        world_sources.append({"label":story["source"],"url":story["url"]})
    if not world:
        world=["לא זוהה דיווח שוק גלובלי מאומת מהיממה האחרונה במקורות החדשות המחוברים."]

    sections=[
        {"heading":"ישראל — בחירות, ביטחון ותקציב","bullets":israel_bullets[:6],
         "sources":israel_sources[:6]},
        {"heading":"גלובלי — התפתחויות מרכזיות","bullets":world,
         "sources":world_sources},
        {"heading":"כיוון להמשך","bullets":[
            "בישראל: לבדוק אם חדשות הבחירות והביטחון משנות בפועל את השקל, "
            "את פרמיית הסיכון, את תשואות האג״ח ואת ציפיות האינפלציה.",
            "בעולם: להתמקד בהפתעות בנתוני המאקרו, בדוחות החברות "
            "ובתמחור מסלול הריבית — ולא להסיק כיוון חד־משמעי מהכותרות."
        ],"sources":[]}
    ]
    title = "סקירת בוקר מתעדכנת: ישראל, גלובלי והשפעות השוק"
    takeaway = "עדכון יומי: בחירות, ביטחון, תקציב, מאקרו ותמחור סיכונים. ידיעות חדשות מסומנות בנפרד מהערכות סיכון קודמות."
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
