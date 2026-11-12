"""Streamlit UI for the Enterprise Knowledge Intelligence & Decision Copilot."""
import traceback
from pathlib import Path

import pandas as pd
import streamlit as st

from config import LLM_MODEL, LLM_PROVIDER
from ingestion import SUPPORTED, ingest_file
from llm import LLM
from rag import RAGEngine
from theme import apply_theme, hero, stat_cards
from vectorstore import VectorStore

st.set_page_config(page_title="Enterprise Knowledge Copilot", page_icon="⚡", layout="wide")
apply_theme()

THEME_TOML = """[theme]
base = "dark"
primaryColor = "#19e3ff"
backgroundColor = "#030712"
secondaryBackgroundColor = "#07142b"
textColor = "#d6f4ff"
font = "sans serif"

[client]
toolbarMode = "minimal"

[server]
showEmailPrompt = false
"""


def check_theme_config():
    """Streamlit colours (tags, tab underline, inputs) come from .streamlit/config.toml, not from CSS.
    If that file is missing, or the app was started from another folder, tell the user how to fix it."""
    cfg = Path(__file__).parent / ".streamlit" / "config.toml"
    created = not cfg.exists()
    if created:
        cfg.parent.mkdir(exist_ok=True)
        cfg.write_text(THEME_TOML, encoding="utf-8")
    if created:
        st.warning("The theme file `.streamlit/config.toml` was missing, so I created it. "
                   "Stop the app (Ctrl+C) and start it again once to apply the full blue theme.")
    elif str(st.get_option("theme.primaryColor")).lower() != "#19e3ff":
        st.warning("Streamlit did not load the theme file, so some colours are still default (red tags, red tab "
                   "underline). Stop the app (Ctrl+C), `cd` into the project folder (the one that contains "
                   "`app.py` and `.streamlit`) and run `python -m streamlit run app.py` again.")


check_theme_config()

AVATARS = {"user": "🧑‍💻", "assistant": "🤖"}


# Streamlit keeps cached objects alive across code edits, so an updated llm.py/rag.py would be ignored
# until a full restart. Keying the cache on the newest .py modification time rebuilds the engine
# automatically whenever any source file changes.
CODE_VERSION = max(p.stat().st_mtime for p in Path(__file__).parent.glob("*.py"))


@st.cache_resource(show_spinner="Loading models and vector store…")
def get_engine(code_version: float):
    store = VectorStore()
    return store, RAGEngine(store, LLM())


try:
    store, engine = get_engine(CODE_VERSION)
except Exception as e:
    st.error(f"Startup error: {e}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []


def render_sources(sources, only_cited=False):
    if not sources:
        return
    shown = [s for s in sources if s.get("cited", True)] if only_cited else sources
    shown = shown or sources
    with st.expander(f"Sources ({len(shown)})"):
        for s in shown:
            tag = "cited in answer" if s.get("cited") else "retrieved"
            st.markdown(f"**[{s['id']}] {s['label']}**  \n{s['section'] or 'No section'}, {tag}, "
                        f"match score {s['similarity']:.2f}")
            st.caption(s["text"][:700] + ("…" if len(s["text"]) > 700 else ""))


def show_error(e: Exception):
    """Show a readable error and keep the full traceback (also printed to the terminal)."""
    traceback.print_exc()
    st.error(f"{type(e).__name__}: {e}")
    with st.expander("Technical details"):
        st.code(traceback.format_exc())


def badge(level: str):
    st.markdown(f'<span class="badge {level}">Confidence: {level}</span>', unsafe_allow_html=True)


# ======================= SIDEBAR =======================
with st.sidebar:
    st.markdown('<div class="side-title">Knowledge base</div>'
                '<div class="side-sub">Upload documents, then choose what to search.</div>',
                unsafe_allow_html=True)

    files = st.file_uploader("Upload documents", type=sorted(SUPPORTED), accept_multiple_files=True)
    if files and st.button("Index documents", width="stretch", type="primary"):
        for f in files:
            try:
                with st.spinner(f"Indexing {f.name}…"):
                    _, n, status = ingest_file(store, f.name, f.getvalue())
                {"indexed": st.success, "duplicate": st.info, "empty": st.warning}[status](
                    f"{f.name}: {status}" + (f" ({n} passages)" if n else ""))
            except Exception as e:
                msg = str(e)
                if "readonly" in msg.lower() or "1032" in msg:
                    st.error(f"{f.name}: the local database is locked or read-only. Stop every running copy "
                             "of this app, delete the data/chroma folder, make sure the project is not inside "
                             "OneDrive, then restart and index again.")
                else:
                    st.error(f"{f.name}: {e}")

    docs = store.list_documents()
    st.divider()
    if docs:
        name_by_id = {d["doc_id"]: d["filename"] for d in docs}
        active_ids = st.multiselect(
            "Documents to search", options=list(name_by_id),
            default=list(name_by_id), format_func=lambda i: name_by_id[i])
        with st.expander("Manage documents"):
            to_del = st.selectbox("Delete a document", options=list(name_by_id),
                                  format_func=lambda i: name_by_id[i])
            if st.button("Delete document"):
                store.delete_document(to_del)
                st.rerun()
    else:
        active_ids, name_by_id = [], {}
        st.info("No documents yet. Upload a file to begin.")

    with st.expander("Model routing"):
        st.caption("If a model hits a limit or goes down, the next one answers automatically.")
        for s in engine.llm.status():
            st.markdown(f"**{s['model']}**  \n{s['state']}")

    if st.button("Clear chat", width="stretch"):
        st.session_state.messages = []
        st.rerun()

# ======================= MAIN =======================
hero(LLM_PROVIDER, LLM_MODEL)

if not docs:
    st.info("Upload and index your documents in the sidebar to get started.")
    st.stop()

stat_cards(len(docs), sum(d["chunks"] for d in docs), len(active_ids))

tab_chat, tab_sum, tab_cmp, tab_act = st.tabs(["Ask", "Summarise", "Compare", "Actions and recommendations"])

# ---------- Chat ----------
with tab_chat:
    for m in st.session_state.messages:
        with st.chat_message(m["role"], avatar=AVATARS[m["role"]]):
            st.markdown(m["content"])
            if m["role"] == "assistant" and m.get("confidence"):
                badge(m["confidence"])
                if m.get("model"):
                    st.caption(f"Answered by {m['model']}")
                render_sources(m.get("sources"))

    if q := st.chat_input("Ask a question about your documents…"):
        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user", avatar=AVATARS["user"]):
            st.markdown(q)
        with st.chat_message("assistant", avatar=AVATARS["assistant"]):
            if not active_ids:
                res = {"answer": "Select at least one document to search in the sidebar.",
                       "sources": [], "confidence": "Low"}
            else:
                with st.spinner("Searching documents…"):
                    try:
                        res = engine.answer(q, history, active_ids)
                    except Exception as e:
                        traceback.print_exc()
                        res = {"answer": f"⚠️ Error ({type(e).__name__}): {e}", "sources": [], "confidence": "Low"}
            model_used = engine.llm.last_used if res.get("sources") else ""
            st.markdown(res["answer"])
            badge(res["confidence"])
            if model_used:
                st.caption(f"Answered by {model_used}")
            render_sources(res["sources"])
        st.session_state.messages.append({"role": "assistant", "content": res["answer"],
                                          "sources": res["sources"], "confidence": res["confidence"],
                                          "model": model_used})

# ---------- Summarise ----------
with tab_sum:
    c1, c2 = st.columns([2, 1])
    doc = c1.selectbox("Document", options=list(name_by_id), format_func=lambda i: name_by_id[i], key="sum_doc")
    style = c2.selectbox("Style", ["Executive summary", "Detailed summary", "Key rules & definitions"])
    if st.button("Generate summary", type="primary"):
        with st.spinner("Summarising…"):
            try:
                text = engine.summarize(doc, style)
                st.markdown(text)
                st.download_button("Download summary", text, file_name="summary.md")
            except Exception as e:
                show_error(e)

# ---------- Compare ----------
with tab_cmp:
    sel = st.multiselect("Select 2 or more documents", options=list(name_by_id),
                         format_func=lambda i: name_by_id[i], key="cmp_docs")
    topic = st.text_input("Compare on topic (optional)",
                          placeholder="e.g. leave entitlements, approval process")
    if st.button("Compare documents", type="primary"):
        if len(sel) < 2:
            st.warning("Select at least two documents.")
        else:
            with st.spinner("Reading each document and comparing…"):
                try:
                    res = engine.compare(sel, topic.strip() or "key rules, entitlements, limits, deadlines and responsibilities")
                    st.markdown(res["answer"])
                    render_sources(res["sources"])
                    st.download_button("Download comparison", res["answer"], file_name="comparison.md")
                except Exception as e:
                    show_error(e)

# ---------- Actions ----------
with tab_act:
    goal = st.text_area("Describe your situation or goal (optional)",
                        placeholder="e.g. We are onboarding 10 new hires next month. What must HR do?")
    if st.button("Generate action plan", type="primary"):
        if not active_ids:
            st.warning("Select at least one document to search.")
        else:
            with st.spinner("Analysing documents…"):
                try:
                    res = engine.action_items(active_ids, goal)
                    st.subheader("Summary")
                    st.write(res.get("summary", ""))
                    items = res.get("action_items", [])
                    if items:
                        st.subheader("Action items")
                        df = pd.DataFrame(items)
                        st.dataframe(df, width="stretch", hide_index=True)
                        st.download_button("Download CSV", df.to_csv(index=False), file_name="action_items.csv")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader("Recommendations")
                        for r in res.get("recommendations", []):
                            st.markdown(f"- {r}")
                    with c2:
                        st.subheader("Risks")
                        for r in res.get("risks", []):
                            st.markdown(f"- {r}")
                    render_sources(res.get("sources"))
                except Exception as e:
                    show_error(e)