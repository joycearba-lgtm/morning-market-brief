
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
def get_index(symbol):
    from urllib.parse import quote
    encoded = quote(symbol, safe="")
    failures = []
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        url = f"https://{host}/v8/finance/chart/{encoded}?range=1mo&interval=1d"
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
            return {
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

result["indices"]["S&P 500"] = get_index("^GSPC")
result["indices"]["Nasdaq Composite"] = get_index("^IXIC")
result["indices"]["Dow Jones"] = get_index("^DJI")

# Israeli indices - Yahoo Finance delayed EOD quotes; missing responses remain unavailable.
result["indices"]["TA-35"] = get_index("TA35.TA")
result["indices"]["TA-125"] = get_index("^TA125.TA")

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

result["treasury_10y"] = get_treasury_10y()

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
