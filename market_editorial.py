"""Daily investment-adviser editorial: numeric market evidence first, headlines second.

No model/API charges. Never allege that a headline caused a market move; distinguish
last available trading session from today's editorial creation time.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ=ZoneInfo("Asia/Jerusalem")


def build(market, news, now):
    indices=market.get("indices") or {}
    commodities=market.get("commodities") or {}
    treasury=market.get("treasury_10y") or {}

    def verified(record):
        if not isinstance(record,dict) or record.get("status")!="ok":
            return False
        ts=record.get("market_time")
        if not isinstance(ts,(int,float)):return False
        age=now-datetime.fromtimestamp(ts,TZ)
        return timedelta(0)<=age<=timedelta(days=4)

    def move(row):
        if not verified(row):return None
        v=row.get("change_percent")
        return float(v) if isinstance(v,(int,float)) else None

    def number(v):
        return f"{v:+.2f}%" .replace("+","+")

    def session(row):
        if not verified(row):return None
        return datetime.fromtimestamp(row["market_time"],TZ).strftime("%d.%m.%Y")

    sp=indices.get("S&P 500",{})
    nas=indices.get("Nasdaq Composite",{})
    dow=indices.get("Dow Jones",{})
    ta35=indices.get("TA-35",{})
    ta125=indices.get("TA-125",{})
    oil=commodities.get("WTI futures",{})
    gold=commodities.get("Gold futures",{})
    a,b,c=move(sp),move(nas),move(dow)
    il35,il125=move(ta35),move(ta125)
    energy=move(oil)
    safe_t=verified(treasury) and isinstance(treasury.get("change_bps"),(int,float))
    tchange=float(treasury["change_bps"]) if safe_t else None
    tv=treasury.get("value") if safe_t else None
    sections=[]
    points=[]

    def section(title,bullets,refs=None):
        if bullets:
            sections.append({"heading":title,"bullets":bullets,"sources":refs or []})

    def point(title,fact,impact,client_action,ref_date):
        points.append({"title":title,"insight":fact,"client_impact":impact,
                       "question":client_action,"reference":"נתוני מסחר מאומתים · "+ref_date})

    if a is not None and b is not None and c is not None:
        date=session(sp)
        common=f"בסגירה האמריקאית האחרונה ({date}): אס אנד פי 500 {number(a)}, נאסדק {number(b)}, ודאו ג׳ונס {number(c)}."
        if b-c>=0.6:
            insight="הפער בין הנאסדק לדאו מלמד שהטכנולוגיה הפגינה עמידות יחסית למניות התעשייה והחברות המסורתיות; זו השוואת ביצועים, לא הסבר סיבתי לתנועה."
            check="לבדוק האם החזקות הלקוח מרוכזות בחברות צמיחה גדולות למרות פיזור בין מספר קרנות."
        elif c-b>=0.6:
            insight="הדאו הפגין עוצמה יחסית לנאסדק; חשוב לבדוק את הרכב המדדים לפני שמסיקים שמתרחשת רוטציה ענפית."
            check="להשוות משקל של מניות ערך ותעשייה מול חברות צמיחה, ולא להסתמך על מדד בודד."
        elif a<0 and b<0 and c<0:
            insight="שלושת המדדים ירדו. הבדלי העוצמה ביניהם חשובים להבנת סוג החשיפה שנפגעה, אך אינם מזהים לבדם את הגורם לירידות."
            check="לבדוק חלוקה ענפית וחשיפות חופפות למדדים האמריקאיים."
        elif a>0 and b>0 and c>0:
            insight="שלושת המדדים עלו, אך העלייה במדדים אינה מלמדת לבדה על רוחב העליות בשוק."
            check="לבחון ריכוזיות, תשואת התיק במטבע הלקוח ופיזור בין סקטורים."
        else:
            insight="התמונה בין מדדי ארצות הברית מעורבת; יש להבחין בין ענפים ומדדים ולא להתייחס לוול סטריט כיחידה אחת."
            check="לבדוק חשיפה ענפית במקום להסיק כיוון מתנועה של מדד אחד."
        section("וול סטריט — מה עשה השוק בפועל",[common+" "+insight])
        point("וול סטריט: לבדוק הרכב וריכוזיות",common,
              insight+" המשמעות ללקוח תלויה בהרכב האחזקות ולא רק בכותרת המדד.",check,date)

    if energy is not None:
        date=session(oil)
        descriptor="זינק" if energy>=2 else "עלה" if energy>0 else "ירד בחדות" if energy<=-2 else "ירד"
        lead=f"בחוזי הנפט מסוג WTI, השינוי בסגירה האחרונה ({date}) היה {number(energy)} — הנפט {descriptor}."
        if energy>1:
            impact="עלייה משמעותית בנפט עלולה להגדיל עלויות לתעופה ותעשייה ולהקשות על ירידת האינפלציה, אם תימשך. חברות הפקה עשויות להיות מושפעות אחרת; לא ניתן לדעת מה גרם לעלייה מנתוני המחיר לבדם."
            check="לבדוק חשיפה לחברות תעופה, אנרגיה ותעשייה, וגם רגישות של אג״ח ארוכות לציפיות אינפלציה."
        elif energy< -1:
            impact="ירידה בנפט עשויה להקל על עלויות דלק ואינפלציה, אך יכולה גם לשקף חשש מביקוש חלש; המחיר לבדו אינו מזהה את הסיבה."
            check="לבדוק חשיפה למפיקות אנרגיה ולחברות עתירות דלק לצד ציפיות אינפלציה."
        else:
            impact="תנודת הנפט אינה גדולה במיוחד בסגירה האחרונה, ולכן אינה לבדה מוקד הסקירה."
            check="לעקוב אחר שינוי מצטבר בנפט ולא לבצע שינוי תיק על סמך יום בודד."
        section("אנרגיה ואינפלציה — התנועה שחשובה לתמחור",[lead+" "+impact])
        if abs(energy)>=1:
            point("נפט: השפעה על רווחיות ואינפלציה",lead,impact,check,date)

    if il35 is not None and il125 is not None:
        date=session(ta35)
        lead=f"בסגירה האחרונה בבורסה בתל אביב ({date}): ת״א־35 {number(il35)} ות״א־125 {number(il125)}."
        if il35<0 and il125<0:
            impact="שני המדדים ירדו. זו עדות לחולשה במדדים המרכזיים, אך לא ניתן לקבוע אם ביטחון, ריבית או מניות גדולות גרמו לכך בלי בדיקת ענפים ומחזורי מסחר."
        elif il35>0 and il125>0:
            impact="שני המדדים עלו. יש לבדוק אם העליות רחבות או נובעות ממספר מניות בעלות משקל גבוה."
        else:
            impact="התמונה המקומית מעורבת, ולכן כדאי להבחין בין חברות גדולות לשוק הרחב."
        section("ישראל — ביצועי הבורסה האחרונים",[lead+" "+impact])
        point("תל אביב: סיכון מקומי ומבנה התיק",lead,
              impact+" רגישות התיק לשקל ולאג״ח ממשלתיות תלויה גם באופי החשיפה.",
              "לבדוק ריכוזיות בישראל, חשיפה לבנקים ולנדל״ן, הצמדה ומטבע התיק.",date)

    if safe_t:
        date=session(treasury)
        direction="עלתה" if tchange>0 else "ירדה" if tchange<0 else "כמעט לא השתנתה"
        lead=f"תשואת אג״ח ממשלת ארצות הברית לעשר שנים עמדה על {float(tv):.2f}% ({date}) ו{direction} ב־{abs(tchange):.1f} נקודות בסיס."
        impact=("עליית התשואה מגדילה את הלחץ על מחירי אג״ח קיימות במח״מ ארוך, בכפוף לשינויים נוספים בעקום."
                if tchange>0.1 else
                "ירידת התשואה עשויה לתמוך במחירי אג״ח קיימות במח״מ ארוך, בכפוף לשינויים נוספים בעקום."
                if tchange< -0.1 else
                "התזוזה הקטנה בתשואה אינה מספיקה כשלעצמה כדי להסיק שינוי משמעותי בתוואי הריבית.")
        section("אג״ח וריבית — מה השתנה בתשואה הארוכה",[lead+" "+impact])
        if abs(tchange)>=2:
            point("אג״ח: לבחון מח״מ ולא רק ריבית בנק מרכזי",lead,
                  impact,"להשוות מח״מ תיק האג״ח ורגישות לעליית תשואות, לצד חשיפה למטבע.",date)

    # Supplement with at most one dated, directly market-relevant headline; do not
    # equate a news title with verification that its allegations or causes are true.
    approved=("reuters","bloomberg","cnbc","financial times","globes","גלובס",
              "themarker","כלכליסט","calcalist","ynet","marketwatch")
    keywords=("fed decision","fomc","inflation data","cpi report","earnings","central bank",
              "ריבית בנק ישראל","החלטת ריבית","מדד המחירים","דוחות כספיים",
              "שבבים","chipmakers","oil supply","נפט","גירעון המדינה")
    rejects=("prediction","forecast:","could","will the","opinion","תחזית למניה","למה כדאי","איך להרוויח")
    extras=[]
    seen=set()
    for record in (news.get("items",[])+news.get("macro_items",[])+news.get("israel_focus",[])):
        if not isinstance(record,dict):continue
        src=str(record.get("source",""))
        title=str(record.get("title","")).rsplit(" - ",1)[0].strip()
        low=title.lower()
        if not any(p in src.lower() for p in approved):continue
        if not any(k in low for k in keywords):continue
        if any(x in low for x in rejects):continue
        try:stamp=datetime.fromisoformat(str(record["published_at"])).astimezone(TZ)
        except (KeyError,TypeError,ValueError):continue
        if not timedelta(0)<=now-stamp<=timedelta(hours=30):continue
        url=str(record.get("link",""))
        if not url.startswith("https://"):continue
        key=(title[:75].casefold(),src.lower())
        if key in seen:continue
        seen.add(key)
        extras.append((stamp,title,src,url))
    extras.sort(reverse=True)
    if extras:
        stamp,title,src,url=extras[0]
        section("דיווח עדכני למעקב — טרם אומתה השפעתו",[
            f"בדיווח של {src} מ־{stamp.strftime('%d.%m.%Y')} נכתב: {title}. "
            "זו כותרת מדווחת, לא אימות עצמאי של האירוע או של השפעתו על מחירי הנכסים. "
            "יש לבדוק את הפרטים ואת תגובת המסחר לפני מסקנה."],
            [{"label":src+" · "+stamp.strftime("%d.%m.%Y"),"url":url}])

    # Portfolio issues beat topical quotas. Three different asset sensitivities are
    # preferable to three versions of the same headline.
    chosen=[]
    used=set()
    for p in points:
        family=("energy" if "נפט" in p["title"] else
                "bond" if "אג״ח" in p["title"] else
                "israel" if "תל אביב" in p["title"] else "equity")
        if family in used:continue
        chosen.append(p);used.add(family)
        if len(chosen)==3:break
    if not sections:
        sections=[{"heading":"אין ציטוטי מסחר מאומתים", "bullets":[
            "מקורות נתוני השוק לא החזירו נתוני סגירה עדכניים. אין להציג תנועות שוק משוערות."],"sources":[]}]
    return {"sections":sections, "advisor":chosen,
            "takeaway":"סקירת אירועי המסחר האחרונים בלבד; שינוי במחיר אינו הוכחה לגורם לשינוי. "
                       "יש לבדוק תאריכי מסחר, תמחור וסיכוני תיק לפני החלטה.",
            "methodology":"סקירה אוטומטית המבוססת על שערי סגירה מתוארכים ומקורות גלויים; אינה ניתוח AI או המלצת השקעה."}
