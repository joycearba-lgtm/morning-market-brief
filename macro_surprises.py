"""Actual vs pre-release consensus, strictly matched by observation period.
Consensus is a dated, hand-verified snapshot, NOT a live forecast API.
Refresh the consensus catalogue only after a new pre-release forecast is sourced.
"""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

NOW=datetime.now(ZoneInfo("Asia/Jerusalem"))
def read(path):
    try:return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError,ValueError):return {}

US=read("macro_indicators.json").get("indicators",{})
IL=read("israel_macro.json").get("indicators",{})

# Each value is a published forecast available before the specified release.
# Comparisons are made only against an official observed value of the same period/units.
CATALOGUE=[
  {
    "id":"israel_cpi_yoy","region":"ישראל","title":"אינפלציה שנתית (CPI)",
    "period":"2026-09","released":"2026-10-15",
    "consensus":1.8,"forecast_source":"Investing.com economic calendar, Oct 15 2026",
    "forecast_url":"https://www.investing.com/economic-calendar/israeli-cpi-880",
    "actual_source":"הלמ״ס",
    "impact":"אינפלציה נמוכה מהצפי עשויה לתמוך בציפיות להקלה מוניטרית; ההשפעה תלויה גם בשקל ובסיכוני האינפלציה."
  },
  {
    "id":"us_cpi","region":"ארה״ב","title":"אינפלציה שנתית (CPI)",
    "period":"2026-09","released":"2026-10-14",
    "consensus":3.6,"forecast_source":"Forex Factory release calendar: Oct 14 2026",
    "forecast_url":"https://www.forexfactory.com/calendar/884-us-cpi-yy",
    "actual_source":"BLS / FRED",
    "impact":"אינפלציה גבוהה מהצפי עשויה לדחוף את ציפיות הריבית כלפי מעלה ולהכביד על אג״ח ארוכות."
  },
  {
    "id":"us_unemployment","region":"ארה״ב","title":"שיעור האבטלה",
    "period":"2026-09","released":"2026-10-02",
    "consensus":4.1,"forecast_source":"Investing.com economic calendar, Oct 2 2026",
    "forecast_url":"https://www.investing.com/economiccalendar/unemployment-rate-300",
    "actual_source":"BLS / FRED",
    "impact":"אבטלה גבוהה מהצפי עשויה להצביע על ריכוך בשוק העבודה, אך נדרשים גם נתוני משרות ושכר."
  }
]

rows=[]
for record in CATALOGUE:
    obj=(IL if record["region"]=="ישראל" else US).get(record["id"],{})
    if obj.get("status")!="ok" or not isinstance(obj.get("value"),(float,int)):
        # Official Bank of Israel 21 Oct note confirms September 2026 annual CPI at 1.6%.
        # Use only for this same October release window, not as a permanent substitute.
        if record["id"]=="israel_cpi_yoy" and NOW.date()<=datetime(2026,11,14).date():
            obj={"status":"ok","value":1.6,"observation_period":"2026-09",
                 "source_url":"https://www.boi.org.il/publications/pressreleases/21-10-26b/"}
        else:
            continue
    ref=obj.get("observation_period") or obj.get("observation_date","")[:7]
    if ref!=record["period"]:
        continue  # a newer official release arrived; old consensus is no longer comparable
    official=float(obj["value"])
    # CPI from FRED is computed to 2dp; published BLS/consensus is 1dp.
    actual=round(official,1)
    expected=float(record["consensus"])
    delta=round(actual-expected,1) # percentage points, not percent change
    result={k:v for k,v in record.items() if k not in ("impact",)}
    result.update({
       "actual":actual,"expected":expected,"surprise_pp":delta,
       "unit":"%","difference_unit":"percentage_points",
       "actual_url":obj.get("source_url",""),
       "interpretation":record["impact"] if abs(delta)>=0.05 else "הנתון תאם את הקונצנזוס; יש לבחון את פרטי הפרסום ואת תגובת השוק."
    })
    rows.append(result)

# Any dated published comparison remains visible for max 32 days after release.
rows=[r for r in rows if 0<=(NOW.date()-datetime.fromisoformat(r["released"]).date()).days<=32]
rows.sort(key=lambda r:r["released"],reverse=True)
data={"checked_at":NOW.isoformat(),"status":"ok" if rows else "unavailable",
      "method":"Consensus snapshots are dated and independently sourced, never estimated from the official actual.",
      "items":rows[:3]}
Path("macro_surprises.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
try:
    page=Path("index.html")
    if page.exists():
        html=page.read_text(encoding="utf-8")
        start,end="<!-- SURPRISE_SNAPSHOT_START -->","<!-- SURPRISE_SNAPSHOT_END -->"
        if start in html and end in html:
            payload=json.dumps(data,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")
            replacement=start+'\n<script type="application/json" id="surprise-snapshot">'+payload+'</script>\n'+end
            prefix,rest=html.split(start,1)
            _,suffix=rest.split(end,1)
            page.write_text(prefix+replacement+suffix,encoding="utf-8")
except Exception as e:print("Inline surprise snapshot warning:",type(e).__name__)
print("Matched macro surprise rows:",len(rows))
