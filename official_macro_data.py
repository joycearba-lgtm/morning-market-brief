"""Official US macro observations from FRED public CSV (no API key).
Observation dates are not release dates. Do not imply same-day release.
"""
import csv
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

NOW = datetime.now(ZoneInfo("Asia/Jerusalem"))
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MorningMarketBrief/1.0)"}
SPECS = {
    "us_cpi": ("CPIAUCNS", "US CPI, not seasonally adjusted", "yoy"),
    "us_unemployment": ("UNRATE", "US unemployment rate, seasonally adjusted", "level"),
    "us_real_gdp": ("GDPC1", "US real GDP, quarterly seasonally adjusted annual rate", "qoq_annualized"),
    "us_effective_fed_funds": ("DFF", "US effective federal funds rate, daily", "level"),
    "us_fed_target_lower": ("DFEDTARL", "Fed funds target lower bound", "level"),
    "us_fed_target_upper": ("DFEDTARU", "Fed funds target upper bound", "level"),
}
out = {"checked_at": NOW.isoformat(), "status": "unavailable", "indicators": {}, "errors": {}}

def fetch_series(code):
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + code
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as response:
        content = response.read(850000).decode("utf-8-sig")
    rows = []
    for row in csv.DictReader(io.StringIO(content)):
        date = (row.get("observation_date") or row.get("DATE") or "").strip()
        raw = (row.get(code) or "").strip()
        if not date or not raw or raw == ".":
            continue
        day = datetime.strptime(date, "%Y-%m-%d").date()
        if day > NOW.date():
            continue
        rows.append((day, float(raw)))
    if not rows:
        raise ValueError("No valid observations")
    rows.sort()
    return rows

def calculate(code, name, method, rows):
    date, current = rows[-1]
    if method == "level":
        change = current - rows[-2][1] if len(rows) > 1 else None
        value = current
        units = "%"
    else:
        prior = None
        if method == "yoy":
            prior_date = date.replace(year=date.year - 1)
            candidates = [x for x in rows if x[0] == prior_date]
            prior = candidates[-1][1] if candidates else None
            units = "% YoY"
            value = (current / prior - 1) * 100 if prior and prior > 0 else None
        else:
            units = "% QoQ annualized"
            prior = rows[-2][1] if len(rows) > 1 else None
            value = ((current / prior) ** 4 - 1) * 100 if prior and prior > 0 else None
        change = None
    if value is None:
        raise ValueError("Insufficient history")
    return {
        "status":"ok", "name":name, "value":round(value, 2),
        "units":units, "observation_date":date.isoformat(),
        "source":"FRED / official US statistical agencies",
        "source_url":"https://fred.stlouisfed.org/series/" + code,
        "series_id":code, "change_from_previous":round(change, 2) if change is not None else None,
        "frequency":"quarterly" if method == "qoq_annualized" else ("daily" if code == "DFF" else "monthly")
    }

for key, (code, label, method) in SPECS.items():
    try:
        rows = fetch_series(code)
        out["indicators"][key] = calculate(code, label, method, rows)
    except Exception as error:
        out["indicators"][key] = {"status":"unavailable", "series_id":code}
        out["errors"][key] = type(error).__name__ + ": " + str(error)[:140]

out["status"] = "ok" if any(x.get("status") == "ok" for x in out["indicators"].values()) else "unavailable"
Path("macro_indicators.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),encoding="utf-8")
print("Official macro series:", {k:v["status"] for k,v in out["indicators"].items()})
