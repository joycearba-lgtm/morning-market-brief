"""One-year outlook: live official rates and Cleveland Fed 1-year inflation model.
Israeli one-year market expectations in the Oct-21 Bank of Israel report are dated,
not real-time. Remove them after 35 days rather than showing stale values as current.
"""
import json, csv, io, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

NOW=datetime.now(ZoneInfo("Asia/Jerusalem"))
HEAD={"User-Agent":"Mozilla/5.0 (MarketBrief/1.0)"}
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=HEAD),timeout=12) as r:
        return r.read(850000).decode("utf-8-sig")

def entry(value, ref, source, url, detail=""):
    return {"status":"ok","value":round(float(value),2),"as_of":ref,
            "source":source,"source_url":url,"detail":detail}

out={"checked_at":NOW.isoformat(),"israel":{},"us":{}}
isra=out["israel"]
us=out["us"]
try:
    url="https://boi.org.il/PublicApi/GetInterest"
    data=json.loads(get(url))
    val=data.get("currentInterest")
    if not isinstance(val,(int,float)) or not 0<=val<=25:
        raise ValueError("Invalid BOI rate")
    isra["rate_now"]=entry(val,NOW.date().isoformat(),"Bank of Israel official interest API",url,
                           "API rate checked on date shown; not the date of last rate decision")
except Exception as e:
    isra["rate_now"]={"status":"unavailable","reason":type(e).__name__}

# One-year market expectation figures from a dated Bank of Israel October 2026 table.
# No automatic claim of new expectations once the publication becomes old.
asof=datetime(2026,10,19,tzinfo=ZoneInfo("Asia/Jerusalem"))
url="https://boi.org.il/en/communication-and-publications/press-releases/21-10-26-aen/"
if timedelta(0)<=NOW-asof<=timedelta(days=35):
    isra["rate_1y"]=entry(3.1,"2026-10-19","BOI: market interest expectations",url,
                           "SHIR market based; approximately one year; dated snapshot")
    isra["inflation_1y"]=entry(1.8,"2026-10-19","BOI: 12 CPI readings from inflation contracts",url,
                                "Market-derived next 12 CPI releases; dated snapshot")
else:
    isra["rate_1y"]={"status":"unavailable","reason":"BOI expectation older than 35 days"}
    isra["inflation_1y"]={"status":"unavailable","reason":"BOI expectation older than 35 days"}

il=Path("israel_macro.json")
try:
    data=json.loads(il.read_text(encoding="utf-8"))
    row=data.get("indicators",{}).get("israel_cpi_yoy",{})
    date=row.get("observation_period","")
    if row.get("status")=="ok" and isinstance(row.get("value"),(int,float)):
        dt=datetime.strptime(date,"%Y-%m")
        age=(NOW.year-dt.year)*12+NOW.month-dt.month
        if 0<=age<=3:
            isra["inflation_now"]=entry(row["value"],date,"CBS Israel CPI",row.get("source_url","https://www.cbs.gov.il/"),
                                         "Last 12-month CPI change; reference month")
except Exception:
    pass
isra.setdefault("inflation_now",{"status":"unavailable"})

usobs=Path("macro_indicators.json")
try:
    data=json.loads(usobs.read_text(encoding="utf-8")).get("indicators",{})
    lo,hi=data.get("us_fed_target_lower",{}),data.get("us_fed_target_upper",{})
    if lo.get("status")=="ok" and hi.get("status")=="ok":
        d=datetime.fromisoformat(hi["observation_date"]).date()
        if 0<=(NOW.date()-d).days<=14 and lo["value"]<=hi["value"]:
            us["rate_now"]={"status":"ok","value":round(hi["value"],2),
                "lower":round(lo["value"],2),"upper":round(hi["value"],2),
                "as_of":hi["observation_date"],"source":"Federal Reserve via FRED",
                "source_url":"https://fred.stlouisfed.org/series/DFEDTARU"}
    cpi=data.get("us_cpi",{})
    if cpi.get("status")=="ok" and isinstance(cpi.get("value"),(float,int)):
        d=datetime.fromisoformat(cpi["observation_date"]).date()
        if 0<=(NOW.date()-d).days<=95:
            us["inflation_now"]=entry(cpi["value"],cpi["observation_date"],
                                     "BLS CPI via FRED","https://fred.stlouisfed.org/series/CPIAUCNS",
                                     "12-month CPI, not PCE")
except Exception:
    pass
us.setdefault("rate_now",{"status":"unavailable"})
us.setdefault("inflation_now",{"status":"unavailable"})

# Cleveland Fed model-implied CPI expected inflation over the following 12 months.
try:
    code="EXPINF1YR"
    csvdata=get("https://fred.stlouisfed.org/graph/fredgraph.csv?id="+code)
    pts=[]
    for row in csv.DictReader(io.StringIO(csvdata)):
        v=row.get(code,"").strip()
        d=(row.get("observation_date") or row.get("DATE") or "").strip()
        if d and v and v!=".":
            pts.append((datetime.strptime(d,"%Y-%m-%d").date(),float(v)))
    if not pts:raise ValueError("No inflation expectations observations")
    d,v=max(pts)
    if not 0<=(NOW.date()-d).days<=75:raise ValueError("Inflation expectation stale")
    if not -5<=v<=25:raise ValueError("Implausible expectation")
    us["inflation_1y"]=entry(v,d.isoformat(),"Cleveland Fed model via FRED",
                               "https://fred.stlouisfed.org/series/EXPINF1YR",
                               "One-year expected CPI inflation, model-based, monthly")
except Exception as e:
    us["inflation_1y"]={"status":"unavailable","reason":type(e).__name__}

# No source with matching 12-month horizon has been verified for US policy-rate expectations.
us["rate_1y"]={"status":"unavailable","reason":"No validated twelve-month-ahead policy rate expectations source"}

Path("forecast_data.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("Forecast availability:",{r:{k:v.get("status") for k,v in t.items()} for r,t in (("IL",isra),("US",us))})
