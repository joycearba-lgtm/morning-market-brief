import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from intraday_market import parse_quote, refresh
from publish_market import merge_quotes


class IntradayQuotesTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 4, 14, tzinfo=ZoneInfo('Asia/Jerusalem'))
        self.old = {'updated_at': '2026-11-04T08:00:00+02:00', 'usd_ils': 3.5,
                    'indices': {'S&P 500': {'status': 'ok', 'value': 100,
                    'market_time': 10, 'history': [{'date': '2026-11-03', 'close': 100}]}},
                    'commodities': {}}

    def quote(self, symbol, now):
        return parse_quote({'meta': {'regularMarketPrice': 4.946,
            'previousClose': 4.894, 'regularMarketTime': now.timestamp() - 60}}, now)

    def test_percent_and_yield_units(self):
        data, count = refresh(self.old, self.quote, self.now)
        self.assertEqual(count, 8)
        self.assertEqual(data['treasury_10y']['value'], 4.946)
        self.assertEqual(data['treasury_10y']['change_bps'], 5.2)
        self.assertEqual(data['indices']['S&P 500']['change_percent'], 1.06)
        self.assertEqual(data['indices']['S&P 500']['history'], self.old['indices']['S&P 500']['history'])
        self.assertEqual(data['usd_ils'], self.old['usd_ils'])

    def test_failure_keeps_original_price_and_timestamp(self):
        def offline(*args):
            raise ValueError('offline')
        data, count = refresh(self.old, offline, self.now)
        self.assertEqual(count, 0)
        self.assertEqual(data['updated_at'], self.old['updated_at'])
        self.assertEqual(data['indices']['S&P 500']['market_time'], 10)
        self.assertEqual(data['indices']['S&P 500']['value'], 100)
        self.assertEqual(data['indices']['S&P 500']['refresh_status'], 'failed')

    def test_concurrent_newer_data_and_history_are_preserved(self):
        data, _ = refresh(self.old, self.quote, self.now)
        self.old['indices']['S&P 500']['market_time'] = self.now.timestamp()
        merged = merge_quotes(self.old, data)
        self.assertEqual(merged['indices']['S&P 500']['value'], 100)
        self.assertEqual(merged['indices']['S&P 500']['history'], self.old['indices']['S&P 500']['history'])

    def test_reject_future_timestamp(self):
        with self.assertRaises(ValueError):
            parse_quote({'meta': {'regularMarketPrice': 110, 'previousClose': 100,
                        'regularMarketTime': self.now.timestamp() + 3600}}, self.now)


if __name__ == '__main__':
    unittest.main()
