Subject: ENAM - IIT screening - 2027

Hello ENAM team,

Please find my submission for the AI Engineer Build Challenge: FINN, a responsive investor workspace combining a ranked portfolio briefing with on-demand company research grounded in annual reports and earnings-call transcripts.

Live prototype: https://finn-investor-intelligence-ashen.vercel.app
GitHub: https://github.com/snehasishh23/finn_investor_intelligence
AI coding conversation: https://chatgpt.com/s/cx_6aea2fca403c81919c467804552777da
Build history and validation: https://github.com/snehasishh23/finn_investor_intelligence/tree/main/docs

Key decisions: deterministic rules classify filings and trigger configurable alerts; model calls are reserved for evidence extraction and synthesis. Document hashes and model-aware caches reduce repeat work. Each research claim links to its source and page, and missing evidence stays unknown. The interface clearly distinguishes illustrative demo content from live research.

Validation: 34 automated tests pass. Hosted live research succeeded for TCS and BAJAJ-AUTO, each using four primary documents and returning seven report sections. I also spot-checked selected TCS figures against the cited PDF. The mobile company picker, research tabs, saved filings and persisted alert preferences were checked in the browser.

Trade-offs: sampled document coverage bounds first-run latency and is disclosed in the report. NSE blocks the hosting region, so the filing feed falls back to a clearly dated captured exchange snapshot; prices are end-of-day. Alerts refresh in-app rather than through background device notifications. The prototype does not yet include authentication, OCR, verified management biographies or durable worker infrastructure.

Next, I would improve financial-page retrieval, evaluate guidance comparisons against a labelled dataset, and add authenticated background ingestion with persistent push delivery.

Best regards,
Snehasish Haldar
