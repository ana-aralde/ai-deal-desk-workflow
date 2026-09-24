# Security & Privacy Design Notes

## Data classification

For the public portfolio deployment, use only fictional or deliberately anonymized data. Do not upload or paste privileged legal advice, real procurement records, customer security questionnaires, credentials, personal data, contract secrets, non-public product information, or government-sensitive material.

## Data minimization

The demo sends only the selected request text and a limited set of Approved source excerpts to the AI service. Common email, phone, Brazilian CPF/CNPJ and long-number patterns are locally redacted before transmission. This is an additional control, not a complete DLP solution.

## Secrets

The OpenAI API key and optional demo access code are read from Streamlit Secrets or environment variables. Real secrets must never be committed to GitHub.

## AI retention and training

The code sends `store=False` in Responses API calls. OpenAI states that API inputs/outputs are not used to train models by default unless the customer opts in. OpenAI also documents default abuse-monitoring retention of up to 30 days and separate eligibility/approval for Zero Data Retention. Organizations handling confidential or regulated data should review current vendor documentation, contract terms and applicable retention controls before production use.

## Human-in-the-loop controls

The application does not allow AI to:

- make a final legal-risk determination;
- determine contractual or regulatory precedence;
- invent certifications, security controls, product capabilities, pricing, entities or dates;
- accept non-standard obligations;
- autonomously send or submit a response.

The output is marked as a draft, routed to accountable SMEs and subjected to a second-read QA checklist.

## Production hardening checklist

Before any real organizational use, add:

1. Identity provider / SSO and multi-factor authentication.
2. Role-based access control and least privilege.
3. Encrypted managed database and encrypted backups.
4. Audit trail for source changes, model calls, approvals and releases.
5. Formal retention/deletion schedule and data-subject request procedures where applicable.
6. DLP, malware scanning and document classification.
7. Vendor/security assessment and DPA review for AI, hosting and database providers.
8. Data residency and cross-border transfer assessment.
9. Incident response and key-rotation procedures.
10. Rate limiting, abuse prevention and cost controls.
11. Model evaluation, hallucination testing, red-team tests and change management.
12. Formal approval of the source-of-truth library and source review dates.

## Legal frameworks

Depending on where and how the application is used, relevant obligations may include Brazil's LGPD, the EU GDPR, contractual confidentiality duties and sector-specific requirements. The correct production design depends on the actual controller/processor roles, data types, jurisdictions, hosting choices and contracts.
