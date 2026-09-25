# AI-Assisted Deal Desk Intake, Routing & QA Workflow

A human-in-the-loop proof of concept for structured Deal Desk intake, document ingestion, requirement-level routing, canonical-source governance, AI-assisted drafting, deadline control, second-read QA, and controlled release.

> **Portfolio demo only.** All demo data is fictional. Do not upload confidential, privileged, personal, or customer-sensitive information.

## Live demo

**Streamlit:** `[ADD YOUR LIVE DEMO URL]`

## Why I built this

Deal Desk work often arrives through fragmented channels: RFPs, procurement questionnaires, spreadsheets, PDFs, legal/commercial requests, security questions, and time-sensitive customer submissions.

The challenge is not simply generating an answer. The workflow must also answer:

- What exactly is being requested?
- What is the deadline and urgency?
- Which internal team owns each material claim?
- Which approved source supports the response?
- Is specialist approval required?
- What remains unresolved before release?
- Who made the final human decision?

This project explores how AI can accelerate that work **without giving AI final authority over external commitments**.

## Core workflow

**1. Structured Request Intake**  
Captures customer, legal entity/business unit, jurisdiction, request type, deadline, owner, scope, and optional request files.

**2. Document & Requirements Ingestion**  
Accepts fictional PDF, DOCX, XLSX, CSV, and TXT files. The app parses supported files in memory and converts the package into a structured requirements register.

**3. Deterministic Triage**  
Creates an auditable baseline review path (`Simplified`, `Standard`, or `Enhanced`) and urgency classification before AI analysis.

**4. Requirement Routing**  
Each extracted requirement receives a category and suggested accountable owner, such as Deal Desk, Legal, Privacy, Security/GRC, Finance, Product, or Infrastructure.

**5. Canonical Source Governance**  
Only sources marked `Approved` are eligible for AI-supported drafting. Draft or deprecated material is excluded from retrieval.

**6. Temporal Source Control**  
The source date is treated as a **next review date**. A source remains within its review window when the submission deadline is on or before that date; a deadline after the next review date triggers revalidation.

**7. AI Review**  
AI reviews the request package and approved evidence, surfaces missing information and risk flags, suggests a review path, and produces draft responses. The AI recommendation never silently overwrites the deterministic baseline.

**8. RFP Response Matrix**  
Creates a requirement-by-requirement working matrix with:
- requirement
- category
- suggested owner
- draft response
- supporting source IDs
- review status
- notes

Review statuses include:
- `Ready for human QA`
- `SME approval required`
- `Evidence missing`
- `Blocked`

**9. Second-Read QA & Human Release Gate**  
The app requires human checks for scope, deadline mechanics, attachments, approved-source traceability, specialist approvals, contradictions, second-reader review, final approver readiness, and submission evidence.

When AI-governance blockers remain, release requires a named human decision and documented rationale.

## Example fictional test

A fictional procurement package containing five requirements was uploaded and parsed:

| Requirement | Suggested owner | Result |
|---|---|---|
| Company postal address / public website | Deal Desk | Ready for human QA |
| SOC 2 status and evidence | Security / GRC | SME approval required |
| Personal-data processing and DPA terms | Privacy / Legal | SME approval required |
| Standard annual pricing and Net 30 terms | Finance | SME approval required |
| EU data residency | Infrastructure + Privacy / Legal | SME approval required |

The workflow preserved the original deterministic `Enhanced` baseline, performed AI-assisted review, retained source traceability, blocked release while human issues remained, and recorded a documented human resolution before the fictional request was marked released.

## Governance principles demonstrated

- AI assists; humans approve.
- Deterministic controls remain visible and auditable.
- Customer/request documents are treated as **input**, not as evidence supporting company claims.
- Material claims must trace to approved internal sources.
- Specialist ownership is explicit.
- Conditional statements stay conditional.
- Missing evidence is surfaced rather than invented.
- High-risk or unresolved items block normal release.
- Human overrides require a named approver and rationale.
- The public demo does not autonomously send or submit responses.

## Privacy and cost controls

- Public portfolio demo uses fictional data only.
- Common PII patterns are redacted before API transmission.
- Uploaded files are parsed in memory and raw uploads are not intentionally persisted by the app.
- Live AI calls are protected by a private demo access code unless explicitly configured otherwise.
- Per-session AI call limits reduce accidental API spend.
- Application data is session-scoped by default.

Pattern-based redaction is not a complete DLP solution. A production deployment would require enterprise authentication, authorization, encrypted persistent storage, audit logging, formal retention rules, DLP/classification controls, stronger source metadata, and production-grade observability.

## Technology

- Python
- Streamlit
- pandas
- OpenAI API
- pypdf
- python-docx
- openpyxl

## What this prototype is — and is not

This is a **working portfolio proof of concept**, not a production Deal Desk platform.

It demonstrates workflow design, AI-assisted operations, governance controls, requirement routing, source traceability, human review, and release discipline. It does not claim to replace Legal, Security, Privacy, Finance, Product, or other accountable specialists.

## Design takeaway

The goal is not to make AI the decision-maker. The goal is to make the human-controlled workflow **faster, more structured, more traceable, and harder to release incorrectly**.
