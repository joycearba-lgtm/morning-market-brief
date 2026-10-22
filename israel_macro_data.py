"""Israel CPI via CBS and unemployment via OECD/FRED; safe if feeds are unavailable."""
import csv
import io
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

NOW = datetime.now(ZoneInfo("Asia/Jerusalem"))
OUT = {"checked_at":NOW.isoformat(),"indicators":{}}
HEAD = {"User-Agent":"Mozilla/5.0 (MarketBriefBot; contact through GitHub repository)"}

def get(url):
    req=urllib.request.Request(url,headers=HEAD)
    with urllib.request.urlopen(req,timeout=10) as response:
        return response.read(600000).decode("utf-8-sig")

def parse_date(text):
    text=str(text or "").strip()
    if re.fullmatch(r"\\d{4}-\\d{2}(-\\d{2})?",text):
        return text[:7]
    if re.fullmatch(r"\\d{2}-\\d{4}",text):
        return text[3:]+"-"+text[:2]
    if re.fullmatch(r"\\d{6}",text):
        return text[:4]+"-"+text[4:]
    return None

def find_entries(value):
    """Only accept nodes containing an explicit observation period and index value."""
    result=[]
    if isinstance(value,dict):
        d=next((parse_date(value.get(k)) for k in ("date","period","month","time","referencePeriod","dateValue") if parse_date(value.get(k))),None)
        v=next((value.get(k) for k in ("value","index","price","indexValue") if isinstance(value.get(k),(int,float))),None)
        if d and isinstance(v,(int,float)) and v>0:
            result.append((d,float(v)))
        for child in value.values():
            result.extend(find_entries(child))
    elif isinstance(value,list):
        for child in value: result.extend(find_entries(child))
    return result

def israel_cpi():
    # Series 120010 is the total consumer price index.
    url="https://api.cbs.gov.il/index/data/price?id=120010&last=16&coef=true&format=json&download=false&lang=en"
    data=json.loads(get(url))
    entries=sorted(set(find_entries(data)))
    if len(entries)<13: raise ValueError("CBS JSON structure unknown or insufficient comparable observations")
    latest,level=entries[-1]
    year,month=map(int,latest.split("-"))
    earlier=f"{year-1:04d}-{month:02d}"
    history=dict(entries)
    if earlier not in history:raise ValueError("No same-month previous year")
    age=(NOW.year-year)*12+(NOW.month-month)
    if age<0 or age>3:raise ValueError("CBS inflation observation is stale")
    return {"status":"ok","value":round((level/history[earlier]-1)*100,2),"unit":"% YoY",
        "observation_period":latest,"source":"CBS Israel CPI","source_url":url,
        "note":"Year-on-year rate computed from comparable CBS index levels"}

def unemployment():
    code="LRUNTTTTILM156N"
    txt=get("https://fred.stlouisfed.org/graph/fredgraph.csv?id="+code)
    rows=[]
    for row in csv.DictReader(io.StringIO(txt)):
        period=parse_date(row.get("DATE") or row.get("observation_date"))
        value=row.get(code)
        if not period or not value or value==".":continue
        rows.append((period,float(value)))
    if not rows:raise ValueError("No unemployment observations")
    period,value=max(rows)
    year,month=map(int,period.split("-"))
    age=(NOW.year-year)*12+(NOW.month-month)
    if age<0 or age>3:raise ValueError("Labor observation too old")
    return {"status":"ok","value":round(value,2),"unit":"%","observation_period":period,
        "source":"OECD via FRED – Israel unemployment, unadjusted, age 15+",
        "source_url":"https://fred.stlouisfed.org/series/"+code}

for key,fn in (("israel_cpi_yoy",israel_cpi),("israel_unemployment",unemployment)):
    try:OUT["indicators"][key]=fn()
    except Exception as e:OUT["indicators"][key]={"status":"unavailable","reason":type(e).__name__+": "+str(e)[:160]}
OUT["status"]="ok" if any(x["status"]=="ok" for x in OUT["indicators"].values()) else "unavailable"
Path("israel_macro.json").write_text(json.dumps(OUT,ensure_ascii=False,indent=2),encoding="utf-8")
print("Israel macro feed statuses:",{k:v["status"] for k,v in OUT["indicators"].items()})
