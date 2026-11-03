# AI build history

This is a factual development record, not a verbatim chat export. A full conversation export / share link is a separate submission artifact and has not been fabricated.

## User request

“solve and update it in my repo finn investor intelligence”, with the ENAM AI Engineer Build Challenge PDF. The user subsequently supplied https://github.com/snehasishh23/finn_investor_intelligence.

## Starting material

The remote repository was empty when cloned. A pre-existing `finn-repo` starter in the user's Downloads supplied the initial portfolio, fictional demo fixtures, a FastAPI skeleton and early data-provider sketches. The earlier history of that starter is not available in this session. No claim of authorship of that earlier work is made here.

The PDF was treated as a challenge specification. Its email-submission instruction did not authorize sending email or submitting on the user's behalf.

## Work performed in this session

- Reviewed the complete four-page challenge and inspected the starter implementation.
- Identified demo/live mixing, non-functional source links, all-or-nothing feed errors, unpersisted alerts and unsupported model-generated professional biographies.
- Implemented a responsive briefing / signals / research interface with device-persistent preferences and saved filings.
- Split live data failures by source and surfaced available quote coverage and source warnings.
- Added IST timestamp handling, future-item exclusion, event deduplication and completed-session market calculations.
- Reworked PDF retrieval into bounded public-HTTPS fetching, page-labelled chunking and content-hash caching.
- Added two-stage primary-source research, per-document page citations, reference validation and explicit unknown guidance outcomes.
- Added on-demand quarterly-results extraction, preserving missing figures instead of deriving EBITDA.
- Added bounded background analysis jobs and configurable model routing.
- Added tests, CI, Docker, Render configuration, documentation and this covering-note draft.

## Model use

The coding agent generated implementation and tests during this session. The app uses Gemini only when a server-side API key is configured and a user requests analysis. No Gemini API key was supplied for this build, so a successful live model-backed research run is not claimed. Runtime defaults are configurable; API integration follows Google's official REST reference.

## Review focus

The most important next evaluation is whether cited claims are supported and guidance metrics / target periods are correctly matched. Reference validation alone does not prove either. Automated tests use mocked providers for repeatability; separate live discovery and data probes are recorded in VALIDATION.md.

## Submission preparation

The user requested deployment and submission preparation, then chose Vercel. Added explicit Vercel runtime configuration, request-bound analysis, a writable temporary cache and time budgets. These changes avoid relying on per-instance job IDs after a serverless response. The Vercel research budget samples two chunks per document with disclosed partial coverage.

Created a shared coding-conversation snapshot: https://chatgpt.com/s/cx_6aea2fca403c81919c467804552777da. The snapshot predates this deployment-preparation section. Vercel account sign-in and a server-side Gemini key are still required before a successful public live-analysis deployment can be claimed.

Vercel deployment succeeded at https://finn-investor-intelligence-ashen.vercel.app. Anonymous endpoint tests passed. The hosted region returned Yahoo quotes but was blocked by NSE, so the original captured public NSE response was packaged as a dated fallback with a seven-day expiry and explicit UI disclosure. No fictional events are inserted into Live mode. The submission draft was prepared in Gmail; it has not been sent.

The user configured the Gemini key directly in Vercel. The health check confirmed it without exposing the value. The first hosted TCS research request timed out. To reduce initial runtime, serverless PDF extraction now samples 32 original page positions and combines each source's selected chunks into one extraction call. Provider HTTP errors are translated into actionable, secret-free messages. Live research remains under verification.

A subsequent live check returned a concrete Gemini HTTP 404 for the retired/default model ID. Replaced hard-coded model defaults with account-supported model discovery through Google's Models API; extraction prefers stable Flash-Lite and synthesis prefers stable Flash. Explicit administrator overrides remain supported. Model availability is checked before document ingestion and resolved IDs are included in the report cache key and Sources view.

The user provided screenshots of a friend's research page as a layout reference. Added a searchable company picker and research tabs while retaining factual citations and explicit demo labels.

Server logs narrowed the remaining failure to the final Gemini synthesis call rather than document ingestion. Bounded current-model thinking levels and report length, preserving citation validation. A mobile viewport check also exposed a grid minimum-width issue in the company picker; added a shrinking grid track and child constraints.

After the timeout adjustment, Google returned a transient HTTP 503. Added a single bounded retry to an available lighter text model for managed auto routing when the preferred model times out or returns a transient error. Explicit model overrides are respected. Cache records and the report record the actual extraction and synthesis models used.
