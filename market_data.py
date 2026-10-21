
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



# Daily closing prices - Yahoo Finance
def get_index(symbol):
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + symbol + "?range=10d&interval=1d"
    )

    try:
        data = json.loads(download(url))
        chart = data["chart"]["result"][0]
        quote = chart["indicators"]["quote"][0]

        closes = [
            value for value in quote["close"]
            if value is not None
        ]

        if len(closes) < 2:
            return {"status": "unavailable"}

        previous = closes[-2]
        latest = closes[-1]

        return {
            "status": "ok",
            "value": round(latest, 2),
            "change_percent": round(
                (latest / previous - 1) * 100, 2
            ),
            "source": "Yahoo Finance",
            "type": "daily_close"
        }

    except Exception as error:
        return {
            "status": "unavailable",
            "error": str(error)
        }

result["indices"]["S&P 500"] = get_index("%5EGSPC")
result["indices"]["Nasdaq Composite"] = get_index("%5EIXIC")
result["indices"]["Dow Jones"] = get_index("%5EDJI")

# Israeli indices require a separately verified data source.
result["indices"]["TA-35"] = {"status": "unavailable"}
result["indices"]["TA-125"] = {"status": "unavailable"}

with open("market_data.json", "w", encoding="utf-8") as file:
    json.dump(result, file, ensure_ascii=False, indent=2)

print(json.dumps(result, ensure_ascii=False, indent=2))
