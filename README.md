# AI-Assisted Deal Desk Intake, Routing & QA Workflow

## Version

**4.0 · Final GitHub-ready package**

A fictional portfolio proof of concept for Deal Desk / Legal Operations workflows. It demonstrates structured intake, deterministic risk triage, SME routing, canonical-source governance, privacy-aware AI drafting, deadline visibility, second-read QA, and an explicit human release gate.

## Why this project exists

The workflow is designed around a high-stakes operational problem: procurement, security, privacy, legal, commercial and product claims often need to be coordinated under hard external deadlines. AI can accelerate classification, retrieval, comparison and drafting, but it should not autonomously make or release material commitments.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app works without an API key using deterministic triage. To enable AI, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, add your OpenAI API key, and keep that real file out of GitHub.

## Recommended portfolio deployment

Use GitHub for the repository and Streamlit Community Cloud for the live application. Keep all data fictional. For a controlled AI demo, configure `APP_PASSWORD`, `OPENAI_API_KEY`, `OPENAI_MODEL`, and `MAX_AI_CALLS_PER_SESSION` in Streamlit's Secrets settings.

## Safety / privacy design

- No real customer data is required.
- Data is session-only by default; no database is configured.
- Pattern-based PII redaction runs before AI calls.
- AI receives only retrieved sources whose status is `Approved`.
- `store=False` is sent with OpenAI Responses API requests.
- The AI is instructed not to invent external claims or make final legal/security/privacy/commercial decisions.
- AI results are drafts; a human QA checklist and final approval gate are required.
- There is no autonomous Send/Submit function.
- Public AI use can be disabled; password-protected AI access and per-session call limits are supported.

## Important limitation

This is a portfolio/demo system, not a production Deal Desk platform. Pattern-based redaction is not a substitute for enterprise DLP. A production system should add SSO/RBAC, audit logs, encrypted managed storage, retention/deletion policies, vendor risk review, incident response, DLP/classification, monitoring, backups, data-residency decisions and formal privacy/security governance.

## Files

- `app.py` — the application
- `requirements.txt` — Python dependencies
- `.gitignore` — prevents secrets, caches and local/private files from being committed
- `.streamlit/config.toml` — safe Streamlit theme/server configuration
- `.streamlit/secrets.toml.example` — safe configuration template; never replace it in GitHub with a real secret file
- `data/README.md` — placeholder for fictional/demo data guidance
- `docs/SECURITY_PRIVACY.md` — security/privacy design notes
- `docs/DEPLOYMENT.md` — deployment instructions

## Disclaimer

All sample content is fictional. This project demonstrates transferable operational and AI-workflow skills and is not legal, security, privacy or compliance advice.
