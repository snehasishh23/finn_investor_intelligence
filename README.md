# FINN · Investor Intelligence

A mobile-first investor workspace for the ENAM AI Engineer Build Challenge. It puts a ranked portfolio briefing, configurable signals and document-grounded research in one place.

**[Open the deployed prototype](https://finn-investor-intelligence-ashen.vercel.app).**

**Runs immediately without API keys.** Demo mode is explicitly fictional. Live failures never turn into fictional sample prices or sample research. If NSE is blocked, filings can use a clearly labelled real exchange snapshot for at most seven days after capture.

## Run locally

Python 3.12+ recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://localhost:8000. For a phone on the same network, run `uvicorn app:app --host 0.0.0.0 --port 8000` and open your computer's LAN address on the phone.

To enable live document analysis, export `GEMINI_API_KEY` **before starting** the server. The app does not automatically read `.env` files. Optional configuration is listed in `.env.example`. Keep keys on the server.

```bash
export GEMINI_API_KEY='your-key'
# Optional model overrides:
export FAST_MODEL=gemini-2.5-flash
export STRONG_MODEL=gemini-2.5-pro
uvicorn app:app --reload
```

Switch the header from **Demo** to **Live**. Market and announcement data require no model key. PDF research and results extraction require a key and consume provider quota. Model availability depends on your Google account; override the model IDs as needed. The [provider API reference](https://ai.google.dev/api/generate-content) documents the REST endpoint.

## A two-minute walkthrough

1. **Briefing:** select 24 hours, 3 days or 7 days. Material filings appear first, routine filings stay collapsed. Save an item, then open the Saved filter.
2. **Signals:** change the volume multiple or absolute daily price-move threshold. Toggle material announcement categories. Rules persist on this browser. Matching items update immediately.
3. **Research:** try TCS, DIXON, INFY or HDFCBANK in demo mode. In Live, enter any valid NSE symbol, including `M&M` or `BAJAJ-AUTO`. Accessible annual-report and transcript links are discovered on Screener; research is not restricted to the portfolio.
4. **Verify:** in live research, open a page citation. In a live results card, choose **Extract results** for Revenue, EBITDA, PBT and PAT, with current / previous / year-ago amounts and QoQ / YoY percentages. Missing numbers remain missing.

The 16 mock holdings span banks, IT services, telecom, consumer goods, pharma, engineering and electronics: RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, SUNPHARMA, TATAMOTORS, ITC, LT, BHARTIARTL, ASIANPAINT, TITAN, DIXON, ETERNAL, KPITTECH and PERSISTENT. Symbol renames or unavailable bars reduce visible coverage; they do not generate substitute prices.

## How it works

```text
Yahoo daily bars ──→ completed-session checks ──→ price / volume signals
NSE announcements → portfolio + IST window → rules → ranked briefing
                                                    └→ optional results PDF extraction
Screener links → public HTTPS PDFs → page-labelled chunks → cheap extraction
                                                     └→ stronger synthesis → citation validation
SQLite caches: exchange rows / EOD / PDF text + content hashes / model responses
```

- **Cost:** filing classification, filtering and signals need no LLM. Financial extraction is requested on demand. Fast and strong models are configurable. Response cache keys include model and output format. Research includes content hashes. PDFs are refreshed after 24 hours; filing rows after 15 minutes; EOD after 30 minutes.
- **Evidence:** pull analysis uses annual reports and transcripts only. Source IDs distinguish pages in different documents. The server rejects claims without citations or with citations outside analysed pages. This validates reference structure, not the truth or entailment of a model claim; human verification remains necessary.
- **Guidance:** synthesis must compare earlier explicit guidance against later delivered results for the same metric, basis and target period. Missing actual evidence is `unknown`. No guidance is an empty comparison, not an invented verdict. Temporal matching is model-driven, not a deterministic financial audit.
- **Coverage:** PDFs retain page identity. A maximum of 12 evenly spaced text chunks per document bounds cost; omitted chunks are disclosed and exact covered page numbers are returned. A page can be partly represented when it spans multiple chunks. This is partial research, not an exhaustive filing review.
- **Reliability:** market and exchange requests run independently. PDF/model work is queued with bounded concurrency and an in-memory job ID. Polling avoids a single long frontend request. Requests for the same running ticker reuse its job.

## API

Interactive schema: `/docs`.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Health and research configuration, without exposing secrets |
| `GET /api/data?mode=demo&hours=24` | Fictional demo snapshot |
| `GET /api/data?mode=live&hours=168` | Live portfolio data, coverage and source warnings |
| `POST /api/research/TCS?mode=live` | Start research; returns `202` and a job ID |
| `POST /api/filings/{id}/results` | Start on-demand extraction of a cached exchange filing |
| `GET /api/jobs/{id}` | Running, complete or failed analysis |

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
node --check static/app.js
```

Tests cover independent feed failures, demo isolation, cache concurrency, completed-session calculations, announcement ranking/windows/deduplication, source discovery, page-preserving chunking, unsafe document URL rejection, unsupported citations, missing guidance evidence, model-cache isolation and research job deduplication. Tests mock upstream services and do not spend model quota. GitHub Actions runs the suite.

## Deployment

### Vercel (preferred)

Import this GitHub repository into Vercel and use the FastAPI framework preset. The root `app.py`, `.python-version` and `vercel.json` configure the Python deployment. No frontend build command is needed. Add `GEMINI_API_KEY` in Vercel's environment-variable settings for live AI analysis, then redeploy. Demo mode works without a key. Do not paste keys into the repository or public client code.

Vercel-specific behavior:

- Analysis completes inside the HTTP request; it does not return a process-local background job ID.
- The configured function duration is 300 seconds, with a request-local 260-second analysis budget. Slow sources can still exhaust that budget; retries reuse caches only when the same warm instance is available.
- The cache defaults to `/tmp/finn/cache.db` and is ephemeral per instance. It is an optimization, not durable storage or shared state.
- On Vercel, PDF reading samples at most **32 evenly spaced pages per document**, retaining original page indices. Research then samples at most **2 text chunks per document** by default on Vercel to keep the initial demo practical. Coverage warnings remain visible. `FINN_RESEARCH_CHUNKS` can override this from 1 to 12; local/Render deployments default to 12.
- Results extraction can rebuild exchange filing IDs on a cold instance. Source access can still fail if exchange hosts block the deployment region.

See [Vercel deployment notes](docs/VERCEL.md). The [official FastAPI guide](https://vercel.com/docs/frameworks/backend/fastapi) documents entrypoint detection; the [Python runtime guide](https://vercel.com/docs/functions/runtimes/python) documents runtime and dependency selection.

### Render / Docker

`render.yaml` defines a Python web service; connect this repository in Render, supply `GEMINI_API_KEY` if you want live analysis, and deploy. Alternatively:

```bash
docker build -t finn .
docker run --rm -p 8000:8000 -e GEMINI_API_KEY finn
```

The Docker command reads `GEMINI_API_KEY` from your shell. Do not bake keys into images. Demo works without it. A public host needs an account-level access restriction or application authentication before enabling paid model calls. This prototype has no user accounts or per-user quotas. Render's free filesystem is ephemeral, so its SQLite cache will reset; use persistent storage for a longer-lived installation. Deployments and account creation are not performed by this repository.

## Deliberate limits

- Signals refresh in-app every 60 seconds while the page is open and visible. There is no background scheduler, Web Push, email or intraday market feed.
- NSE / Yahoo / Screener and PDF hosts may rate-limit or block automated clients. NSE currently blocks the Vercel deployment region. A captured public exchange response is included as a dated fallback, with original filing links and recalculated event ages; it expires seven days after capture and is always disclosed in live-mode warnings. Empty exchange responses are not proof that no filing exists. The UI shows source warnings and quote coverage.
- Management backgrounds are not invented. Live management notices link to the original filing and explicitly state that professional background has not been verified. External profile enrichment is left for a later iteration.
- Scanned PDFs need OCR, which is not included. Fetches are limited to 25 MB / 600 pages. Document URLs must be public HTTPS and redirects are revalidated; production network isolation would provide stronger SSRF protection.
- Only NSE symbols are supported; no BSE symbol mapping, portfolio editing, position sizing or investment recommendations.
- On local/Render deployments, job state is process-local. Run a single Uvicorn worker; use Redis / a durable worker queue before horizontally scaling. Vercel uses request-bound analysis instead. Browser selections are device-local.
- This is a focused prototype; model claims and financial comparisons require review against the source.

See [covering note](docs/COVERING_NOTE.md), [build history](docs/BUILD_HISTORY.md) and [validation](docs/VALIDATION.md).
