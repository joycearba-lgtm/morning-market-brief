
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
    "indices": {}
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
result["indices"]["TA-35"] = get_index("^TA35.TA")
result["indices"]["TA-125"] = get_index("^TA125.TA")

with open("market_data.json", "w", encoding="utf-8") as file:
    json.dump(result, file, ensure_ascii=False, indent=2)

print(json.dumps(result, ensure_ascii=False, indent=2))
