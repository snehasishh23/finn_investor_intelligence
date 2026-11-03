import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from app import app, jobs
from finn import cache, documents, filings, llm, market, research


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setenv('FINN_CACHE_PATH', str(tmp_path / 'cache.db'))
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.setenv('FAST_MODEL', 'test-fast')
    monkeypatch.setenv('STRONG_MODEL', 'test-strong')


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_demo_runs_without_external_services(client, monkeypatch):
    monkeypatch.setattr(market, 'eod', lambda: pytest.fail('demo called Yahoo'))
    monkeypatch.setattr(filings, 'feed', lambda h: pytest.fail('demo called NSE'))
    data = client.get('/api/data').json()
    assert data['mode'] == 'demo'
    assert len(data['P']) == 16
    assert all(a['h'] <= 24 for a in data['A'])
    assert client.get('/').status_code == 200
    assert client.get('/static/app.js').status_code == 200
    assert client.post('/api/research/TCS').json()['mode'] == 'demo'
    assert client.post('/api/research/UNKNOWN').status_code == 404
    assert client.get('/api/data?hours=-2').status_code == 422
    assert client.get('/api/data?hours=169').status_code == 422


def test_live_failure_preserves_other_feed(client, monkeypatch):
    monkeypatch.setattr(market, 'eod', lambda: [{'t': 'TCS'}])
    def fail(hours):
        raise RuntimeError('upstream unavailable')
    monkeypatch.setattr(filings, 'feed', fail)
    data = client.get('/api/data?mode=live').json()
    assert data['P'] == [{'t': 'TCS'}]
    assert data['A'] == []
    assert data['mode'] == 'live'
    assert data['warnings']
    assert not any('demo' in row for row in data['P'])


def test_live_research_requires_configuration(client):
    assert client.post('/api/research/TCS?mode=live').status_code == 503
    assert client.post('/api/research/%3Cscript%3E').status_code == 422
    assert research.ticker('m&m.NS') == 'M&M'


def test_cache_concurrent_writes_and_ttl():
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda n: cache.put(str(n), {'value': n}), range(30)))
    assert cache.get('29') == {'value': 29}
    assert cache.get('29', ttl=-1) is None
    assert cache.get('missing') is None


def test_completed_eod_excludes_current_candle():
    frame = pd.DataFrame({'Close': [100.] * 23, 'Volume': [100.] * 23}, index=pd.date_range('2026-10-01', periods=23))
    frame.iloc[-2] = [105, 200]
    frame.iloc[-1] = [180, 900]
    early = datetime(2026, 10, 23, 12, tzinfo=ZoneInfo('Asia/Kolkata'))
    result = market.summarize('TCS', frame, early)
    assert result['px'] == 105
    assert result['ch'] == 5
    assert result['vol'] == 2
    assert result['as_of'] == '2026-10-22'


def test_volume_baseline_excludes_latest_session():
    frame = pd.DataFrame({'Close': [100.] * 22, 'Volume': [100.] * 21 + [300.]}, index=pd.date_range('2026-01-01', periods=22))
    assert market.summarize('TCS', frame)['vol'] == 3
    frame['Volume'] = 0
    assert market.summarize('TCS', frame) is None


def test_classifier_does_not_promote_results_newspaper_ads():
    assert filings.classify('Newspaper advertisement of quarterly results') == ('routine', 1)
    assert filings.classify('Outcome of board meeting') == ('routine', 1)
    assert filings.classify('Financial results for the quarter') == ('results', 3)
    assert filings.classify('CFO resignation and appointment of CFO') == ('mgmt', 3)


def test_exchange_timestamps_use_ist_and_future_items_are_excluded(monkeypatch):
    now = datetime.now(ZoneInfo('Asia/Kolkata'))
    row = {'symbol':'TCS','an_dt': now.strftime('%d-%b-%Y %H:%M:%S'),'desc':'Financial results','attchmntFile':'https://example.com/a.pdf'}
    normalized = filings.normalize(row, now)
    assert 0 <= normalized['h'] < 0.01
    assert normalized['published_at'].endswith('+05:30')
    cache.put('announcements:v3', [row, row, {**row, 'an_dt':'01-Jan-2099 00:00:00'}])
    assert len(filings.feed(24)) == 1


def test_discovery_resolves_relative_links_and_deduplicates(monkeypatch):
    html = '''<div id="annual-reports"><a href="/ar.pdf">Financial Year 2026</a><a href="/ar.pdf">2026</a></div>
    <div id="concalls"><li>Oct 2026 <a href="/q.pdf">Transcript</a><a href="/presentation.pdf">PPT</a></li></div>'''
    class Response:
        status_code = 200
        text = html
        def raise_for_status(self): pass
    monkeypatch.setattr(research.requests, 'get', lambda *a, **k: Response())
    found = research.discover('TCS')
    assert len(found) == 2
    assert found[0]['url'] == 'https://www.screener.in/ar.pdf'
    assert found[1]['title'] == 'Oct 2026 Transcript PPT'


def test_document_chunks_preserve_page_ids_and_bounds():
    result = list(documents.chunks({'pages':['a'*20000,'second page']}, 'S1', 1000))
    assert all(len(part) <= 1000 for part in result)
    assert '[S1 p1]' in result[0]
    assert any('[S1 p2]' in part for part in result)
    assert sum(part.count('a') for part in result) == 20001  # includes 'page'


@pytest.mark.parametrize('url',['http://example.com/a','https://127.0.0.1/a','https://user:pass@example.com/a','https://example.com:8080/a','file:///etc/passwd'])
def test_document_fetch_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        documents.public_url(url)


def test_citation_validation_requires_analysed_pages():
    sources = [{'id':'S1','covered_pages':[1,3]}]
    report = {'sections':[{'title':'Business','claims':[{'text':'Fact','citations':[{'source':'S1','page':1}]}]}], 'guidance':[]}
    assert research.validate(report, sources) == report
    report['sections'][0]['claims'][0]['citations'][0]['page'] = 2
    with pytest.raises(ValueError, match='outside'):
        research.validate(report, sources)
    report['sections'][0]['claims'][0]['citations'] = []
    with pytest.raises(ValueError, match='no primary'):
        research.validate(report, sources)


def test_guidance_verdict_requires_matching_delivered_evidence():
    claim = {'text':'Target','citations':[{'source':'S1','page':1}]}
    report = {'sections':[{'title':'Business','claims':[claim]}], 'guidance':[{'promise':claim,'delivered':None,'status':'kept'}]}
    with pytest.raises(ValueError, match='delivered evidence'):
        research.validate(report, [{'id':'S1','covered_pages':[1]}])
    report['guidance'][0]['status'] = 'unknown'
    research.validate(report, [{'id':'S1','covered_pages':[1]}])


def test_model_cache_distinguishes_model_and_format(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','test-key')
    calls = []
    class Response:
        ok = True
        def raise_for_status(self): pass
        def json(self):
            return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"ok":true}'}]}}]}
    def post(*a, **kw):
        assert 'test-key' not in a[0]
        calls.append(kw)
        return Response()
    monkeypatch.setattr(llm.requests, 'post', post)
    assert llm.ask('same') == '{"ok":true}'
    assert llm.ask('same',as_json=True) == {'ok': True}
    llm.ask('same')
    monkeypatch.setenv('FAST_MODEL','another-model')
    llm.ask('same')
    assert len(calls) == 3


def test_research_job_completion_and_dedup(client, monkeypatch):
    import threading
    gate = threading.Event()
    monkeypatch.setenv('GEMINI_API_KEY','test-key')
    def run(symbol):
        gate.wait(timeout=3)
        return {'ticker':symbol,'mode':'live'}
    monkeypatch.setattr(research, 'run', run)
    response = client.post('/api/research/TCS?mode=live')
    assert response.status_code == 202
    job_id = response.json()['job_id']
    assert client.post('/api/research/TCS?mode=live').json()['job_id'] == job_id
    assert client.get('/api/jobs/'+job_id).json()['status'] == 'running'
    gate.set()
    jobs[job_id]['future'].result(timeout=3)
    assert client.get('/api/jobs/'+job_id).json()['result']['ticker'] == 'TCS'
    assert client.get('/api/jobs/missing').status_code == 404


def test_research_pipeline_preserves_source_ids_and_cache(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    monkeypatch.setattr(research, 'discover', lambda symbol: [{'id':'S1','kind':'Annual report','title':'FY26','url':'https://example.com/ar.pdf'}])
    monkeypatch.setattr(research, 'fetch_pdf', lambda url: {'pages':['Revenue 100 crore.'], 'hash':'content-v1','url':url})
    calls = []
    def ask(prompt, tier='fast', as_json=False):
        calls.append(tier)
        if tier == 'fast':
            assert '[S1 p1]' in prompt
            return 'Revenue 100 crore [S1 p1].'
        return {'sections':[{'title':'Financial snapshot','claims':[{'text':'Revenue 100 crore.','citations':[{'source':'S1','page':1}]}]}], 'guidance':[]}
    monkeypatch.setattr(research.llm, 'ask', ask)
    report = research.run('TCS')
    assert report['mode'] == 'live'
    assert report['sources'][0]['covered_pages'] == [1]
    assert report['sources'][0]['url'] == 'https://example.com/ar.pdf'
    assert research.run('TCS') == report
    assert calls == ['fast','strong']


def test_results_extraction_preserves_missing_ebitda(monkeypatch):
    monkeypatch.setattr(filings, 'fetch_pdf', lambda url: {'pages':['Quarterly results'], 'hash':'a'})
    monkeypatch.setattr(filings.llm, 'ask', lambda *a, **k: {'unit':'INR crore','basis':'consolidated','periods':['Q2','Q1','Prior Q2'],'rows':[{'metric':name,'values':[None,None,None] if name == 'EBITDA' else [100,90,80], 'page':1} for name in ['Revenue','EBITDA','PBT','PAT']]})
    result = filings.enrich({'c':'results','url':'https://example.com/a.pdf'})
    assert result['rows'][1]['values'] == [None,None,None]
    assert 'not estimated' in result['notice']


def test_bse_viewer_link_resolves_to_pdf(monkeypatch):
    fetched = []
    monkeypatch.setattr(documents, 'public_url', lambda url: url)
    class Response:
        is_redirect = False
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def raise_for_status(self): pass
        def iter_content(self, size): return [b'%PDF-test']
    def get(url, **kwargs):
        fetched.append(url)
        return Response()
    class Page:
        def extract_text(self): return 'Primary source text'
    class PDF:
        pages = [Page()]
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(documents.requests, 'get', get)
    monkeypatch.setattr(documents.pdfplumber, 'open', lambda data: PDF())
    result = documents.fetch_pdf('https://www.bseindia.com/stockinfo/AnnPdfOpen.aspx?Pname=abc-123.pdf')
    assert fetched == ['https://www.bseindia.com/xml-data/corpfiling/AttachHis/abc-123.pdf']
    assert result['pages'] == ['Primary source text']


def test_vercel_analysis_completes_in_request(client, monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    monkeypatch.setattr(research, 'run', lambda symbol: {'ticker':symbol,'mode':'live'})
    response = client.post('/api/research/TCS?mode=live')
    assert response.status_code == 200
    assert response.json() == {'ticker':'TCS','mode':'live'}
    assert 'job_id' not in response.json()


def test_vercel_cache_uses_writable_tmp(monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.delenv('FINN_CACHE_PATH')
    with cache.connection() as db:
        path = db.execute('PRAGMA database_list').fetchone()[2]
    assert path.endswith('/tmp/finn/cache.db')


def test_analysis_budget_expires_and_resets():
    from finn import budget
    with budget.limit(-1):
        with pytest.raises(TimeoutError):
            budget.timeout(20)
    assert budget.timeout(20) == 20


def test_vercel_returns_actionable_analysis_failure(client, monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    def fail(symbol):
        raise TimeoutError('Time budget exhausted')
    monkeypatch.setattr(research, 'run', fail)
    response = client.post('/api/research/TCS?mode=live')
    assert response.status_code == 503
    assert response.json()['detail'] == 'Time budget exhausted'


def test_blocked_exchange_uses_disclosed_real_snapshot(client, monkeypatch, tmp_path):
    import json
    now = datetime.now(ZoneInfo('Asia/Kolkata'))
    row = {'symbol':'TCS','an_dt':now.strftime('%d-%b-%Y %H:%M:%S'),'desc':'Financial results','attchmntFile':'https://example.com/filing.pdf'}
    path = tmp_path / 'snapshot.json'
    path.write_text(json.dumps({'captured_at':now.isoformat(),'rows':[row]}))
    monkeypatch.setattr(filings, 'SNAPSHOT', path)
    class Session:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        headers = {}
        def get(self,*args,**kwargs):
            import requests
            raise requests.HTTPError('blocked')
    monkeypatch.setattr(filings.requests,'Session',Session)
    monkeypatch.setattr(market,'eod',lambda:[])
    result = client.get('/api/data?mode=live').json()
    assert result['A'][0]['t'] == 'TCS'
    assert result['filings_source']['source'] == 'snapshot'
    assert any('not a current live feed' in w for w in result['warnings'])


def test_expired_exchange_snapshot_is_rejected(monkeypatch,tmp_path):
    import json
    path = tmp_path / 'snapshot.json'
    path.write_text(json.dumps({'captured_at':'2020-01-01T00:00:00+00:00','rows':[]}))
    monkeypatch.setattr(filings,'SNAPSHOT',path)
    with pytest.raises(ValueError,match='seven-day'):
        filings.captured_rows()


def test_vercel_pdf_sampling_keeps_original_page_positions(monkeypatch):
    monkeypatch.setenv('VERCEL','1')
    monkeypatch.setattr(documents,'public_url',lambda url:url)
    extracted = []
    class Response:
        is_redirect = False
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def raise_for_status(self): pass
        def iter_content(self,size): return [b'%PDF-large-sample']
    class Page:
        def __init__(self,index): self.index = index
        def extract_text(self):
            extracted.append(self.index)
            return f'Page {self.index + 1}'
    class PDF:
        pages = [Page(i) for i in range(100)]
        def __enter__(self): return self
        def __exit__(self,*args): pass
    monkeypatch.setattr(documents.requests,'get',lambda *a,**k:Response())
    monkeypatch.setattr(documents.pdfplumber,'open',lambda raw:PDF())
    result = documents.fetch_pdf('https://example.com/large.pdf')
    assert len(extracted) == 32
    assert len(result['pages']) == 100
    assert result['pages'][99] == 'Page 100'
    assert result['partial'] is True
    assert 100 in result['extracted_pages']
    assert '[S1 p100]' in ''.join(documents.chunks(result,'S1'))


def test_model_quota_error_is_actionable(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','test-key')
    class Response:
        ok = False
        status_code = 429
    monkeypatch.setattr(llm.requests,'post',lambda *a,**k:Response())
    with pytest.raises(ValueError,match='quota or rate limit'):
        llm.ask('quota test')


def test_auto_model_selection_uses_current_text_models(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','test-key')
    monkeypatch.delenv('FAST_MODEL')
    monkeypatch.delenv('STRONG_MODEL')
    calls = []
    class Response:
        ok = True
        def json(self):
            return {'models':[{'name':'models/'+name,'supportedGenerationMethods':['generateContent']} for name in ['gemini-2.5-flash','gemini-3.5-flash-lite','gemini-3.8-flash','gemini-3.8-flash-tts','gemini-4-argon','gemini-3.8-flash-image']]}
    def get(url,**kwargs):
        assert 'test-key' not in url
        calls.append(url)
        return Response()
    monkeypatch.setattr(llm.requests,'get',get)
    assert llm.resolve_model('fast') == 'gemini-3.5-flash-lite'
    assert llm.resolve_model('strong') == 'gemini-3.8-flash'
    assert len(calls) == 1


def test_explicit_model_override_is_preserved(monkeypatch):
    monkeypatch.setenv('FAST_MODEL','custom-supported-model')
    monkeypatch.setattr(llm.requests,'get',lambda *a,**k:pytest.fail('override must not list models'))
    assert llm.resolve_model('fast') == 'custom-supported-model'


def test_current_model_synthesis_uses_bounded_thinking(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','test-key')
    monkeypatch.setenv('STRONG_MODEL','gemini-3.8-flash')
    class Response:
        ok = True
        def json(self): return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"ok":true}'}]}}]}
    def post(url,**kwargs):
        config=kwargs['json']['generationConfig']
        assert config['thinkingConfig'] == {'thinkingLevel':'LOW'}
        assert config['maxOutputTokens'] == 4096
        assert config['responseMimeType'] == 'application/json'
        return Response()
    monkeypatch.setattr(llm.requests,'post',post)
    assert llm.ask('concise synthesis','strong',True) == {'ok':True}


def test_transient_synthesis_failure_uses_disclosed_fallback(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','test-key')
    monkeypatch.setenv('STRONG_MODEL','auto')
    monkeypatch.setattr(llm,'resolve_model',lambda tier='fast':'gemini-3.5-flash-lite' if tier=='fast' else 'gemini-3.8-flash')
    calls = []
    class Response:
        def __init__(self,ok,status): self.ok,self.status_code=ok,status
        def json(self): return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"ok":true}'}]}}]}
    def post(url,**kwargs):
        calls.append(url)
        return Response(False,503) if len(calls)==1 else Response(True,200)
    monkeypatch.setattr(llm.requests,'post',post)
    assert llm.ask('fallback test','strong',True) == {'ok':True}
    assert llm.model_used('fallback test','strong',True) == 'gemini-3.5-flash-lite'
    assert len(calls)==2
    assert 'gemini-3.5-flash-lite' in calls[1]
    llm.ask('fallback test','strong',True)
    assert len(calls)==2


def test_recent_research_skips_source_discovery(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.setenv('STRONG_MODEL', 'auto')
    monkeypatch.setattr(llm, 'resolve_model', lambda tier='fast': 'fast-model' if tier == 'fast' else 'slow-model')
    monkeypatch.setattr(research, 'discover', lambda symbol: [{'id':'S1','kind':'Transcript','title':'Q2','url':'https://example.com/a.pdf'}])
    monkeypatch.setattr(research, 'fetch_pdf', lambda url: {'pages':['Evidence'], 'hash':'hash'})
    calls = []
    def ask(prompt, tier='fast', as_json=False):
        calls.append((tier, as_json))
        return {'sections':[{'title':'Snapshot','claims':[]}]} if as_json else 'Evidence [S1 p1]'
    monkeypatch.setattr(llm, 'ask', ask)
    monkeypatch.setattr(llm, 'model_used', lambda *args: 'fast-model')
    report = research.run('TCS')
    monkeypatch.setattr(research, 'discover', lambda symbol: pytest.fail('repeat search fetched sources'))
    assert research.run('TCS') == report
    assert calls == [('fast', False), ('fast', True)]
    assert report['models']['synthesis'] == 'fast-model'


def test_parallel_documents_keep_request_deadline(monkeypatch):
    from threading import Barrier
    from finn import budget
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    sources = [{'id':f'S{i}', 'kind':'Transcript', 'title':'Q2', 'url':f'https://example.com/{i}.pdf'} for i in range(1,4)]
    monkeypatch.setattr(research, 'discover', lambda symbol: sources)
    barrier = Barrier(3)
    def fetch(url):
        assert 0 < budget.remaining() <= 120
        barrier.wait(timeout=5)  # Fails if downloads are accidentally sequential.
        return {'pages':['Evidence'], 'hash':url}
    monkeypatch.setattr(research, 'fetch_pdf', fetch)
    monkeypatch.setattr(llm, 'ask', lambda prompt,tier='fast',as_json=False: {'sections':[{'title':'Snapshot','claims':[]}]} if as_json else 'Evidence')
    with budget.limit(120):
        report = research.run('TCS')
    assert [s['id'] for s in report['sources']] == ['S1','S2','S3']
