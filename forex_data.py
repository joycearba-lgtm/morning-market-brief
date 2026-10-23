"""Fetch a delayed intraday USD/ILS market quote, separately from BOI representative rate.
Does not manufacture live prices. Non-stale quotes only.
"""
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

now = datetime.now(timezone.utc)
result={"checked_at":now.isoformat(),"status":"unavailable","symbol":"USDILS=X",
        "source":"Yahoo Finance","type":"delayed_market_quote"}
errors=[]
for host in ("query1.finance.yahoo.com","query2.finance.yahoo.com"):
    try:
        url=f"https://{host}/v8/finance/chart/{quote('USDILS=X',safe='')}?range=1d&interval=1m"
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=16) as resp:
            obj=json.loads(resp.read().decode("utf-8"))
        chart=(obj.get("chart",{}).get("result") or [None])[0]
        if not chart:raise ValueError("Missing Yahoo chart result")
        meta=chart.get("meta",{})
        if meta.get("currency") not in ("ILS",None):
            raise ValueError("Unexpected quote currency")
        timestamps=chart.get("timestamp") or []
        q=(chart.get("indicators",{}).get("quote") or [{}])[0].get("close") or []
        samples=[(t,float(p)) for t,p in zip(timestamps,q) if isinstance(t,(int,float)) and isinstance(p,(int,float)) and 1<=p<=10]
        if samples:
            ts,value=samples[-1]
        else:
            value=meta.get("regularMarketPrice")
            ts=meta.get("regularMarketTime")
        if not isinstance(value,(int,float)) or not isinstance(ts,(int,float)) or not 1<=value<=10:
            raise ValueError("Invalid value or timestamp")
        stamped=datetime.fromtimestamp(ts,timezone.utc)
        if not timedelta(0)<=now-stamped<=timedelta(minutes=120):
            raise ValueError("Market quote older than 120 min or future-dated")
        result.update({"status":"ok","value":round(float(value),4),
                       "market_time":stamped.isoformat(),
                       "delay_notice":"Indicative delayed market quote, not Bank of Israel representative rate."})
        break
    except Exception as exc:
        errors.append(host+": "+type(exc).__name__)
if result["status"]!="ok":result["errors"]=errors
Path("fx_data.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
