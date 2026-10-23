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
    issues.append("macro_brief.json: missing valid current-day briefing")
if not isinstance(brief.get("sections"),list) or len(brief["sections"])<3:
    issues.append("macro_brief.json: fewer than three editorial sections")
elif sum(len(x.get("bullets",[])) for x in brief["sections"] if isinstance(x,dict))<5:
    issues.append("macro_brief.json: editorial points unexpectedly missing")
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
    if f'"date":"{today}"' not in html:
        issues.append("index.html: embedded briefing is not dated today")
    for required in ('id="market-snapshot"','id="editorial-macro"','id="calendar-snapshot"'):
        if required not in html:
            issues.append("index.html: missing "+required)

result={"date":today,"checked_at":now.isoformat(),
        "status":"ok" if not issues else "failed",
        "issues":issues,"warnings":warnings}
Path("update_health.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
if issues: sys.exit(1)
