"""Fetch recent market headlines, not generated market explanations."""
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html import unescape

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MorningMarketBrief/1.0)"}
NOW = datetime.now(timezone.utc)
MAX_AGE = timedelta(hours=52)
FEEDS = [
    ("ישראל", "בורסה תל אביב ריבית בנק ישראל מניות שוק ההון when:2d", "he", "IL", "IL:he"),
    ("חו״ל", "stocks Wall Street Federal Reserve Treasury inflation earnings when:2d", "en-US", "US", "US:en"),
    ("מאקרו ארה״ב", "Federal Reserve inflation OR jobs OR economic growth when:2d", "en-US", "US", "US:en"),
    ("מאקרו ישראל", "בנק ישראל ריבית OR אינפלציה OR תוצר OR אבטלה when:2d", "he", "IL", "IL:he"),
]
MARKET_TERMS = re.compile(
    r"בורסה|מניות|שוק ההון|ריבית|אינפלצי|אג״ח|שקל|דולר|בנק ישראל|מדד|"
    r"stocks?|shares?|market|wall street|federal reserve|fed |treasury|bond|"
    r"inflation|interest rate|nasdaq|s&p|earnings|oil price|gold price|economy|gdp|payroll|unemployment|צמיחה|תוצר|גירעון|אבטלה",
    re.IGNORECASE
)

def safe_url(value):
    url = (value or "").strip()
    if url.startswith("https://news.google.com/"):
        return url
    if url.startswith("https://") and len(url) < 2000:
        return url
    return None

def collect_news(group, query, language, country, edition):
    params = urllib.parse.urlencode({"q": query, "hl": language, "gl": country, "ceid": edition})
    url = "https://news.google.com/rss/search?" + params
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=12) as response:
        xml = response.read(600000)
    root = ET.fromstring(xml)
    headlines = []
    for item in root.findall("./channel/item"):
        title = unescape((item.findtext("title") or "").strip())
        link = safe_url(item.findtext("link"))
        pub = item.findtext("pubDate")
        source_element = item.find("source")
        source = unescape((source_element.text or "").strip()) if source_element is not None else ""
        if not title or not link or not pub:
            continue
        try:
            published = parsedate_to_datetime(pub).astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            continue
        if not timedelta(0) <= NOW - published <= MAX_AGE:
            continue
        if not MARKET_TERMS.search(title):
            continue
        # Expose headline and publisher only; never infer market causation.
        headlines.append({
            "title": title[:180],
            "link": link,
            "source": source[:70] or "Google News",
            "published_at": published.isoformat(),
            "region": group
        })
    seen = set()
    selected = []
    for item in sorted(headlines, key=lambda x: x["published_at"], reverse=True):
        key = re.sub(r"\W+", "", item["title"].lower())[:90]
        if key not in seen:
            seen.add(key)
            selected.append(item)
        if len(selected) == 3:
            break
    return selected

news = {"updated_at": NOW.isoformat(), "status": "unavailable", "items": [], "macro_items": [], "errors": []}
for args in FEEDS:
    try:
        stories = collect_news(*args)
        key = "macro_items" if args[0].startswith("מאקרו") else "items"
        news[key].extend(stories)
    except Exception as error:
        news["errors"].append(args[0] + ": " + type(error).__name__)

if news["items"] or news["macro_items"]:
    news["status"] = "ok"

with open("news_data.json", "w", encoding="utf-8") as file:
    json.dump(news, file, ensure_ascii=False, indent=2)

# Store the last successful briefing in the HTML itself as an offline-safe snapshot.
# If this update fails, leave the previous stories (with original published dates) alone.
if news["items"] or news["macro_items"]:
    from pathlib import Path
    page = Path("index.html")
    if page.exists():
        html = page.read_text(encoding="utf-8")
        begin = "<!-- NEWS_SNAPSHOT_START -->"
        end = "<!-- NEWS_SNAPSHOT_END -->"
        payload = json.dumps(news, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
        replacement = begin + '\n<script type="application/json" id="news-snapshot">' + payload + "</script>\n" + end
        if begin in html and end in html:
            prefix, rest = html.split(begin, 1)
            _, suffix = rest.split(end, 1)
            page.write_text(prefix + replacement + suffix, encoding="utf-8")

print("News headlines:", len(news["items"]), "errors:", news["errors"])
