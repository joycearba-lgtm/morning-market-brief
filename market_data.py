
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


# Daily closing prices - Stooq
def get_index(symbol):
    end = TODAY.strftime("%Y%m%d")
    start = (TODAY - timedelta(days=20)).strftime("%Y%m%d")

    url = (
        "https://stooq.com/q/d/l/"
        f"?s={symbol}&i=d&d1={start}&d2={end}"
    )

    try:
        text = download(url)
        rows = list(csv.DictReader(io.StringIO(text)))
        rows = [
            row for row in rows
            if row.get("Close") not in (None, "", "N/D")
        ]

        if len(rows) < 2:
            return {"status": "unavailable"}

        previous = float(rows[-2]["Close"])
        latest = float(rows[-1]["Close"])

        return {
            "status": "ok",
            "value": latest,
            "change_percent": round(
                (latest / previous - 1) * 100, 2
            ),
            "date": rows[-1]["Date"],
            "source": "Stooq",
            "type": "daily_close"
        }
    except Exception as error:
        return {
            "status": "unavailable",
            "error": str(error)
        }


result["indices"]["S&P 500"] = get_index("^spx")
result["indices"]["Nasdaq Composite"] = get_index("^ndq")
result["indices"]["Dow Jones"] = get_index("^dji")

# Israeli indices require a separately verified data source.
result["indices"]["TA-35"] = {"status": "unavailable"}
result["indices"]["TA-125"] = {"status": "unavailable"}

with open("market_data.json", "w", encoding="utf-8") as file:
    json.dump(result, file, ensure_ascii=False, indent=2)

print(json.dumps(result, ensure_ascii=False, indent=2))
