
import csv
import io
import json
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

HEADERS = {"User-Agent": "Mozilla/5.0"}
TODAY = datetime.now(ZoneInfo("Asia/Jerusalem"))

result = {
    "updated_at": TODAY.isoformat(),
    "source": "Bank of Israel",
    "usd_ils": None,
    "rate_date": None,
    "status": "unavailable",
    "indices": {},
    "commodities": {}
}


def download(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8-sig")


# USD/ILS - Bank of Israel
try:
    url = "https://boi.org.il/PublicApi/GetExchangeRates"
    data = json.loads(download(url))

    for item in data.get("exchangeRates", []):
        if item.get("key") == "USD":
            result["usd_ils"] = item.get("currentExchangeRate")
            result["rate_date"] = (
                item.get("lastUpdate")
                or data.get("lastUpdate")
            )
            result["status"] = (
                "ok" if result["usd_ils"] is not None
                else "unavailable"
            )
            break
except Exception as error:
    result["usd_error"] = str(error)



# Daily closing prices - Yahoo Finance (try both public chart hosts)
def get_index(symbol, history_range='1mo'):
    from urllib.parse import quote
    encoded = quote(symbol, safe="")
    failures = []
    ranges=[history_range,"1mo"] if history_range!="1mo" else ["1mo"]
    for host,selected_range in [(h,r) for r in ranges for h in ("query1.finance.yahoo.com","query2.finance.yahoo.com")]:
        url = f"https://{host}/v8/finance/chart/{encoded}?range={selected_range}&interval=1d"
        try:
            data = json.loads(download(url))
            charts = data.get("chart", {}).get("result") or []
            if not charts:
                raise ValueError("No chart result")
            chart = charts[0]
            quote_data = chart.get("indicators", {}).get("quote", [{}])[0]
            closes = [float(v) for v in (quote_data.get("close") or []) if v is not None]
            if len(closes) >= 2 and closes[-2] != 0:
                previous, latest = closes[-2:]
            else:
                meta = chart.get("meta", {})
                latest = meta.get("regularMarketPrice")
                previous = meta.get("chartPreviousClose") or meta.get("previousClose")
                if not isinstance(latest, (int, float)) or not isinstance(previous, (int, float)) or previous == 0:
                    raise ValueError("Not enough closing price data")
            # Historical chart points: retain exchange-local session dates and
            # exclude an unfinished current session or invalid/missing prices.
            import math
            meta=chart.get("meta",{})
            exchange_tz=ZoneInfo(meta.get("exchangeTimezoneName") or "UTC")
            period=meta.get("currentTradingPeriod",{}).get("regular",{})
            session_start=period.get("start",0)
            session_end=period.get("end",0)
            points={}
            for stamp,close in zip(chart.get("timestamp") or [],quote_data.get("close") or []):
                if not isinstance(stamp,(int,float)) or stamp>TODAY.timestamp(): continue
                if session_start<=stamp and TODAY.timestamp()<session_end: continue
                if not isinstance(close,(int,float)) or not math.isfinite(close) or close<=0: continue
                day=datetime.fromtimestamp(stamp,exchange_tz).date().isoformat()
                points[day]=round(close,4)
            history=[{"date":day,"close":value} for day,value in sorted(points.items())]
            return {
                "history": history,
                "history_range": selected_range,
                "history_status": "ok" if len(history)>=2 else "unavailable",
                "status": "ok",
                "value": round(latest, 2),
                "change_percent": round((latest / previous - 1) * 100, 2),
                "source": "Yahoo Finance",
                "type": "daily_close",
                "market_time": chart.get("meta", {}).get("regularMarketTime"),
            }
        except Exception as error:
            failures.append(f"{host}: {type(error).__name__}: {str(error)[:120]}")
    return {"status": "unavailable", "reason": "; ".join(failures)}

result["indices"]["S&P 500"] = get_index("^GSPC", "5y")
result["indices"]["Nasdaq Composite"] = get_index("^IXIC", "5y")
result["indices"]["Dow Jones"] = get_index("^DJI")

# Israeli indices - Yahoo Finance delayed EOD quotes; missing responses remain unavailable.
result["indices"]["TA-35"] = get_index("TA35.TA", "5y")
result["indices"]["TA-125"] = get_index("^TA125.TA", "5y")

# Front-month futures, not spot: prices can change as contracts roll.
result["commodities"]["WTI futures"] = get_index("CL=F")
result["commodities"]["Gold futures"] = get_index("GC=F")

# 10-year US Treasury constant maturity yield (annual percent), FRED DGS10.
def get_treasury_10y():
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
        rows = csv.DictReader(io.StringIO(download(url)))
        points = []
        for row in rows:
            raw = row.get("DGS10", "").strip()
            date = (row.get("DATE") or row.get("observation_date") or "").strip()
            if raw and raw != "." and date:
                points.append((date, float(raw)))
        if len(points) < 2:
            raise ValueError("Not enough FRED observations")
        (previous_date, previous), (date, latest) = points[-2:]
        age = (TODAY.date() - datetime.strptime(date, "%Y-%m-%d").date()).days
        if age < 0 or age > 14:
            raise ValueError("Treasury yield data is stale")
        return {
            "status": "ok",
            "value": round(latest, 3),
            "change_bps": round((latest - previous) * 100, 1),
            "source": "FRED / Federal Reserve H.15",
            "as_of": date,
            "type": "annual_yield_percent"
        }
    except Exception as error:
        # No made-up or stale values: explicitly flag a source failure.
        return {"status": "unavailable", "reason": str(error)}

# Prefer the Yahoo chart API already working for the other US indices.
# ^TNX is quoted as an annual yield percentage, not a bond price.
tnx = get_index("^TNX")
if tnx.get("status") == "ok":
    last_yield = float(tnx["value"])
    pct_change = float(tnx["change_percent"])
    previous_yield = last_yield / (1 + pct_change / 100)
    result["treasury_10y"] = {
        "status": "ok",
        "value": last_yield,
        "change_bps": round((last_yield - previous_yield) * 100, 1),
        "source": "Cboe 10Y Treasury Yield / Yahoo Finance",
        "type": "annual_yield_percent",
        "market_time": tnx.get("market_time"),
    }
else:
    result["treasury_10y"] = get_treasury_10y()
    if result["treasury_10y"].get("status") != "ok":
        result["treasury_10y"]["fallback_error"] = tnx.get("reason", "No Yahoo yield quote")


with open("market_data.json", "w", encoding="utf-8") as file:
    json.dump(result, file, ensure_ascii=False, indent=2)


# Keep a fully-renderable market snapshot inside the HTML page.
# This makes the dashboard usable even when a separate JSON fetch is blocked.
try:
    import re
    from pathlib import Path
    page = Path("index.html")
    if page.exists():
        html = page.read_text(encoding="utf-8")
        snapshot = json.dumps(result, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
        replacement = (
            '<!-- MARKET_SNAPSHOT_START -->\\n'
            '<script id="market-snapshot" type="application/json">' + snapshot + '</script>\\n'
            '<!-- MARKET_SNAPSHOT_END -->'
        )
        pattern = r'<!-- MARKET_SNAPSHOT_START -->.*?<!-- MARKET_SNAPSHOT_END -->'
        updated, count = re.subn(pattern, lambda match: replacement.replace('\\n', '\n'), html, count=1, flags=re.S)
        if count == 1:
            page.write_text(updated, encoding="utf-8")
        else:
            print("Warning: missing embedded snapshot markers")
except Exception as error:
    print("Warning: could not update embedded market snapshot:", error)

print(json.dumps(result, ensure_ascii=False, indent=2))
