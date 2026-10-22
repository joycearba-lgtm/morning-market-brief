"""Short macro release calendar: BLS official ICS and Bank of Israel published dates.
Events are scheduled releases, not publication of actual data. Fail closed.
"""
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

IL=ZoneInfo("Asia/Jerusalem")
NY=ZoneInfo("America/New_York")
now=datetime.now(IL)
EVENTS=[]
ERRORS=[]
def add(dt,title,source,url,priority):
    if not dt or dt.tzinfo is None:return
    local=dt.astimezone(IL)
    if (local.date()-now.date()).days < 0 or (local.date()-now.date()).days > 45:return
    EVENTS.append({"title":title,"at":local.isoformat(),"source":source,"url":url,"priority":priority})

def unfold(text):
    output=[]
    for line in text.replace("\r\n","\n").split("\n"):
        if line.startswith((" ","\t")) and output:
            output[-1]+=line[1:]
        else: output.append(line)
    return output

# BLS online calendar includes scheduled releases in Eastern time.
try:
    url="https://www.bls.gov/schedule/news_release/bls.ics"
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; MorningMarketBrief/1.0)"})
    with urllib.request.urlopen(req,timeout=12) as response:
        raw=response.read(1000000).decode("utf-8-sig",errors="replace")
    blocks=raw.split("BEGIN:VEVENT")[1:]
    if not blocks: raise ValueError("No VEVENT entries")
    labels=[
        (r"Consumer Price Index", "מדד המחירים לצרכן (CPI)", 1),
        (r"Employment Situation", "דוח התעסוקה (NFP)", 1),
        (r"Producer Price Index", "מדד המחירים ליצרן (PPI)", 2),
        (r"Job Openings and Labor Turnover", "משרות פתוחות (JOLTS)", 2),
        (r"Employment Cost Index", "מדד עלות ההעסקה", 2),
        (r"Import and Export Price Index", "מחירי יבוא ויצוא", 3),
    ]
    for block in blocks:
        lines=unfold(block.split("END:VEVENT")[0])
        title=next((line[8:] for line in lines if line.startswith("SUMMARY:")),"")
        found=next(((he,priority) for pattern,he,priority in labels if re.search(pattern,title,re.I)),None)
        if not found:continue
        dtline=next((x for x in lines if x.startswith("DTSTART")),"")
        value=dtline.split(":",1)[-1].strip()
        if not value:continue
        try:
            if re.fullmatch(r"\d{8}",value):
                dt=datetime.strptime(value,"%Y%m%d").replace(hour=8,minute=30,tzinfo=NY)
                # Never invent a time for all-day items.
                continue
            elif value.endswith("Z"):
                dt=datetime.strptime(value,"%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            else:
                dt=datetime.strptime(value,"%Y%m%dT%H%M%S").replace(tzinfo=NY)
        except ValueError:
            continue
        add(dt,found[0],"BLS",url,found[1])
except Exception as e:
    ERRORS.append("BLS: "+type(e).__name__)

# Official BOI announcement schedule 2026 – 16:00 Israel, verified from BOI.
boi_dates=["2026-01-05","2026-02-23","2026-03-30","2026-05-25",
           "2026-07-06","2026-09-01","2026-10-21","2026-11-23"]
for date in boi_dates:
    dt=datetime.strptime(date+" 16:00","%Y-%m-%d %H:%M").replace(tzinfo=IL)
    add(dt,"החלטת הריבית של בנק ישראל","בנק ישראל",
        "https://www.boi.org.il/roles/monetary-policy/interest-rate-dates/",1)

# Federal Reserve official 2026 FOMC calendar: statement at 14:00 ET.
# Verified meeting and minutes dates from federalreserve.gov. Eastern time conversion handles DST.
fed_calendar=[
    ("2026-10-28 14:00", "החלטת ריבית הפד", 1),
    ("2026-11-18 14:00", "פרוטוקול ישיבת הפד", 2),
    ("2026-12-09 14:00", "החלטת ריבית הפד", 1),
]
for date,title,priority in fed_calendar:
    dt=datetime.strptime(date,"%Y-%m-%d %H:%M").replace(tzinfo=NY)
    add(dt,title,"Federal Reserve",
        "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",priority)

# Keep only verified today events; otherwise show a concise upcoming list.
seen=set()
ordered=[]
for item in sorted(EVENTS,key=lambda x:(x["at"],x["priority"])):
    k=(item["title"],item["at"])
    if k not in seen:
        seen.add(k)
        ordered.append(item)
today=[x for x in ordered if datetime.fromisoformat(x["at"]).date()==now.date()]
upcoming=[x for x in ordered if datetime.fromisoformat(x["at"]).date()>now.date()]
chosen=sorted(today,key=lambda x:(x["priority"],x["at"]))[:3] if today else upcoming[:3]
result={
    "checked_at":now.isoformat(),
    "date":now.date().isoformat(),
    "mode":"today" if today else "upcoming",
    "events":chosen,
    "source_note":"BLS scheduled calendar and Bank of Israel published decision schedule; confirm schedule with linked agency",
    "errors":ERRORS,
}
Path("economic_calendar.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
# Embed current calendar for browsers where fetching the JSON fails.
try:
    page=Path("index.html")
    if page.exists():
        html=page.read_text(encoding="utf-8")
        start="<!-- CALENDAR_SNAPSHOT_START -->"
        end="<!-- CALENDAR_SNAPSHOT_END -->"
        if start in html and end in html:
            payload=json.dumps(result,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")
            replacement=start+'\n<script type="application/json" id="calendar-snapshot">'+payload+'</script>\n'+end
            prefix,rest=html.split(start,1)
            _,suffix=rest.split(end,1)
            page.write_text(prefix+replacement+suffix,encoding="utf-8")
except Exception as error:
    print("Calendar snapshot warning:",type(error).__name__)

print("Calendar:",result["mode"],[(x["title"],x["at"]) for x in chosen],"errors:",ERRORS)
