
import json
import urllib.request

symbols = {
    "S&P 500": "%5EGSPC",
    "Nasdaq Composite": "%5EIXIC",
    "Dow Jones": "%5EDJI"
}

for name, symbol in symbols.items():
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + symbol + "?range=5d&interval=1d"
    )

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.load(response)

        chart = data["chart"]["result"][0]
        quote = chart["indicators"]["quote"][0]
        closes = [x for x in quote["close"] if x is not None]

        print(name, "OK" if len(closes) >= 2 else "NO DATA")
        print("Closing prices:", closes[-2:])

    except Exception as error:
        print(name, "ERROR:", str(error))
