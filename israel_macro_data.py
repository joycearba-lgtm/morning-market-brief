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
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}(-[0-9]{2})?",text):
        return text[:7]
    if re.fullmatch(r"[0-9]{2}-[0-9]{4}",text):
        return text[3:]+"-"+text[:2]
    if re.fullmatch(r"[0-9]{6}",text):
        return text[:4]+"-"+text[4:]
    return None

def find_entries(value):
    """Only accept nodes containing an explicit observation period and index value."""
    result=[]
    if isinstance(value,dict):
        d=next((parse_date(value.get(k)) for k in ("date","period","month","time","referencePeriod","dateValue") if parse_date(value.get(k))),None)
        if not d:
            year=value.get("year") or value.get("Year")
            month=value.get("month") or value.get("Month")
            if isinstance(year,(int,str)) and isinstance(month,(int,str)):
                try:
                    yy,mm=int(year),int(month)
                    if 1900<=yy<=2100 and 1<=mm<=12:
                        d=f"{yy:04d}-{mm:02d}"
                except ValueError:
                    pass
        v=next((value.get(k) for k in ("value","index","price","indexValue","Value") if isinstance(value.get(k),(int,float))),None)
        if d and isinstance(v,(int,float)) and v>0:
            result.append((d,float(v)))
        for child in value.values():
            result.extend(find_entries(child))
    elif isinstance(value,list):
        for child in value: result.extend(find_entries(child))
    return result

def find_cpi_rates(value):
    """Use CBS-provided annual % change, never infer it from mixed index bases."""
    found=[]
    if isinstance(value,dict):
        period=None
        for key in ("date","period","month","time","referencePeriod","dateValue"):
            period=parse_date(value.get(key))
            if period: break
        if not period:
            y=value.get("year")
            m=value.get("month")
            try:
                y,m=int(y),int(m)
                if 1900<=y<=2100 and 1<=m<=12:
                    period=f"{y:04d}-{m:02d}"
            except (ValueError,TypeError):
                pass
        annual=value.get("percentYear")
        if period and isinstance(annual,(int,float)):
            found.append((period,float(annual)))
        for child in value.values():
            found.extend(find_cpi_rates(child))
    elif isinstance(value,list):
        for child in value:found.extend(find_cpi_rates(child))
    return found

def israel_cpi():
    url="https://api.cbs.gov.il/index/data/price?id=120010&last=16&coef=true&format=json&download=false&lang=en"
    data=json.loads(get(url))
    rates=sorted(set(find_cpi_rates(data)))
    if not rates:
        if isinstance(data,dict):
            raise ValueError("No dated percentYear records; top-level CBS fields: " + ", ".join(str(k) for k in list(data.keys())[:12]))
    if not rates:
        raise ValueError("No dated percentYear observations found in official CBS response")
    period,annual=rates[-1]
    year,month=map(int,period.split("-"))
    age=(NOW.year-year)*12+(NOW.month-month)
    if age<0 or age>3:raise ValueError("CBS inflation rate is stale")
    if not -10<=annual<=40:raise ValueError("CBS annual change outside plausible range")
    return {"status":"ok","value":round(annual,2),"unit":"% YoY",
        "observation_period":period,"source":"CBS Israel CPI published annual percentage change",
        "source_url":url,"note":"CBS percentYear field, not calculated from mixed index base series"}

def unemployment():
    code="LRUNTTTTILM156S"
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
    if age<0 or age>4:raise ValueError("Labor observation too old")
    return {"status":"ok","value":round(value,2),"unit":"%","observation_period":period,
        "source":"OECD via FRED – Israel unemployment, seasonally adjusted, age 15+",
        "source_url":"https://fred.stlouisfed.org/series/"+code}

for key,fn in (("israel_cpi_yoy",israel_cpi),("israel_unemployment",unemployment)):
    try:OUT["indicators"][key]=fn()
    except Exception as e:OUT["indicators"][key]={"status":"unavailable","reason":type(e).__name__+": "+str(e)[:160]}
OUT["status"]="ok" if any(x["status"]=="ok" for x in OUT["indicators"].values()) else "unavailable"
Path("israel_macro.json").write_text(json.dumps(OUT,ensure_ascii=False,indent=2),encoding="utf-8")
print("Israel macro feed statuses:",{k:v["status"] for k,v in OUT["indicators"].items()})
