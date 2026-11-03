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
