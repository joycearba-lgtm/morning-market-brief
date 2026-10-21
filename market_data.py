import json
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

API_URL = 'https://boi.org.il/PublicApi/GetExchangeRates'

result = {
    'updated_at': datetime.now(ZoneInfo('Asia/Jerusalem')).isoformat(),
    'source': 'Bank of Israel',
    'usd_ils': None,
    'rate_date': None,
    'status': 'unavailable'
}

try:
    request = urllib.request.Request(API_URL, headers={'User-Agent': 'MorningMarketBrief/1.0', 'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    for item in data.get('exchangeRates', []):
        if item.get('key') == 'USD':
            result['usd_ils'] = item.get('currentExchangeRate')
            result['rate_date'] = data.get('lastUpdate')
            result['status'] = 'ok' if result['usd_ils'] is not None else 'unavailable'
            break
except Exception as error:
    result['error'] = str(error)

with open('market_data.json', 'w', encoding='utf-8') as file:
    json.dump(result, file, ensure_ascii=False, indent=2)

print(json.dumps(result, ensure_ascii=False, indent=2))
