"""FINN API. Demo never silently substitutes for a failed live request."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import threading
import time
from typing import Literal
import uuid
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from finn import filings, market, research

ROOT = Path(__file__).parent
DEMO = json.loads((ROOT / 'finn/demo.json').read_text())
app = FastAPI(title='FINN Investor Intelligence', version='1.0.0')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
feed_pool = ThreadPoolExecutor(max_workers=2)
work_pool = ThreadPoolExecutor(max_workers=2)
jobs, job_keys = {}, {}
lock = threading.Lock()
log = logging.getLogger('finn')


def demo_research(symbol):
    original = DEMO['R'].get(symbol)
    if not original:
        raise HTTPException(404, 'No illustrative research for this ticker. Choose live mode to analyse any supported NSE ticker.')
    def claim(text):
        return {'text': text, 'citations': []}
    return {'mode': 'demo', 'ticker': symbol, 'sources': [], 'warnings': ['All figures and claims below are fictional examples. No primary-source research was performed.'],
            'sections': [{'title': title, 'claims': [claim(text)], 'missing': ''} for title, text in [
                ('Business snapshot', original['biz']), ('Financial snapshot', ' · '.join(f'{a}: {b}' for a, b in original['fin'])),
                ('Trajectory', original['traj']), ('Balance sheet', original['bal']), ('Cash quality', original['cash']),
                ('Bull case', original['bull']), ('Bear case', original['bear'])]],
            'guidance': [{'period': p, 'promise': claim(a), 'delivered': claim(b), 'status': {'miss': 'missed', 'part': 'partial'}.get(status, status)} for p, a, b, status in original['pvd']]}


@app.get('/api/health')
def health():
    return {'status': 'ok', 'research_configured': bool(os.getenv('GEMINI_API_KEY'))}


@app.get('/api/data')
def data(hours: int = Query(24, ge=1, le=168), mode: Literal['demo', 'live'] = 'demo'):
    if mode == 'demo':
        return {'mode': 'demo', 'P': DEMO['P'], 'A': [{**a, 'id': f'demo-{i}'} for i, a in enumerate(DEMO['A']) if a['h'] <= hours],
                'coverage': {'portfolio': len(market.PORTFOLIO), 'quotes': len(DEMO['P'])},
                'warnings': ['Illustrative snapshot. Prices, filings and research are fictional.'], 'fetched_at': None}
    tasks = {'market': feed_pool.submit(market.eod), 'filings': feed_pool.submit(filings.feed, hours)}
    result = {'mode': 'live', 'P': [], 'A': [], 'warnings': [], 'fetched_at': datetime.now(timezone.utc).isoformat()}
    for name, future in tasks.items():
        try:
            rows = future.result()
            result['P' if name == 'market' else 'A'] = rows
            if not rows:
                result['warnings'].append('No EOD bars returned by Yahoo.' if name == 'market' else 'No portfolio filings returned for this window; exchange coverage is not guaranteed.')
        except Exception:
            log.exception('%s feed failed', name)
            result['warnings'].append(f'{name.title()} source unavailable. Retry later; no sample data has been substituted.')
    result['coverage'] = {'portfolio': len(market.PORTFOLIO), 'quotes': len(result['P'])}
    return result


def submit(key, function, *args):
    with lock:
        now = time.time()
        expired = [job_id for job_id, job in jobs.items() if job['future'].done() and now - job['created'] > 3600]
        for job_id in expired:
            job_keys.pop(jobs[job_id]['key'], None)
            del jobs[job_id]
        existing = job_keys.get(key)
        if existing and not jobs[existing]['future'].done():
            return JSONResponse({'job_id': existing}, status_code=202)
        if sum(not job['future'].done() for job in jobs.values()) >= 6:
            raise HTTPException(429, 'Research queue is busy. Please retry shortly.')
        job_id = uuid.uuid4().hex
        jobs[job_id] = {'future': work_pool.submit(function, *args), 'created': now, 'key': key}
        job_keys[key] = job_id
    return JSONResponse({'job_id': job_id}, status_code=202)


@app.post('/api/research/{symbol}')
def start_research(symbol: str, mode: Literal['demo', 'live'] = 'demo'):
    try:
        symbol = research.ticker(symbol)
    except ValueError as error:
        raise HTTPException(422, str(error))
    if mode == 'demo':
        return demo_research(symbol)
    if not os.getenv('GEMINI_API_KEY'):
        raise HTTPException(503, 'Set GEMINI_API_KEY on the server to enable live research.')
    return submit('research:' + symbol, research.run, symbol)


@app.post('/api/filings/{filing_id}/results')
def results(filing_id: str):
    from finn import cache
    for row in cache.get('announcements:v3', 900) or []:
        if row.get('symbol') in market.PORTFOLIO:
            try:
                item = filings.normalize(row)
            except (KeyError, ValueError, TypeError):
                continue
            if item['id'] == filing_id:
                if item['c'] != 'results' or not item.get('url'):
                    raise HTTPException(422, 'This filing has no results PDF.')
                if not os.getenv('GEMINI_API_KEY'):
                    raise HTTPException(503, 'Set GEMINI_API_KEY to extract results.')
                return submit('results:' + filing_id, filings.enrich, item)
    raise HTTPException(404, 'Filing not found or expired. Refresh the digest.')


@app.get('/api/jobs/{job_id}')
def job_status(job_id: str):
    with lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, 'Job not found; the server may have restarted.')
    future = job['future']
    if not future.done():
        return {'status': 'running'}
    try:
        return {'status': 'complete', 'result': future.result()}
    except ValueError as error:
        return {'status': 'failed', 'error': str(error)}
    except Exception:
        log.exception('Analysis failed')
        return {'status': 'failed', 'error': 'Analysis provider or source unavailable. Check server logs and retry.'}


@app.get('/')
def home():
    return FileResponse(ROOT / 'static/index.html')
