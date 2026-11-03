# Validation record

Checked on 4 November 2026 (Asia/Kolkata).

Production: https://finn-investor-intelligence-ashen.vercel.app

## Passing checks

- **34 automated tests passed**, locally and in GitHub Actions for deployment source commit `03053b0`. External model calls are mocked in unit tests; integration results below are separate observations.
- JavaScript syntax and `git diff --check` passed.
- Anonymous hosted homepage, CSS, JavaScript, health endpoint, demo data and all four demo research companies returned HTTP 200. Invalid mode/window requests returned 422.
- Health reports research configured; the API key was entered by the user directly into Vercel and was not copied into source or output files.
- **Live TCS research: HTTP 200 in 71.4 seconds**, four primary documents and seven report sections.
- **Live BAJAJ-AUTO research: HTTP 200 in 31.5 seconds**, four primary documents and seven sections. This ticker is outside the mock portfolio.
- Both reports disclose the actual extraction and synthesis model (`gemini-3.5-flash-lite`), including the managed fallback from the preferred synthesis model.
- TCS source spot-check: the original transcript PDF page 3 supports quarterly revenue of ₹73,188 crore; page 6 supports the reported 102.2% cash conversion. This is a limited manual check, not a complete accuracy evaluation.
- Real ITC results filing extraction returned HTTP 200 in 6.1 seconds, with consolidated INR crore periods, revenue/PBT/PAT values and page 9 citations. EBITDA remained null rather than being estimated. This checks the hosted workflow, not full numerical accuracy.
- The production research UI renders the TCS report, document/page citations, six tabs, source coverage and actual model IDs.
- Mobile company picker has no horizontal overflow (375px content and scroll width); company filtering, research tabs, Saved filter and alert preference persistence were exercised. Volume threshold was restored to 2× after the persistence check.
- Hosted live data returns 15 available EOD quotes from the 16-symbol mock portfolio and 68 dated exchange announcement records.

## Practical limits

- NSE blocks requests from the Vercel region. Filings use a clearly labelled real snapshot captured at `2026-11-03T19:11:03.021443+00:00`, with original timestamps/URLs and seven-day expiry. It is not a current live feed. Prices are EOD, not intraday.
- Source PDF pages are sampled on Vercel, with exact page coverage displayed. Citation structure is validated; semantic accuracy and omitted context still require human review. Missing evidence remains unknown.
- Live guidance comparisons depend on explicit comparable promises and actuals in the selected documents; an empty comparison is not replaced with fabricated guidance.
- Provider latency/quota and document availability can change. Auto routing discovers supported models and allows one bounded fallback for transient failures.
- SQLite caches are ephemeral on Vercel. There is no authentication, OCR, verified management biography service, durable background ingestion or device push delivery.
- Vercel Drop deployment is manual. GitHub pushes do not automatically redeploy this project.
- No submission email has been sent.
