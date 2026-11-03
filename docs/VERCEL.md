# Vercel deployment

Repository: https://github.com/snehasishh23/finn_investor_intelligence

## Import settings

- Framework: FastAPI
- Root directory: repository root
- Python: 3.12 via `.python-version`
- Entrypoint: `app.py` exports `app`
- Dependencies: `requirements.txt`
- Build command / output directory: framework defaults
- Function duration: 300 seconds via `vercel.json`

The UI and demo API need no secrets. Enable live model analysis by adding `GEMINI_API_KEY` to the production environment and redeploying. Optional `FAST_MODEL`, `STRONG_MODEL` and `FINN_RESEARCH_CHUNKS` overrides are server-side only.

Do not use a long-lived local database path on Vercel. The default cache path is `/tmp/finn/cache.db`, which is disposable and instance-local. Analysis returns its result within the same request, using a 260-second budget. A production research system would use durable workflow execution and shared storage for longer jobs.

## Post-deploy verification

1. Open the production URL in a private browser and verify it is accessible to the assessors.
2. Check `/api/health`, `/api/data?mode=demo`, `/static/app.js` and the homepage.
3. Test the demo briefing, Saved filter, signal thresholds, and all four demo research tickers on a phone viewport.
4. Select Live and check source warnings / available quote coverage.
5. With the server-side model key configured, research TCS and one ticker outside the portfolio. Open page citations and verify the actual evidence manually.
6. Insert the verified production URL into `docs/COVERING_NOTE.md` and the submission email.

Deployment is not considered complete until the production URL has been tested. A domain has not been guessed or inserted as if it already exists.

Official references: [FastAPI](https://vercel.com/docs/frameworks/backend/fastapi), [Python runtime](https://vercel.com/docs/functions/runtimes/python), [function duration](https://vercel.com/docs/functions/configuring-functions/duration).

## Current deployment

https://finn-investor-intelligence-ashen.vercel.app

Deployed through Vercel Drop to the existing Hobby account. There is no Git integration, so GitHub pushes do not yet trigger deployments. New versions can be uploaded from the project's Vercel dashboard. The source repository remains https://github.com/snehasishh23/finn_investor_intelligence.
