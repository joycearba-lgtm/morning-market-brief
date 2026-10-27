"""Publish one consistent, source-dated editorial to JSON and the page snapshot."""
import json
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Asia/Jerusalem')
def load(path):
    try: return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError): return {}
now=datetime.now(TZ)
def current_research(candidate, now):
    """Never refresh a research timestamp just because market data ran."""
    try:
        generated=datetime.fromisoformat(candidate['generated_at'])
        until=datetime.fromisoformat(candidate['valid_until'])
        sections=candidate['sections']
        return (
            candidate.get('editorial_mode')=='researched'
            and candidate.get('status')=='automatic_conditional'
            and candidate.get('date')==now.date().isoformat()
            and generated.tzinfo is not None and until.tzinfo is not None
            and -timedelta(minutes=5)<=now-generated<timedelta(hours=24)
            and now<until<=generated+timedelta(hours=36)
            and isinstance(sections,list) and len(sections)>=2
            and all(isinstance(s,dict) and s.get('bullets') for s in sections)
            and any(s.get('sources') for s in sections)
        )
    except (KeyError,TypeError,ValueError):
        return False

candidate=load('researched_brief.json')
if current_research(candidate,now):
    brief=candidate
else:
    # Quote collection cannot replace researched analysis with headline templates.
    # Preserve the original date and timestamp; the editorial audit reports delay.
    published=load('macro_brief.json')
    options=[b for b in (candidate,published)
             if b.get('editorial_mode')=='researched' and b.get('sections')]
    if not options:
        raise SystemExit('No researched editorial available; refusing headline substitution')
    brief=max(options,key=lambda b:b.get('generated_at',''))
    print('Awaiting current-day researched brief; retaining '+str(brief.get('date')))
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

