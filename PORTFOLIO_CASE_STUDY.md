# Portfolio Case Study
## AI-Assisted Deal Desk Intake, Routing & QA Workflow

### Summary

I built and deployed a working Streamlit proof of concept for Deal Desk and RFP operations.

The workflow accepts structured intake data and fictional request packages, extracts requirements, routes them to accountable internal owners, retrieves approved sources, generates requirement-level AI-assisted drafts, creates a response matrix, surfaces unsupported claims, and enforces human QA before release.

The central design principle is that **AI assists; humans remain accountable for externally material claims and final release**.

### Problem

Deal Desk work often arrives through RFPs, procurement questionnaires, spreadsheets, PDFs, security requests, commercial questions, and legal/privacy issues. The operational challenge is not simply generating text quickly. The response must also be supported by authoritative evidence, routed to the correct specialist, completed within the customer deadline, and reviewed before it becomes an external commitment.

### What I designed

The workflow contains:

- structured request intake;
- multi-format document ingestion;
- requirement extraction and categorization;
- deterministic review-path and urgency logic;
- cross-functional SME routing;
- an Approved canonical-source library;
- source freshness / next-review-date controls;
- AI-assisted review and drafting;
- a requirement-level RFP response matrix;
- evidence-gap handling;
- second-read QA;
- documented human resolution / exception handling;
- controlled fictional release;
- a dashboard retaining historical status after release.

### Final demo behavior

In the final public demo run, a fictional procurement package containing five requirements was uploaded and parsed.

The system:
- extracted all five requirements;
- assigned an `Enhanced` deterministic baseline;
- assigned `High` AI risk after AI review;
- retrieved approved evidence for only part of the package;
- marked unsupported requirements as `Evidence missing` instead of inventing answers;
- required Security/GRC validation for SOC 2 evidence;
- surfaced missing privacy, commercial, and EU-hosting evidence;
- correctly treated a future next-review date as still within the source review window for the submission deadline;
- blocked normal release while governance issues remained;
- required a named human decision and rationale;
- allowed fictional release only after documented human resolution;
- returned the dashboard to zero active requests/escalations while retaining historical status.

### Why this matters

The prototype demonstrates that AI value in Deal Desk is not limited to writing faster. A useful workflow also needs:

- authoritative-source governance;
- visible ownership;
- deadline and urgency management;
- distinction between customer input and company evidence;
- evidence-gap handling;
- auditability;
- explicit human authority over release.

### Production considerations

A production implementation would add SSO, RBAC, encrypted persistent storage, immutable audit logging, enterprise DLP/classification, malware scanning, richer source metadata, version control, semantic retrieval with metadata filters, formal approval routing, CRM/CLM/procurement integrations, telemetry, and production security/privacy review.

### Skills demonstrated

Deal Desk operations, workflow design, requirements analysis, risk-based routing, stakeholder ownership, source governance, AI-assisted drafting, human-in-the-loop controls, QA design, deadline management, privacy-aware prototyping, and iterative product testing.
