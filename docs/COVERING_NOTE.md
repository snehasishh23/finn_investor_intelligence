Subject: ENAM - IIT screening - 2027

Hello ENAM team,

I built FINN, a responsive investor workspace around two workflows: a portfolio briefing that ranks material exchange filings and collapses routine disclosures, and on-demand company research that keeps the original document beside each claim.

Repository: https://github.com/snehasishh23/finn_investor_intelligence
Prototype URL: awaiting Vercel deployment verification. The repository includes Vercel, Render and Docker configuration.
AI coding conversation: https://chatgpt.com/s/cx_6aea2fca403c81919c467804552777da
Build summary and validation notes are included in the repository under docs/.

Key decisions: rules handle filing classification and alerts at no model cost; a cheaper model extracts evidence and a stronger model synthesizes research. Caches include model identity and document content hashes. The interface distinguishes fictional demo content from live sources and preserves available data when an upstream service fails. Research citations identify both document and page, and missing guidance or financial figures remain explicitly unknown.

Trade-offs: annual reports and transcripts are sampled with visible coverage limits to bound initial latency and cost. Citation structure is checked, but the model's interpretation still requires human verification. The prototype provides in-app polling and persisted signal preferences rather than background device notifications. I left out authentication, verified management-background lookup, OCR, durable worker queues and exhaustive financial normalization.

Next: improve financial-page retrieval, evaluate guidance comparisons against a labelled dataset, add verified management biography sources, and introduce authenticated background ingestion with persistent push delivery. Those changes would make the prototype more dependable as a daily investor tool.

Best regards,
Snehasish

---
Draft only. No email has been sent. Replace the prototype URL line after Vercel deployment succeeds.
