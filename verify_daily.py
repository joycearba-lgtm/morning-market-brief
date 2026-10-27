"""Validate essentials before publishing the 08:12 Israel morning brief.
A failed check stops the scheduled commit, leaving the last dated report intact.
Noncritical missing sources are explicitly recorded as warnings.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import sys

now = datetime.now(ZoneInfo("Asia/Jerusalem"))
today = now.date().isoformat()
issues, warnings = [], []
editorial_issues = []
allow_pending = '--allow-pending-editorial' in sys.argv

def load(name):
    try:
        return json.loads(Path(name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(f"{name}: unreadable ({type(exc).__name__})")
        return {}

def timestamp(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z","+00:00")).astimezone(now.tzinfo)
    except (ValueError, TypeError):
        return None

market=load("market_data.json")
brief=load("macro_brief.json")
news=load("news_data.json")
calendar=load("economic_calendar.json")

for filename, data, key in [
    ("market_data.json",market,"updated_at"),
    ("news_data.json",news,"updated_at"),
]:
    updated=timestamp(data.get(key))
    if not updated or updated.date().isoformat()!=today:
        issues.append(f"{filename}: no timestamp for {today}")

if brief.get("date")!=today or brief.get("status")!="automatic_conditional":
    editorial_issues.append("macro_brief.json: missing valid current-day briefing")
if brief.get('editorial_mode')!='researched':
    editorial_issues.append('macro_brief.json: headlines are not a researched editorial')
generated=timestamp(brief.get('generated_at'))
until=timestamp(brief.get('valid_until'))
if not generated or generated>now+timedelta(minutes=5) or not until or until<=now:
    editorial_issues.append('macro_brief.json: invalid or expired editorial timestamp')
points=brief.get('advisor')
if not isinstance(points,list) or not 1<=len(points)<=3 or not all(
        isinstance(p,dict) and p.get('title') and p.get('insight')
        and str(p.get('source_url','')).startswith('https://')
        and timestamp(str(p.get('event_date',''))+'T00:00:00+00:00')
        for p in points):
    editorial_issues.append('macro_brief.json: missing sourced client points')
# Editorial content must cover both geographies, without padding it with quote tables.
sections=brief.get("sections")
required_headings={"ישראל — האירועים והמשמעות לשווקים","העולם — מה עומד במוקד"}
if not isinstance(sections,list) or not required_headings.issubset(
        {x.get("heading") for x in sections if isinstance(x,dict)}):
    issues.append("macro_brief.json: missing Israel/world editorial coverage")
else:
    for section in sections:
        bullets=section.get("bullets") if isinstance(section,dict) else None
        if not isinstance(bullets,list) or not bullets or not all(isinstance(b,str) and b.strip() for b in bullets):
            issues.append("macro_brief.json: empty or malformed editorial section")
        if isinstance(section,dict) and "הסגירה האחרונה" in section.get("heading",""):
            issues.append("macro_brief.json: duplicated quote section in editorial")
    if not any(x.get("sources") for x in sections if isinstance(x,dict)):
        warnings.append("No sourced news event available; explicit coverage gaps only")
if news.get("status")!="ok":
    warnings.append("No validated current headlines; institutional context may still be current")
for problem in news.get("errors",[]):
    warnings.append("News: "+str(problem))
for problem in calendar.get("errors",[]):
    warnings.append("Calendar: "+str(problem)+"; date-scoped fallback in use if present")

page=Path("index.html")
if not page.exists():
    issues.append("index.html missing")
else:
    html=page.read_text(encoding="utf-8")
    import re
    embedded=re.search(r'<script id="editorial-macro" type="application/json">(.*?)</script>',html,re.S)
    try:
        if not embedded or json.loads(embedded.group(1))!=brief:
            issues.append('index.html: editorial snapshot does not match macro_brief.json')
    except ValueError:
        issues.append('index.html: malformed editorial snapshot')
    for required in ('id="market-snapshot"','id="editorial-macro"','id="calendar-snapshot"'):
        if required not in html:
            issues.append("index.html: missing "+required)

if not allow_pending:
    issues.extend(editorial_issues)
else:
    warnings.extend(editorial_issues)
result={"date":today,"checked_at":now.isoformat(),
        "status":"failed" if issues else "editorial_pending" if editorial_issues else "ok",
        "editorial_status":"pending" if editorial_issues else "current",
        "editorial_issues":editorial_issues,"issues":issues,"warnings":warnings}
Path("update_health.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
if issues: sys.exit(1)

