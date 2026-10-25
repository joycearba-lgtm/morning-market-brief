"""Dated market brief, with separate reported events and conditional implications."""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
TZ = ZoneInfo('Asia/Jerusalem')

# Each topic has an explicit transmission channel and a client-ready explanation.
TOPICS = [
 ('בחירות ומדיניות בישראל', r'בחירות|כנסת|קואליצ|סקרים|מנדטים|election',
  'המשמעות הכלכלית של הבחירות תלויה ביכולת להקים ממשלה, לאשר תקציב ולקבוע סדרי עדיפויות. עיכוב בתקציב או התחייבויות להוצאות נוספות עלולים להגדיל את צורכי גיוס החוב; סקר לבדו אינו שינוי במדיניות.',
  'בתקופת בחירות נבחן בעיקר מה משתנה בתקציב ובמדיניות הכלכלית. אי־ודאות פוליטית יכולה להוסיף תנודתיות לשקל ולאג״ח, אך אין כיוון קבוע לשוק בעקבות סקר.',
  'האם יש לך הוצאה שקלית גדולה בקרוב, או שהכסף מיועד לטווח ארוך?'),
 ('המצב הביטחוני והגיאופוליטי', r'איראן|הסלמה|הפסקת אש|מלחמה|לחימה|ביטחו|ביטחו|בטחו|חמאס|חיזבאללה|iran|ceasefire|war|sanctions',
  'הערוצים הרלוונטיים בישראל הם הסיכון לשקל, הוצאות הביטחון ופעילות העסקים. פגיעה באספקת אנרגיה עלולה להעלות גם את עלויות הדלק והאינפלציה. זו השפעה אפשרית; תגובת השוק נבחנת בנפרד.',
  'החדשות הביטחוניות עשויות להשפיע על השקעות בישראל דרך השקל, פעילות החברות ועלות המימון. נבחן יחד את החשיפה המקומית ואת הצורך בכסף נזיל לפני החלטה.',
  'איזה חלק מהכסף תצטרך בשנה הקרובה, וכמה מהתיק כבר תלוי במשק הישראלי?'),
 ('תקציב וגירעון', r'תקציב|גירעון|גירעונות|גיוס חוב|דירוג אשראי|deficit|sovereign|budget',
  'גידול בגירעון מחייב מימון נוסף. אם השוק ידרוש פיצוי גבוה יותר על הסיכון, תשואות האג״ח עלולות לעלות ומחירי אג״ח קיימות לרדת, בעיקר במח״מ ארוך.',
  'שינוי בתקציב עשוי להשפיע על אג״ח ממשלתיות גם כשבנק ישראל אינו משנה ריבית. ככל שהאג״ח ארוכה יותר, מחירה בדרך כלל רגיש יותר לשינוי בתשואה.',
  'מה חשוב לך יותר בחלק הסולידי: יציבות בטווח הקרוב או נעילת תשואה לאורך זמן?'),
 ('ריבית ואינפלציה', r'ריבית|אינפלצי|מדד המחירים|תעסוקה|fed|fomc|inflation|payroll|rate decision',
  'נתון אינפלציה או תעסוקה משנה את תמונת הריבית בעיקר כשהוא שונה מהציפיות. אינפלציה גבוהה מהצפי עלולה לדחות הפחתות ולהכביד על אג״ח ארוכות; האטה בפעילות מציבה גם סיכון לרווחי החברות.',
  'להשקעות חשוב גם מה השוק ציפה לקבל. הפחתת ריבית אינה מבטיחה עליות, והפתעת אינפלציה יכולה להשפיע על האג״ח עוד לפני החלטת הבנק המרכזי.',
  'האם מטרת ההחזקה באג״ח היא הכנסה שוטפת או אפשרות לממש בקרוב?'),
 ('אנרגיה', r'נפט|ברנט|crude|brent|oil',
  'התייקרות נפט מעלה עלויות דלק ועלולה להקשות על ירידת האינפלציה. מפיקות אנרגיה וחברות תעופה עשויות להיות מושפעות בכיוונים שונים. ירידת נפט הופכת את ערוץ העלויות, אך יכולה לנבוע גם מביקוש חלש.',
  'מחיר הנפט משפיע אחרת על חברות שונות: מפיקות עשויות ליהנות מהתייקרות, בעוד שחברות עתירות דלק סופגות עלויות גבוהות יותר. לכן נבחן את הרכב ההשקעות ולא רק את המדד.',
  'האם קיימת בתיק חשיפה משמעותית לאנרגיה או לחברות תחבורה?'),
 ('חברות וטכנולוגיה', r'דוחות|רווח|שבבים|טכנולוג|nvidia|earnings|semiconductor|chip|nasdaq',
  'בדיווחי חברות חשוב להפריד בין התוצאות שכבר פורסמו לבין התחזית קדימה. שינוי בצפי לרווחים עשוי להשפיע על התמחור; תנועת מדד טכנולוגיה אינה מעידה שכל חברות הענף נעו באותו כיוון.',
  'נבחן אם הדיווח משנה את צפי הרווחים של החברות שבידיך. החזקה בכמה קרנות אינה תמיד פיזור, משום שאותן חברות גדולות עשויות להופיע בכולן.',
  'האם תרצה שנבדוק כמה מהתיק מרוכז באותן חברות דרך קרנות שונות?'),
 ('מסחר במניות', r'בורסה|מניות|וול סטריט|wall street|stock market|s&p|dow',
  'דיווח על מדד מסכם סל של חברות. כדי להבין את משמעותו לתיק יש להשוות בין המדדים ובין הענפים שבאחזקות בפועל.',
  'תנועת המדד אינה בהכרח תנועת התיק שלך. נבדוק אילו ענפים הובילו ומה הייתה התשואה לאחר השפעת המטבע.',
  'האם השינוי שמטריד אותך הוא במדד, או בשווי התיק בשקלים?'),
]
APPROVED = ('reuters','bloomberg','cnbc','financial times','גלובס','globes','themarker',
 'כלכליסט','calcalist','ynet','ביזפורטל','כאן','n12','חדשות 12','מעריב','הארץ','business times')

def select_events(news, now):
    events, seen = [], set()
    for row in news.get('israel_focus', []) + news.get('items', []) + news.get('macro_items', []):
        if not isinstance(row, dict): continue
        source = str(row.get('source', ''))
        if not any(s in source.lower() for s in APPROVED): continue
        try:
            stamp = datetime.fromisoformat(row['published_at'].replace('Z','+00:00'))
            if stamp.tzinfo is None: continue
            stamp = stamp.astimezone(TZ)
        except (KeyError, ValueError, TypeError): continue
        if not timedelta(0) <= now-stamp <= timedelta(hours=52): continue
        title = str(row.get('title','')).strip()
        # Remove repeated publisher/category suffixes without truncating the event.
        while ' - ' in title and title.rsplit(' - ',1)[1].strip() in (source,'שוק ההון','TheMarker'):
            title = title.rsplit(' - ',1)[0].strip()
        if len(title)<20 or not str(row.get('link','')).startswith('https://'): continue
        if '?' in title or '？' in title or '|' in title: continue
        if any(w in title for w in ('השורשים העתיקים','היסטוריה','אשליות ההכרעה','היערכות לבחירות','המפכ','ירד מהפסים','ההתעלמות של המשקיעים','מציע להתמודד')): continue
        if any(s in title.lower() for s in ('טור דעה','פרשנות','| ליאת','prediction','price target','למה כדאי','נשמע הגיוני')): continue
        if title.startswith(('"','״','“')): continue
        key = re.sub(r'\W+','',title.lower())
        if key in seen: continue
        topic = next((t for t in TOPICS if re.search(t[1],title,re.I)),None)
        if not topic: continue
        # Political coverage must contain a concrete economic or policy channel.
        if topic is TOPICS[0] and not re.search(r'תקציב|גירעון|כלכל|מסים|מיסים|דירוג|שקל|אג[״\"]ח|בורסה|הקמת ממשלה|הרכבת ממשלה|אושרה|פיזור הכנסת|מועד הבחירות',title): continue
        if topic is TOPICS[1] and not re.search(r'הפסקת אש|הסלמה|תקיפה|תקף|תקפו|הסכם|סנקציות|גיוס|הוצאות|נפט|ceasefire|sanctions|attack|oil',title,re.I): continue
        region = row.get('region','')
        local = region in ('ישראל','מאקרו ישראל','בחירות','ביטחון','פיסקלי')
        # Local feeds sometimes include stories solely about foreign economies.
        if local and re.search(r'צרפת|גרמניה|בריטניה|france',title,re.I): continue
        if not local and topic is TOPICS[0]: continue
        seen.add(key)
        events.append(dict(row, title=title, stamp=stamp, topic=topic, local=local))
    events.sort(key=lambda x:x['stamp'],reverse=True)
    chosen=[]
    # Reserve space for politics/security instead of allowing financial features to crowd them out.
    for kind in ('בחירות ומדיניות בישראל','המצב הביטחוני והגיאופוליטי'):
        match=next((x for x in events if x['local'] and x['topic'][0]==kind),None)
        if match: chosen.append(match)
    for local in (True,False):
        match=next((x for x in events if x['local']==local and x not in chosen and x['topic'][0] not in {c['topic'][0] for c in chosen}),None)
        if match: chosen.append(match)
    return chosen[:4]

def build(market, news, now):
    sections, points = [], []
    def add(heading, lines, refs=None):
        if lines: sections.append({'heading':heading,'bullets':lines,'sources':refs or []})
    def valid(row):
        if not isinstance(row,dict) or row.get('status')!='ok': return False
        try: return timedelta(0)<=now-datetime.fromtimestamp(row['market_time'],TZ)<=timedelta(days=4)
        except (KeyError,TypeError,ValueError,OverflowError): return False
    def quote(row, label):
        if not valid(row) or not isinstance(row.get('change_percent'),(float,int)): return None
        return f"{label} {row['change_percent']:+.2f}% ({datetime.fromtimestamp(row['market_time'],TZ):%d.%m})"
    events=select_events(news,now)
    for local,heading in ((True,'ישראל — האירועים והמשמעות לשווקים'),(False,'העולם — מה עומד במוקד')):
        lines,refs=[],[]
        for e in events:
            if e['local'] != local: continue
            topic,_,impact,message,question=e['topic']
            if topic=='ריבית ואינפלציה' and re.search(r'set to|expected|preview|צפוי|לקראת',e['title'],re.I):
                impact='זהו דיווח לקראת החלטת ריבית, ולא החלטה שכבר התקבלה. אם הריבית תישאר גבוהה לאורך זמן, עלות המימון תישאר גבוהה לחברות ולמשקי בית. תגובת האג״ח תלויה גם במסר הבנק ובמה שכבר תומחר.'
                message='לקראת החלטת הריבית נבחן בעיקר את המסר לגבי ההמשך. החלטה להשאיר ריבית ללא שינוי יכולה להזיז את השוק אם המסר שונה ממה שהמשקיעים ציפו.'
                question='האם יש בתיק אג״ח ארוכות או חברות שרגישות במיוחד לעלות המימון?'
            stamp=e['stamp'].strftime('%d.%m %H:%M')
            fact=f"לפי {e['source']} ({stamp}): {e['title']}."
            lines.append(f'{topic}: {fact} המשמעות האפשרית: {impact}')
            refs.append({'label':e['source']+' · '+stamp,'url':e['link']})
            if len(points)<3:
                points.append({'title':topic,'insight':message,'client_impact':impact,
                    'question':question,'reference':fact,'source_url':e['link'],
                    'event_date':e['stamp'].date().isoformat()})
        if local:
            for topic,label in ((TOPICS[0][0],'בחירות'),(TOPICS[1][0],'ביטחון וגיאופוליטיקה')):
                if not any(e['local'] and e['topic'][0]==topic for e in events):
                    lines.append(f'{label}: לא נמצא דיווח חדשותי עדכני מתאים במקורות שנאספו. זהו פער בכיסוי, ולא קביעה שלא היו התפתחויות.')
        elif not lines:
            lines.append('לא נמצא דיווח בינלאומי עדכני מתאים; נתוני הסגירה מופיעים בנפרד להלן.')
        add(heading,lines,refs)
    indices=market.get('indices') or {}
    for heading,names in [('תל אביב — הסגירה האחרונה',[('TA-35','ת״א־35'),('TA-125','ת״א־125')]),
                          ('וול סטריט — הסגירה האחרונה',[('S&P 500','S&P 500'),('Nasdaq Composite','Nasdaq'),('Dow Jones','Dow Jones')])]:
        quotes=[q for key,label in names if (q:=quote(indices.get(key,{}),label))]
        if quotes: add(heading,['; '.join(quotes)+'.'])
    oil=(market.get('commodities') or {}).get('WTI futures',{})
    oilquote=quote(oil,'נפט WTI')
    if oilquote and abs(oil['change_percent'])>=1:
        up=oil['change_percent']>0
        impact=('התייקרות הדלק עשויה להכביד על תעופה ותעשייה ולהוסיף לחץ אינפלציוני אם תימשך.' if up else
                'הוזלת הדלק עשויה להקל על עלויות החברות; עבור מפיקות נפט היא עלולה לפגוע בהכנסות.')
        add('נפט — עלויות ואינפלציה',[oilquote+'. '+impact])
        if len(points)<3:
            points.append({'title':'מה אומר השינוי בנפט?','insight':f'בסגירה האחרונה הנפט {"עלה" if up else "ירד"} ב־{abs(oil["change_percent"]):.2f}%. '+impact,
                'client_impact':'ההשפעה על התיק תלויה במשקל חברות האנרגיה מול חברות הצורכות דלק ובמשך השינוי במחיר.',
                'question':'האם יש בתיק חשיפה גדולה לענפים שמושפעים ממחירי הדלק?',
                'reference':oilquote+' · Yahoo Finance'})
    return {'sections':sections,'advisor':points,'takeaway':'למעקב: שינוי ממשי במדיניות ובתקציב בישראל, התפתחויות ביטחוניות, ותנועת הנפט והתשואות לעומת הסגירה הקודמת.',
        'methodology':'סקירה אוטומטית ללא עלות נוספת. דיווחי החדשות מבוססים על כותרות מתוארכות; ההשלכות הן תרחישים לפי נושא, ולא ניתוח מלא של הכתבות או הסבר מוכח לתנועות השוק.'}
