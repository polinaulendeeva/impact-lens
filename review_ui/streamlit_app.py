import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so "app" can be imported

import streamlit as st
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Assessment, Chunk, Company, GuardrailEvent, Review, Theme

st.set_page_config(page_title="Impact Lens review", layout="wide")
st.title("Impact Lens: review assessments")

# ---- sidebar -------------------------------------------------------------
reviewer = st.sidebar.text_input("Reviewer name")
with SessionLocal() as s:
    versions = s.scalars(
        select(Assessment.prompt_version).distinct().order_by(Assessment.prompt_version.desc())
    ).all()
version = st.sidebar.selectbox("Prompt version", versions)
show = st.sidebar.radio("Show", ["Pending", "Reviewed", "All"])
hide_zero = st.sidebar.checkbox("Hide score 0", value=True)


def load(version):
    with SessionLocal() as s:
        rows = s.execute(
            select(Assessment, Company.name, Theme.name)
            .join(Company, Company.id == Assessment.company_id)
            .join(Theme, Theme.id == Assessment.theme_id)
            .where(Assessment.prompt_version == version)
            .order_by(Company.name, Theme.name)
        ).all()
        history = {}
        for r in s.scalars(select(Review).order_by(Review.created_at)).all():
            history.setdefault(r.assessment_id, []).append(r)
        s.expunge_all()
    return rows, history


def final_score(a, past):
    """The score after review: the model's if approved, the reviewer's if edited."""
    if not past:
        return "pending"
    last = past[-1]
    if last.decision == "edit":
        return last.edited_score
    if last.decision == "approve":
        return a.score
    return "rejected"


rows, history = load(version)
reviewed = sum(1 for a, _, _ in rows if a.id in history)
st.sidebar.metric("Reviewed", f"{reviewed} of {len(rows)}")

items = []
for a, company, theme in rows:
    past = history.get(a.id, [])
    if hide_zero and a.score == 0:
        continue
    if show == "Pending" and past:
        continue
    if show == "Reviewed" and not past:
        continue
    items.append((a, company, theme, past))

tab_review, tab_rejected = st.tabs(["Assessments", "Rejected by guardrails"])

# ---- assessments ---------------------------------------------------------
with tab_review:
    if not items:
        st.info("Nothing to show with these filters.")
    else:
        def label(i):
            a, company, theme, past = items[i]
            if not past:
                return f"{company} / {theme}  (model score {a.score}, pending)"
            last = past[-1]
            if last.decision == "edit":
                return f"{company} / {theme}  (model score {a.score}, edited to {last.edited_score})"
            done = {"approve": "approved", "reject": "rejected"}[last.decision]
            return f"{company} / {theme}  (model score {a.score}, {done})"

        idx = st.selectbox("Assessment", range(len(items)), format_func=label)
        a, company, theme, past = items[idx]
        left, right = st.columns([3, 2])

        with left:
            st.subheader(f"{company}: {theme}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Model score", a.score)
            c2.metric("After review", final_score(a, past))
            c3.metric("Confidence", a.confidence or "n/a")
            c4.metric("Revenue share",
                      f"{a.revenue_share_pct:g}%" if a.revenue_share_pct is not None else "not stated")
            st.write(a.rationale)
            st.caption(f"Model {a.model}, prompt {a.prompt_version}, {a.created_at:%Y-%m-%d %H:%M}")

            st.markdown("**Evidence**")
            if not a.citations:
                st.write("No citations.")
            with SessionLocal() as s:
                for c in a.citations:
                    chunk = s.get(Chunk, c["chunk_id"])
                    with st.expander(f'Page {c["page"]}: "{c["quote"][:90]}"'):
                        st.markdown(f'> {c["quote"]}')
                        st.caption("Full passage")
                        st.write(chunk.text if chunk else "Passage not found")

        with right:
            st.markdown("**Your decision**")
            with st.form(f"review-{a.id}", clear_on_submit=True):
                decision = st.radio("Decision", ["approve", "edit", "reject"], horizontal=True)
                new_score = st.selectbox("Corrected score (used for edit)", [0, 1, 2, 3], index=a.score)
                reason = st.text_area("Reason (required for edit and reject)")
                if st.form_submit_button("Save decision"):
                    if not reviewer.strip():
                        st.error("Enter your name in the sidebar first.")
                    elif decision != "approve" and not reason.strip():
                        st.error("Give a reason for an edit or a rejection.")
                    else:
                        with SessionLocal() as s:
                            s.add(Review(
                                assessment_id=a.id,
                                reviewer=reviewer.strip(),
                                decision=decision,
                                edited_score=new_score if decision == "edit" else None,
                                reason=reason.strip() or None,
                            ))
                            s.commit()
                        st.rerun()

            st.markdown("**History**")
            if not past:
                st.write("No decisions yet.")
            for r in reversed(past):
                change = f" to score {r.edited_score}" if r.decision == "edit" else ""
                st.write(f"{r.created_at:%Y-%m-%d %H:%M}, {r.reviewer}: **{r.decision}**{change}")
                if r.reason:
                    st.caption(r.reason)

# ---- rejected ------------------------------------------------------------
with tab_rejected:
    st.write("Answers the guardrails refused to store. Each needs a person to look at it.")
    with SessionLocal() as s:
        events = s.execute(
            select(GuardrailEvent.created_at, Company.name, Theme.code,
                   GuardrailEvent.rule, GuardrailEvent.detail)
            .join(Company, Company.id == GuardrailEvent.company_id)
            .join(Theme, Theme.id == GuardrailEvent.theme_id)
            .order_by(GuardrailEvent.created_at.desc())
        ).all()
    st.dataframe(
        [{"When": f"{e[0]:%Y-%m-%d %H:%M}", "Company": e[1], "Theme": e[2],
          "Rule": e[3], "Detail": e[4]} for e in events],
        use_container_width=True,
    )