"""Refresh quotes only; keep completed-session history and editorial content."""
import copy
import json
import math
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

SYMBOLS = {
    'indices': {'S&P 500': '^GSPC', 'Nasdaq Composite': '^IXIC',
                'Dow Jones': '^DJI', 'TA-35': 'TA35.TA', 'TA-125': '^TA125.TA'},
    'commodities': {'WTI futures': 'CL=F', 'Gold futures': 'GC=F'},
}


def parse_quote(chart, now):
    meta = chart['meta']
    value = meta.get('regularMarketPrice')
    previous = meta.get('previousClose') or meta.get('chartPreviousClose')
    stamp = meta.get('regularMarketTime')
    if not all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0
               for v in (value, previous, stamp)):
        raise ValueError('Missing price, previous close or source timestamp')
    if stamp > now.timestamp() + 60:
        raise ValueError('Future source timestamp')
    return {'status': 'ok', 'value': round(value, 4),
            'change_percent': round((value / previous - 1) * 100, 2),
            'previous_close': previous, 'source': 'Yahoo Finance',
            'type': 'latest_quote', 'market_time': stamp,
            'checked_at': now.isoformat(), 'refresh_status': 'ok'}


def fetch_quote(symbol, now):
    errors = []
    for host in ('query1.finance.yahoo.com', 'query2.finance.yahoo.com'):
        try:
            url = f'https://{host}/v8/finance/chart/{quote(symbol, safe="")}?range=1d&interval=5m'
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.load(response)
            return parse_quote(data['chart']['result'][0], now)
        except Exception as error:
            errors.append(type(error).__name__)
    raise ValueError('Quote refresh failed: ' + ', '.join(errors))


def refresh(data, fetch=fetch_quote, now=None):
    now = now or datetime.now(ZoneInfo('Asia/Jerusalem'))
    result = copy.deepcopy(data)
    successes = 0
    for group, symbols in SYMBOLS.items():
        for label, symbol in symbols.items():
            old = result.setdefault(group, {}).get(label, {})
            try:
                latest = fetch(symbol, now)
                # An old server response must never move a quote backwards.
                if latest['market_time'] < (old.get('market_time') or 0):
                    raise ValueError('Source returned an older quote')
                result[group][label] = {**old, **latest}
                result[group][label].pop('refresh_error', None)
                successes += 1
            except Exception as error:
                old.update(refresh_status='failed', refresh_error=str(error),
                           checked_at=now.isoformat())
                result[group][label] = old
    try:
        tnx = fetch('^TNX', now)
        old = result.get('treasury_10y', {})
        if tnx['market_time'] < (old.get('market_time') or 0):
            raise ValueError('Source returned an older yield')
        result['treasury_10y'] = {
            **tnx, 'value': tnx['value'],
            'change_bps': round((tnx['value'] - tnx['previous_close']) * 100, 1),
            'type': 'annual_yield_percent',
            'source': 'Cboe 10Y Treasury Yield / Yahoo Finance',
        }
        result['treasury_10y'].pop('change_percent', None)
        successes += 1
    except Exception as error:
        result.setdefault('treasury_10y', {}).update(
            refresh_status='failed', refresh_error=str(error), checked_at=now.isoformat())
    result['intraday_checked_at'] = now.isoformat()
    result['intraday_refresh_status'] = 'ok' if successes == 8 else 'partial' if successes else 'failed'
    if successes:
        result['updated_at'] = now.isoformat()
    return result, successes


if __name__ == '__main__':
    path = Path('market_data.json')
    data, count = refresh(json.loads(path.read_text(encoding='utf-8')))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Quote refresh: {count}/8 sources; original quote timestamps retained')
    if not count:
        raise SystemExit('No quotes refreshed; leaving published data untouched')
