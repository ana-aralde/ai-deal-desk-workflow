from __future__ import annotations

import json
import os
import re
import uuid
import hmac
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


APP_TITLE = "AI-Assisted Deal Desk Intake, Routing & QA Workflow"
APP_VERSION = "5.1"


# -----------------------------
# Configuration helpers
# -----------------------------
def secret(name: str, default: Any = None) -> Any:
    """Read from Streamlit secrets first, then environment variables."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, default)


def bool_secret(name: str, default: bool = False) -> bool:
    value = str(secret(name, str(default))).strip().lower()
    return value in {"1", "true", "yes", "y", "on"}


def int_secret(name: str, default: int) -> int:
    try:
        return int(secret(name, default))
    except Exception:
        return default


# -----------------------------
# Privacy / data minimization
# -----------------------------
PII_PATTERNS = [
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "[EMAIL_REDACTED]"),
    (re.compile(r"(?<!\d)(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}(?!\d)"), "[PHONE_REDACTED]"),
    (re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)"), "[CPF_REDACTED]"),
    (re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)"), "[CNPJ_REDACTED]"),
    (re.compile(r"(?<!\d)(?:\d[ -]*?){13,19}(?!\d)"), "[LONG_NUMBER_REDACTED]"),
]


def redact_common_pii(text: str) -> Tuple[str, int]:
    redacted = text or ""
    count = 0
    for pattern, replacement in PII_PATTERNS:
        redacted, n = pattern.subn(replacement, redacted)
        count += n
    return redacted, count


def truncate(text: str, max_chars: int = 6000) -> str:
    text = text or ""
    return text if len(text) <= max_chars else text[:max_chars] + "\n[TRUNCATED]"


# -----------------------------
# Domain rules
# -----------------------------
SME_MAP = {
    "Tender / RFP / Procurement Questionnaire": ["Deal Desk"],
    "Security Questionnaire": ["Security / GRC"],
    "Privacy / DPA": ["Privacy", "Legal"],
    "Contract / Legal Terms": ["Legal"],
    "Commercial / Pricing": ["Finance", "Sales"],
    "Vendor Onboarding": ["Deal Desk", "Finance"],
    "Attestation / Representation": ["Legal", "Deal Desk"],
    "Product Capability": ["Product"],
    "Infrastructure / Data Residency": ["Infrastructure", "Privacy"],
    "Other": ["Deal Desk"],
}

HIGH_RISK_CUES = [
    "data residency", "cross-border", "dpa", "privacy", "gdpr", "dora",
    "fedramp", "soc 2", "iso 27001", "iso 27701", "cyber essentials",
    "indemnity", "liability", "warranty", "audit right", "subprocessor",
    "certification", "roadmap", "guarantee", "breach", "security incident",
    "sanctions", "aml", "cft", "regulator", "government", "federal",
]

MEDIUM_RISK_CUES = [
    "insurance", "payment", "pricing", "renewal", "sla", "service level",
    "entity", "registration", "attestation", "representation", "tax",
]


def deterministic_triage(request_type: str, text: str, deadline: date) -> Dict[str, Any]:
    normalized = (text or "").lower()
    days_left = (deadline - date.today()).days
    high_hits = [cue for cue in HIGH_RISK_CUES if cue in normalized]
    med_hits = [cue for cue in MEDIUM_RISK_CUES if cue in normalized]

    if request_type in {"Privacy / DPA", "Contract / Legal Terms", "Security Questionnaire", "Infrastructure / Data Residency"}:
        review_path = "Enhanced"
    elif high_hits:
        review_path = "Enhanced"
    elif med_hits or request_type in {"Commercial / Pricing", "Attestation / Representation"}:
        review_path = "Standard"
    else:
        review_path = "Simplified"

    if days_left < 0:
        urgency = "Overdue"
    elif days_left <= 1:
        urgency = "Critical"
    elif days_left <= 3:
        urgency = "High"
    elif days_left <= 7:
        urgency = "Medium"
    else:
        urgency = "Normal"

    owners = list(SME_MAP.get(request_type, ["Deal Desk"]))
    if any(x in normalized for x in ["privacy", "dpa", "gdpr", "data residency", "cross-border"]):
        owners = sorted(set(owners + ["Privacy", "Legal"]))
    if any(x in normalized for x in ["security", "soc 2", "iso 27001", "fedramp", "cyber"]):
        owners = sorted(set(owners + ["Security / GRC"]))
    if any(x in normalized for x in ["pricing", "payment", "insurance"]):
        owners = sorted(set(owners + ["Finance"]))
    if any(x in normalized for x in ["roadmap", "capability", "feature"]):
        owners = sorted(set(owners + ["Product"]))

    return {
        "review_path": review_path,
        "urgency": urgency,
        "days_left": days_left,
        "suggested_owners": owners,
        "risk_cues": high_hits + med_hits,
    }


def keyword_relevance(query: str, source_text: str) -> float:
    stop = {"the", "and", "or", "of", "to", "a", "in", "for", "is", "are", "on", "with", "de", "e", "o", "a", "do", "da", "para"}
    q = {w for w in re.findall(r"[A-Za-zÀ-ÿ0-9_-]+", query.lower()) if len(w) > 2 and w not in stop}
    s = {w for w in re.findall(r"[A-Za-zÀ-ÿ0-9_-]+", source_text.lower()) if len(w) > 2 and w not in stop}
    if not q:
        return 0.0
    return len(q & s) / max(1, len(q))


def retrieve_sources(query: str, sources: List[Dict[str, Any]], limit: int = 4) -> List[Dict[str, Any]]:
    approved = [s for s in sources if s.get("status") == "Approved"]
    scored = [(keyword_relevance(query, s.get("content", "")), s) for s in approved]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for score, s in scored[:limit] if score > 0] or approved[: min(limit, len(approved))]


# -----------------------------
# AI service
# -----------------------------
def ai_available() -> bool:
    return bool(secret("OPENAI_API_KEY")) and OpenAI is not None


def ai_permitted() -> bool:
    """Allow paid AI only when explicitly public or unlocked for this browser session."""
    if bool_secret("ALLOW_PUBLIC_AI", False):
        return True
    required_code = secret("AI_DEMO_CODE")
    return bool(required_code) and bool(st.session_state.get("ai_unlocked", False))


def call_ai_analysis(request: Dict[str, Any], sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not ai_available():
        raise RuntimeError("OpenAI API key is not configured.")
    if not ai_permitted():
        raise RuntimeError("Live AI is locked for this session. Enter the demo access code in AI Review.")

    max_calls = int_secret("MAX_AI_CALLS_PER_SESSION", 3)
    used = st.session_state.get("ai_calls", 0)
    if used >= max_calls:
        raise RuntimeError(f"Session AI limit reached ({max_calls}).")

    source_payload = []
    total_redactions = 0
    for s in sources:
        clean, n = redact_common_pii(truncate(s.get("content", ""), 3500))
        total_redactions += n
        source_payload.append({
            "source_id": s.get("source_id"),
            "title": s.get("title"),
            "owner": s.get("owner"),
            "review_date": s.get("review_date"),
            "content": clean,
        })

    clean_question, n = redact_common_pii(truncate(request.get("description", ""), 6000))
    total_redactions += n

    prompt = {
        "request": {
            "request_type": request.get("request_type"),
            "jurisdiction": request.get("jurisdiction"),
            "entity": request.get("entity"),
            "deadline": str(request.get("deadline")),
            "description": clean_question,
        },
        "approved_sources": source_payload,
    }

    instructions = """
You are an AI assistant embedded in a Deal Desk workflow. You support intake, routing, drafting and QA, but you do not make final legal, security, privacy, commercial or product commitments.

Rules:
1. Use ONLY the approved_sources supplied in the input for externally material factual claims. Never invent certifications, legal entities, capabilities, dates, pricing, security controls, data residency, regulatory conclusions or contractual commitments.
2. If the approved sources are insufficient, say so explicitly and list the missing evidence.
3. Surface contradictions rather than resolving legal hierarchy or contractual precedence yourself.
4. Recommend accountable SME owners for material claims.
5. Treat the output as a draft requiring human validation and approval.
6. Return valid JSON only, with these keys: summary, review_path, risk_level, suggested_owners, detected_flags, missing_information, source_ids_used, draft_response, qa_checks, human_approval_required.
7. review_path must be one of Simplified, Standard, Enhanced. risk_level must be Low, Medium, High.
8. human_approval_required must always be true.
""".strip()

    client = OpenAI(api_key=secret("OPENAI_API_KEY"))
    model = secret("OPENAI_MODEL", "gpt-5.6-luna")
    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=json.dumps(prompt, ensure_ascii=False),
        reasoning={"effort": "low"},
        store=False,
    )
    st.session_state["ai_calls"] = used + 1

    text = response.output_text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {
            "summary": "The model returned non-JSON output; human review required.",
            "review_path": "Enhanced",
            "risk_level": "High",
            "suggested_owners": ["Deal Desk"],
            "detected_flags": ["AI output parsing failure"],
            "missing_information": [],
            "source_ids_used": [s.get("source_id") for s in sources],
            "draft_response": text,
            "qa_checks": ["Validate all claims manually"],
            "human_approval_required": True,
        }
    data["local_pii_redactions"] = total_redactions
    data["model"] = model
    return data


# -----------------------------
# State and sample data
# -----------------------------
def init_state() -> None:
    st.session_state.setdefault("requests", [])
    st.session_state.setdefault("sources", [])
    st.session_state.setdefault("ai_calls", 0)
    st.session_state.setdefault("ai_unlocked", False)


def load_demo_data() -> None:
    if st.session_state["requests"] or st.session_state["sources"]:
        return
    st.session_state["sources"] = [
        {
            "source_id": "SRC-001",
            "title": "Approved Security Statement - Fictional",
            "owner": "Security / GRC",
            "status": "Approved",
            "review_date": str(date.today() + timedelta(days=60)),
            "content": "Fictional demo source: The company maintains an information security program and requires Security/GRC approval before externally representing certification scope or control effectiveness.",
        },
        {
            "source_id": "SRC-002",
            "title": "Approved Privacy Statement - Fictional",
            "owner": "Privacy / Legal",
            "status": "Approved",
            "review_date": str(date.today() + timedelta(days=45)),
            "content": "Fictional demo source: Privacy and cross-border data transfer commitments must be validated by Privacy/Legal. The Deal Desk may reuse approved language only when the entity, service and jurisdiction match the source scope.",
        },
        {
            "source_id": "SRC-003",
            "title": "Product Capability Note - Fictional",
            "owner": "Product",
            "status": "Approved",
            "review_date": str(date.today() + timedelta(days=30)),
            "content": "Fictional demo source: Product capability and roadmap claims require Product-owner confirmation. Future features must not be represented as committed delivery dates unless specifically approved.",
        },
    ]
    st.session_state["requests"] = [
        {
            "request_id": "REQ-DEMO-01",
            "created_at": datetime.now().isoformat(timespec="minutes"),
            "customer": "Fictional European Bank",
            "entity": "EU Entity",
            "jurisdiction": "European Union",
            "request_type": "Security Questionnaire",
            "deadline": str(date.today() + timedelta(days=4)),
            "owner": "Deal Desk",
            "status": "In Review",
            "description": "Confirm current security certification scope and whether customer data can be hosted in the EU. Provide evidence and identify any claims requiring Security, Privacy or Legal validation.",
            "review_path": "Enhanced",
            "urgency": "Medium",
            "suggested_owners": ["Security / GRC", "Privacy", "Legal"],
            "risk_cues": ["certification", "data residency"],
            "ai_result": None,
            "qa": {},
        }
    ]


# -----------------------------
# UI components
# -----------------------------
def ai_access_panel() -> bool:
    """Render the live-AI access control without blocking the rest of the public app."""
    if not ai_available():
        st.info("Live AI is not configured yet. The deterministic workflow remains fully usable.")
        return False

    if bool_secret("ALLOW_PUBLIC_AI", False):
        st.warning("Live AI is currently public. For a portfolio deployment, use an access code to control API spend.")
        return True

    required_code = secret("AI_DEMO_CODE")
    if not required_code:
        st.info("Live AI is access-controlled and currently disabled. Configure AI_DEMO_CODE in Streamlit Secrets to enable it.")
        return False

    if st.session_state.get("ai_unlocked", False):
        st.success("Live AI demo unlocked for this browser session.")
        if st.button("Lock live AI", key="lock_live_ai"):
            st.session_state["ai_unlocked"] = False
            st.rerun()
        return True

    st.info("The workflow is public, but paid AI calls require a demo access code to prevent unauthorized API use.")
    entered = st.text_input("Live AI demo access code", type="password", key="ai_demo_code_input")
    if st.button("Unlock live AI", key="unlock_live_ai"):
        if hmac.compare_digest(str(entered), str(required_code)):
            st.session_state["ai_unlocked"] = True
            st.rerun()
        else:
            st.error("Incorrect demo access code.")
    return False


def sidebar() -> None:
    with st.sidebar:
        st.markdown(f"### {APP_TITLE}")
        st.caption(f"Portfolio proof of concept · v{APP_VERSION}")
        st.divider()
        st.write("**AI status**")
        if ai_available():
            st.success(f"Configured · {secret('OPENAI_MODEL', 'gpt-5.6-luna')}")
        else:
            st.warning("Not configured · rule engine still works")
        st.write(f"AI calls this session: {st.session_state.get('ai_calls', 0)} / {int_secret('MAX_AI_CALLS_PER_SESSION', 3)}")
        st.divider()
        if st.button("Load fictional demo data"):
            load_demo_data()
            st.rerun()
        if st.button("Clear session data"):
            st.session_state["requests"] = []
            st.session_state["sources"] = []
            st.session_state["ai_calls"] = 0
            st.rerun()
        st.caption("Data is held in the current Streamlit session only by default. Do not use real confidential customer data in the public portfolio demo.")


def dashboard_tab() -> None:
    requests = st.session_state["requests"]
    st.subheader("Operating dashboard")
    if not requests:
        st.info("No requests yet. Add one in Request Intake or load fictional demo data.")
        return

    today = date.today()
    enhanced = sum(1 for r in requests if r.get("review_path") == "Enhanced")
    open_items = sum(1 for r in requests if r.get("status") not in {"Released", "Closed"})
    due_3 = 0
    overdue = 0
    for r in requests:
        try:
            d = date.fromisoformat(str(r.get("deadline")))
            delta = (d - today).days
            if delta < 0:
                overdue += 1
            elif delta <= 3:
                due_3 += 1
        except Exception:
            pass

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Open requests", open_items)
    c2.metric("Enhanced review", enhanced)
    c3.metric("Due ≤ 3 days", due_3)
    c4.metric("Overdue", overdue)

    df = pd.DataFrame(requests)
    columns = [c for c in ["request_id", "customer", "request_type", "deadline", "review_path", "urgency", "status", "owner"] if c in df.columns]
    st.dataframe(df[columns], use_container_width=True, hide_index=True)

    st.download_button(
        "Export queue as CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="deal_desk_queue.csv",
        mime="text/csv",
    )


def intake_tab() -> None:
    st.subheader("1 · Structured request intake")
    st.caption("Captures the minimum facts needed to route ownership, deadlines and review depth before drafting begins.")
    with st.form("intake_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        customer = c1.text_input("Customer / requesting organization", placeholder="Fictional customer")
        entity = c2.text_input("Company legal entity / business unit", placeholder="US / UK / EU / Federal entity")
        jurisdiction = c1.text_input("Jurisdiction", placeholder="European Union")
        request_type = c2.selectbox("Request type", list(SME_MAP.keys()))
        deadline = c1.date_input("External deadline", value=date.today() + timedelta(days=7))
        owner = c2.text_input("Primary Deal Desk owner", value="Deal Desk")
        description = st.text_area("Requirement / question / scope", height=170, placeholder="Paste or summarize the request. Avoid confidential or personal data in a public demo.")
        consent = st.checkbox("I confirm this demo input contains no real confidential, privileged, personal or customer-sensitive information.")
        submitted = st.form_submit_button("Triage and add to queue", type="primary")

    if submitted:
        if not description.strip():
            st.error("Add a requirement or question.")
            return
        if not consent:
            st.error("Confirm the data-minimization statement before adding the request.")
            return
        triage = deterministic_triage(request_type, description, deadline)
        item = {
            "request_id": f"REQ-{uuid.uuid4().hex[:8].upper()}",
            "created_at": datetime.now().isoformat(timespec="minutes"),
            "customer": customer or "Fictional / not specified",
            "entity": entity or "Not specified",
            "jurisdiction": jurisdiction or "Not specified",
            "request_type": request_type,
            "deadline": str(deadline),
            "owner": owner or "Deal Desk",
            "status": "Intake",
            "description": description,
            **triage,
            "ai_result": None,
            "qa": {},
        }
        st.session_state["requests"].append(item)
        st.success(f"Added {item['request_id']} · {item['review_path']} review · {item['urgency']} urgency")
        st.write("Suggested owners:", ", ".join(item["suggested_owners"]))
        if item["risk_cues"]:
            st.write("Risk cues:", ", ".join(item["risk_cues"]))


def source_library_tab() -> None:
    st.subheader("2 · Canonical source library")
    st.caption("Only Approved sources are eligible for AI drafting. Draft or Deprecated material remains visible but is excluded from retrieval.")
    with st.form("source_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        title = c1.text_input("Source title")
        owner = c2.text_input("Accountable source owner", placeholder="Security / GRC")
        status = c3.selectbox("Status", ["Approved", "Draft", "Deprecated"])
        review_date = c1.date_input("Next review date", value=date.today() + timedelta(days=90))
        source_id = c2.text_input("Source ID", value=f"SRC-{uuid.uuid4().hex[:6].upper()}")
        content = st.text_area("Approved content / policy excerpt / validated answer", height=150)
        submit = st.form_submit_button("Add source")
    if submit:
        if not title or not content:
            st.error("Source title and content are required.")
        else:
            st.session_state["sources"].append({
                "source_id": source_id,
                "title": title,
                "owner": owner or "Unassigned",
                "status": status,
                "review_date": str(review_date),
                "content": content,
            })
            st.success("Source added.")

    if st.session_state["sources"]:
        sdf = pd.DataFrame(st.session_state["sources"])
        st.dataframe(sdf[["source_id", "title", "owner", "status", "review_date"]], use_container_width=True, hide_index=True)
        st.download_button("Export source register as CSV", sdf.to_csv(index=False).encode("utf-8"), "canonical_sources.csv", "text/csv")
    else:
        st.info("No sources. Load demo data or add an approved source.")


def ai_review_tab() -> None:
    st.subheader("3 · AI-assisted routing, evidence retrieval and drafting")
    requests = st.session_state["requests"]
    if not requests:
        st.info("Add a request first.")
        return
    labels = {r["request_id"]: f"{r['request_id']} · {r['request_type']} · due {r['deadline']}" for r in requests}
    req_id = st.selectbox("Select request", list(labels.keys()), format_func=lambda x: labels[x])
    req = next(r for r in requests if r["request_id"] == req_id)

    st.write("**Rule-based triage:**", req.get("review_path"), "|", req.get("urgency"))
    st.write("**Suggested SMEs:**", ", ".join(req.get("suggested_owners", [])))
    relevant = retrieve_sources(req.get("description", ""), st.session_state["sources"])
    st.write("**Retrieved approved sources:**", ", ".join(s.get("source_id", "") for s in relevant) if relevant else "None")

    with st.expander("Privacy pre-check", expanded=False):
        redacted, n = redact_common_pii(req.get("description", ""))
        st.write(f"Common PII patterns detected/redacted before API transmission: **{n}**")
        st.code(redacted[:2500] or "No text", language=None)
        st.caption("Pattern-based redaction reduces exposure but is not a complete DLP system. Production use should add enterprise DLP/classification controls.")

    live_ai_unlocked = ai_access_panel()
    confirm = st.checkbox("I understand AI output is a draft and requires human validation before any external use.", key=f"confirm_{req_id}")
    if st.button("Run AI review", type="primary", disabled=not (confirm and live_ai_unlocked)):
        if not relevant:
            st.warning("No Approved source is available. Add an approved source before using AI drafting.")
            return
        try:
            with st.spinner("Running privacy-aware AI review..."):
                result = call_ai_analysis(req, relevant)
            req["ai_result"] = result
            req["status"] = "In Review"
            st.success("AI review completed. Human approval is still required.")
        except Exception as exc:
            st.error(str(exc))

    result = req.get("ai_result")
    if result:
        c1, c2 = st.columns(2)
        c1.markdown(f"**AI review path:** {result.get('review_path') or 'Not provided'}")
        c2.markdown(f"**AI risk level:** {result.get('risk_level') or 'Not provided'}")
        st.write("**Summary**")
        st.write(result.get("summary"))
        st.write("**Flags**")
        st.write(result.get("detected_flags") or [])
        st.write("**Missing information**")
        st.write(result.get("missing_information") or [])
        st.write("**Source IDs used**")
        st.write(result.get("source_ids_used") or [])
        st.write("**Draft response — NOT APPROVED**")
        st.text_area("Draft", value=result.get("draft_response", ""), height=220, key=f"draft_{req_id}")
        st.info("The app intentionally does not provide an autonomous Send/Submit action.")


def qa_tab() -> None:
    st.subheader("4 · Second-read QA and human release gate")
    requests = st.session_state["requests"]
    if not requests:
        st.info("Add a request first.")
        return
    req_id = st.selectbox("Select request for QA", [r["request_id"] for r in requests], key="qa_req")
    req = next(r for r in requests if r["request_id"] == req_id)

    checks = [
        "Scope, customer, legal entity, jurisdiction and package version confirmed",
        "Deadline and portal/submission mechanics confirmed",
        "All required fields and attachments accounted for",
        "Material claims trace to Approved canonical sources",
        "Entity and certification distinctions verified",
        "Legal / Privacy / Security / Finance / Product approvals obtained where required",
        "Contradictory or stale sources resolved by accountable owner",
        "A second reader reviewed names, dates, figures, attachments and consistency",
        "Named final approver confirmed readiness",
        "Submission evidence / receipt will be retained after release",
    ]
    qa = req.setdefault("qa", {})
    for idx, check in enumerate(checks):
        qa[str(idx)] = st.checkbox(check, value=qa.get(str(idx), False), key=f"qa_{req_id}_{idx}")

    approved = all(qa.values()) if qa else False
    if approved:
        st.success("QA gate passed. A human final approver may release the submission outside this demo.")
        if st.button("Mark as Released (demo status only)"):
            req["status"] = "Released"
            st.rerun()
    else:
        st.warning("HOLD: release gate is not complete.")


def architecture_tab() -> None:
    st.subheader("5 · Why the controls exist")
    st.markdown(
        """
**Design principle:** AI should create leverage around repetitive, information-intensive work while accountable humans retain final authority over externally material claims and commitments.

- **Structured intake** reduces ambiguity before work starts and makes deadlines, jurisdiction, entity and owner explicit.
- **Deterministic triage** creates a transparent baseline that does not depend on model output.
- **Canonical-source library** prevents plausible-but-unverified answers from becoming customer-facing commitments.
- **AI retrieval and drafting** accelerates research and first drafts, but only from Approved material.
- **PII redaction + data minimization** reduces unnecessary personal-data exposure before API calls.
- **SME routing** makes the true accountable owner visible early enough to unblock the request.
- **Second-read QA** detects contradictions, missing evidence and wrong entity/certification details before release.
- **Human release gate** prevents autonomous external submission and preserves accountability.
- **Session-only storage by default** makes the public portfolio demo safer; production systems should use authenticated, access-controlled, audited storage.
        """
    )
    st.warning("Portfolio demo only. Do not use this deployment for confidential customer, legal, security, HR or personal data.")


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="⚙️", layout="wide")
    init_state()
    sidebar()

    st.title(APP_TITLE)
    st.write("A fictional, human-in-the-loop proof of concept for structured intake, risk-based routing, canonical-source governance, AI-assisted drafting, deadline control and release QA.")
    st.caption("All demo content is fictional. The application deliberately separates AI assistance from accountable human approval.")

    tabs = st.tabs(["Dashboard", "Request Intake", "Source Library", "AI Review", "QA & Release", "Architecture"])

    # Render form-driven tabs first so newly submitted data is available
    # to the Dashboard during the same Streamlit rerun. The visual tab
    # order remains unchanged.
    with tabs[1]: intake_tab()
    with tabs[2]: source_library_tab()
    with tabs[3]: ai_review_tab()
    with tabs[4]: qa_tab()
    with tabs[5]: architecture_tab()
    with tabs[0]: dashboard_tab()


if __name__ == "__main__":
    main()
