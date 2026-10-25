"""Publish one consistent, source-dated editorial to JSON and the page snapshot."""
import json
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo
from market_editorial import build
TZ=ZoneInfo('Asia/Jerusalem')
def load(path):
    try: return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError): return {}
now=datetime.now(TZ)
report=build(load('market_data.json'),load('news_data.json'),now)
brief=dict(report,date=now.date().isoformat(),generated_at=now.isoformat(),
    valid_until=datetime.combine(now.date()+timedelta(days=1),time(hour=9),tzinfo=TZ).isoformat(),
    title='סקירת הבוקר — ישראל והעולם',status='automatic_conditional')
Path('macro_brief.json').write_text(json.dumps(brief,ensure_ascii=False,indent=2),encoding='utf-8')
page=Path('index.html')
if page.exists():
    html=page.read_text(encoding='utf-8')
    start,end='<!-- EDITORIAL_MACRO_START -->','<!-- EDITORIAL_MACRO_END -->'
    if start in html and end in html:
        payload=json.dumps(brief,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
        prefix,rest=html.split(start,1)
        _,suffix=rest.split(end,1)
        page.write_text(prefix+start+'\n<script id="editorial-macro" type="application/json">'+payload+'</script>\n'+end+suffix,encoding='utf-8')
print(f"Brief {brief['date']}: {len(brief['sections'])} sections, {len(brief['advisor'])} client points")
