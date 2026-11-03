"""Exchange announcements: rules first, optional on-demand results enrichment."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import hashlib
import math
import json
from pathlib import Path
import requests
from . import cache, llm
from .documents import fetch_pdf
from .market import PORTFOLIO

H = {'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en-US,en;q=0.9', 'Referer': 'https://www.nseindia.com/'}
SNAPSHOT = Path(__file__).with_name('filings_snapshot.json')


def captured_rows():
    packet = json.loads(SNAPSHOT.read_text())
    captured = datetime.fromisoformat(packet['captured_at'])
    age = datetime.now(ZoneInfo('Asia/Kolkata')) - captured
    if age.total_seconds() < 0 or age.total_seconds() > 7 * 86400:
        raise ValueError('Captured exchange snapshot is outside its seven-day lifetime.')
    return packet['rows'], packet['captured_at']


RULES = [
    ('routine', 1, ['newspaper', 'trading window', 'analyst meet', 'compliance certificate']),
    ('mgmt', 3, ['resign', 'appointment of', 'cessation', 'key managerial', 'chief financial', 'chief executive']),
    ('lit', 3, ['show cause', 'penalty', 'insolvency', 'litigation', 'regulatory action']),
    ('ma', 3, ['acquisition', 'merger', 'demerger', 'joint venture']),
    ('results', 3, ['financial result', 'quarterly result', 'audited result']),
    ('fund', 3, ['rights issue', 'qip', 'preferential', 'buyback']),
    ('capex', 3, ['capex', 'capital expenditure', 'new plant', 'capacity expansion']),
    ('rating', 2, ['credit rating']), ('div', 2, ['dividend']),
    ('ins', 2, ['insider', 'sast', 'pledge']), ('pr', 2, ['press release', 'clarification', 'order']),
]


def classify(text):
    for category, priority, keywords in RULES:
        if any(k in text.lower() for k in keywords):
            return category, priority
    return 'routine', 1


def normalize(row, now=None):
    now = now or datetime.now(ZoneInfo('Asia/Kolkata'))
    published = datetime.strptime(row['an_dt'], '%d-%b-%Y %H:%M:%S').replace(tzinfo=ZoneInfo('Asia/Kolkata'))
    age = (now - published).total_seconds() / 3600
    text = f"{row.get('desc', '')} {row.get('attchmntText', '')}"
    category, priority = classify(text)
    return {'id': hashlib.sha256(f"{row.get('symbol')}:{published}:{row.get('attchmntFile')}:{text}".encode()).hexdigest()[:20],
            't': row['symbol'], 'c': category, 'p': priority, 'h': round(age, 2),
            'published_at': published.isoformat(), 'title': row.get('desc', ''),
            'sum': (row.get('attchmntText') or '')[:400], 'url': row.get('attchmntFile'),
            'bio_notice': 'Professional background has not been verified.' if category == 'mgmt' else None}


def feed(hours=24):
    rows = cache.get('announcements:v3', 900)
    if rows is None:
        try:
            with requests.Session() as session:
                session.headers.update(H)
                session.get('https://www.nseindia.com', timeout=12).raise_for_status()
                response = session.get('https://www.nseindia.com/api/corporate-announcements',
                                       params={'index': 'equities', 'from_date': (datetime.now(ZoneInfo('Asia/Kolkata')) - timedelta(days=7)).strftime('%d-%m-%Y'), 'to_date': datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%d-%m-%Y')}, timeout=25)
                response.raise_for_status()
                rows = response.json()
            if not isinstance(rows, list):
                raise ValueError('Unexpected NSE response.')
            cache.put('announcements:status', {'source': 'live'})
        except (requests.RequestException, ValueError):
            rows, captured_at = captured_rows()
            cache.put('announcements:status', {'source': 'snapshot', 'captured_at': captured_at})
        cache.put('announcements:v3', rows)
    out, seen = [], set()
    for row in rows:
        if row.get('symbol') not in PORTFOLIO:
            continue
        try:
            item = normalize(row)
        except (KeyError, ValueError, TypeError):
            continue
        if 0 <= item['h'] <= hours and item['id'] not in seen:
            seen.add(item['id'])
            out.append(item)
    return sorted(out, key=lambda item: (-item['p'], item['h']))


def enrich(item):
    if item['c'] != 'results' or not item.get('url'):
        raise ValueError('Only results filings support number extraction.')
    document = fetch_pdf(item['url'])
    text = '\n'.join(f'[p{i+1}] {page}' for i, page in enumerate(document['pages']))
    partial = len(text) > 60000
    result = llm.ask('Extract consolidated quarterly results from this filing only. Return JSON {"unit":"INR crore", "basis":"consolidated", "periods":["current period","previous quarter","year ago"], "rows":[{"metric":"Revenue|EBITDA|PBT|PAT", "values":[null,null,null], "page":1}]}. '
                     'Produce all four metrics. Normalize lakh/million amounts to crore. Missing values are null. EBITDA must be explicitly stated; never derive it. '
                     'Use null periods when unavailable. Do not substitute annual figures for quarterly figures.\n' + text[:60000], 'fast', True)
    if result.get('unit') != 'INR crore' or result.get('basis') != 'consolidated' or len(result.get('periods', [])) != 3:
        raise ValueError('Results did not establish comparable units and accounting basis.')
    if {row.get('metric') for row in result.get('rows', [])} != {'Revenue', 'EBITDA', 'PBT', 'PAT'}:
        raise ValueError('Results response is incomplete.')
    for row in result['rows']:
        if type(row.get('page')) is not int or not 1 <= row['page'] <= len(document['pages']):
            raise ValueError('Invalid results source page.')
        if len(row.get('values', [])) != 3 or any(v is not None and (type(v) not in (int, float) or not math.isfinite(v)) for v in row['values']):
            raise ValueError('Invalid results values.')
    result.update({'url': item['url'], 'partial': partial, 'notice': 'Model extraction; verify against the linked filing. Missing EBITDA is not estimated.'})
    return result
