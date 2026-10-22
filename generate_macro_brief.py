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

    # Three usable conversations: insight, client impact, concrete diagnostic.
    # Keep them tied to dated validated observations and never recommend a trade.
    advisor=[]
    il_cpi=observation("israel_cpi_yoy",israel_observations)
    us_cpi=observation("us_cpi",observations)
    fed_lo=observation("us_fed_target_lower",observations,14)
    fed_hi=observation("us_fed_target_upper",observations,14)
    if il_cpi:
        advisor.append({
            "title":"האג״ח בתיק: האם ההצמדה עדיין מתאימה?",
            "insight":"ההתמתנות באינפלציה בישראל אינה מבטיחה הורדת ריבית מיידית. אם התשואות ישתנו, מח״מ ארוך יהיה רגיש יותר, בעוד הגנות הצמדה עשויות להתנהג אחרת.",
            "client_impact":"לקוח עם צורך בכסף בשנתיים הקרובות חשוף אחרת מלקוח שמשקיע לעשור; גם משקל הצמודות מול השקליות משנה.",
            "question":"מהו סכום המשיכה הצפוי בשנתיים הקרובות, ומה שיעור האג״ח הארוכות והצמודות בתיק?",
            "reference":"נתוני הלמ״ס ובנק ישראל; מדד "+il_cpi["observation_period"]
        })
    if us_cpi:
        advisor.append({
            "title":"חשיפה למניות ארה״ב: האם התיק מרוכז בצמיחה?",
            "insight":"אינפלציה עיקשת בארה״ב עשויה להקשות על הפחתות ריבית. מניות שתמחורן נשען על רווחים עתידיים רגישות לעיתים יותר לעליית שיעור ההיוון.",
            "client_impact":"גם תיק שעוקב אחרי מדד רחב עשוי להכיל חשיפה מרוכזת לענקיות טכנולוגיה, בלי שהלקוח מודע לריכוזיות.",
            "question":"כמה מהחלק המנייתי שלך חשוף לחברות הטכנולוגיה הגדולות, והאם ירידה חדה בענף תשנה את הצורך שלך בנזילות?",
            "reference":"CPI ארה״ב, תקופת "+us_cpi["observation_date"][:7]
        })
    dollar=market.get("usd_ils")
    rate_stamp=market.get("rate_date","")
    try:
        age=now-datetime.fromisoformat(rate_stamp.replace("Z","+00:00")).astimezone(TZ)
    except (ValueError,TypeError,AttributeError):
        age=timedelta(days=99)
    if isinstance(dollar,(int,float)) and timedelta(0)<=age<=timedelta(days=3):
        advisor.append({
            "title":"השקעות חו״ל: לזהות סיכון מטבעי סמוי",
            "insight":"תשואה חיובית בדולר עלולה להישחק בשקלים כשהמטבע האמריקאי נחלש. המטבע של הקרן או הבורסה שבה נסחרת אינו בהכרח מטבע החשיפה הכלכלית.",
            "client_impact":"לקוח שהוצאותיו הקרובות בשקלים עשוי להזדקק לפיזור שונה מלקוח שיש לו התחייבויות בדולרים.",
            "question":"באיזה מטבע יהיו ההוצאות הגדולות שלך בשלוש השנים הקרובות, ומה שיעור החשיפה הלא־מגודרת למט״ח?",
            "reference":"שער יציג בנק ישראל, "+rate_stamp[:10]
        })
    fallbacks=[
        {"title":"סיכון מח״מ","insight":"עליית תשואות מורידה את מחירן של אג״ח קיימות; הרגישות עולה עם המח״מ.","client_impact":"צרכי נזילות קצרים עלולים להתנגש עם החזקה במח״מ ארוך.","question":"מתי צפויה המשיכה הבאה ומה המח״מ המשוקלל בתיק?","reference":"ניתוח עקרוני"},
        {"title":"ריכוז מנייתי","insight":"מדד רחב עשוי לכלול ריכוז גבוה בחברות ענק.","client_impact":"פיזור בין קרנות שונות אינו מבטיח פיזור בחשיפה הכלכלית.","question":"מהו משקל עשר המניות הגדולות בתיק מכל הקרנות יחד?","reference":"ניתוח עקרוני"},
        {"title":"חשיפה מטבעית","insight":"תנודות מט״ח משפיעות על התשואה במונחי שקל.","client_impact":"פער בין מטבע ההשקעה למטבע ההוצאות מוסיף אי־ודאות.","question":"איזה חלק מההוצאות העתידיות שלך נקוב בשקלים ומהי החשיפה הלא־מגודרת?","reference":"ניתוח עקרוני"}
    ]
    for item in fallbacks:
        if len(advisor)>=3:break
        if not any(x["title"]==item["title"] for x in advisor):advisor.append(item)
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
    # Real, dated business headlines may add meaning beyond market quote cards.
    # Headlines are identified as publisher reports and never independently
    # treated as verified explanations for market price changes.
    def sourced_headlines(region, limit=2):
        allowed=("ביזפורטל","כלכליסט","calcalist","גלובס","globes",
                 "reuters","bloomberg","cnbc","financial times","themarker")
        picks=[]
        for story in news.get("items",[]):
            if not isinstance(story,dict) or story.get("region")!=region:
                continue
            title=story.get("title","")
            pub=story.get("source","")
            if not any(x in pub.lower() for x in allowed) or not title:
                continue
            try:
                ts=datetime.fromisoformat(story["published_at"]).astimezone(TZ)
            except (ValueError,KeyError,TypeError):
                continue
            if not timedelta(0)<=now-ts<=timedelta(hours=36):
                continue
            url=story.get("link","")
            if not isinstance(url,str) or not url.startswith("https://"):
                continue
            picks.append((title.rsplit(" - ",1)[0].strip(),pub,url))
            if len(picks)>=limit:break
        return picks

    def event_context(title):
        t=title.lower()
        if any(k in t for k in ("נפט","ברנט","oil","crude","energy")):
            return ("למשקיעים: שינוי מתמשך במחירי האנרגיה עשוי לשנות את "
                    "ציפיות האינפלציה, מרווחי חברות תעופה ותעשייה "
                    "ואת הרווחיות בענפי האנרגיה. זו השלכה אפשרית, "
                    "לא קביעה על סיבת תנועת המדדים.")
        if any(k in t for k in ("הסלמה","ביטחונ","איראן","war","geopolit")):
            return ("למשקיעים: הסיכון הגיאופוליטי עשוי להשפיע על פרמיית הסיכון, "
                    "על השקל ועל תשואות אג״ח ממשלתיות. חשוב לבדוק אם השינוי "
                    "בציפיות אכן מגולם במחירים, ולא להסיק מכותרת בלבד.")
        if any(k in t for k in ("ריבית","בנק ישראל","fed","federal reserve","treasury")):
            return ("למשקיעים: לשים לב לפער בין ההצהרות לתוואי הריבית "
                    "המגולם בשוק; אג״ח במח״מ ארוך ומניות צמיחה רגישות "
                    "במיוחד לתמחור התשואות.")
        if any(k in t for k in ("בנקים","ביטוח","נדל","bank","financial")):
            return ("למשקיעים: המשמעות לענף תלויה במרווחי מימון, "
                    "בעלות האשראי ובריבית; נדרשת בדיקת ביצועי הענף "
                    "ומכפילים לפני מסקנה על אפיק השקעה.")
        if any(k in t for k in ("מניות","בורסה","nasdaq","wall street","stocks","shares")):
            return ("למשקיעים: כדאי להפריד בין שינוי חד בחברה בודדת "
                    "לבין מגמה רוחבית, ולבדוק ריכוזיות בתיק לפני תגובה.")
        return "משמעות אפשרית לתיק תיבחן לאחר אימות פרטי הכתבה ונתוני השוק."

    source_sections=[]
    for region,heading in (("חו״ל","גלובלי"),("ישראל","ישראל")):
        stories=sourced_headlines(region,2)
        if stories:
            source_sections.append({
                "heading":heading,
                "bullets":[f'לפי דיווח {pub}: {headline}. {event_context(headline)}'
                           for headline,pub,url in stories],
                "sources":[{"label":pub,"url":url} for _,pub,url in stories]
            })
        else:
            existing=next((section for section in sections if section["heading"]==heading),None)
            if existing:
                source_sections.append(existing)
    outlook=next((section for section in sections if section["heading"]=="כיוון להמשך"),None)
    if outlook:
        source_sections.append(outlook)
    if source_sections:sections=source_sections
    title = "האירועים שמשפיעים על השווקים · מה חשוב לדעת"
    takeaway = "למעקב: רוחב השוק, מחירי האנרגיה וציפיות הריבית. פרשנות מותנית, לא תיאור של גורם שוק שלא אומת."
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
