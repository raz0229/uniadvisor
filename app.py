"""Streamlit GUI: streamlit run app.py"""
import json
import streamlit as st
import config, memory, rag
from agent import AdvisorAgent

st.set_page_config(page_title="UniAdvisor", page_icon="🎓", layout="wide")
st.markdown("""
<style>
.stApp{background:linear-gradient(160deg,#0f172a 0%,#1e1b4b 100%);}
section[data-testid="stSidebar"]{background:#111827;border-right:1px solid #334155;}
.hero{padding:18px 24px;border-radius:18px;background:linear-gradient(90deg,#6366f1,#8b5cf6,#ec4899);color:white;margin-bottom:14px}
.hero h1{margin:0;font-size:1.9rem;color:white}.hero p{margin:4px 0 0;opacity:.9}
.stChatMessage{background:rgba(255,255,255,.05);border-radius:16px;border:1px solid rgba(255,255,255,.08)}
.chip{display:inline-block;padding:2px 10px;border-radius:99px;font-size:.75rem;font-weight:600;margin-right:6px}
.RAG{background:#0ea5e9;color:#fff}.MCP{background:#10b981;color:#fff}.MEMORY{background:#f59e0b;color:#111}
.card{padding:10px 14px;border-radius:12px;background:rgba(255,255,255,.06);margin-bottom:8px;font-size:.85rem}
</style>""", unsafe_allow_html=True)

DATA = json.load(open(config.CATALOG_PATH, encoding="utf-8"))["students"]

# ---------- sidebar ----------
with st.sidebar:
    st.markdown("## 🎓 UniAdvisor")
    sid = st.selectbox("Student", list(DATA), format_func=lambda k: f"{k} · {DATA[k]['name']}")
    s = DATA[sid]
    st.markdown(f"<div class='card'><b>{s['name']}</b><br>{s['program']} · Semester {s['semester']}<br>"
                f"{len(s['completed'])} courses completed</div>", unsafe_allow_html=True)
    if st.button("➕ New session (clears short-term memory)", use_container_width=True):
        st.session_state.pop("agent", None); st.session_state.pop("msgs", None); st.rerun()
    st.markdown("#### 🧠 Long-term memory")
    mems = memory.recall(sid)
    for m in mems: st.markdown(f"<div class='card'>• {m}</div>", unsafe_allow_html=True)
    if not mems: st.caption("Nothing stored yet. Tell the advisor your goals!")
    if mems and st.button("Forget this student", use_container_width=True):
        memory.clear(sid); st.rerun()
    st.markdown("#### 📚 Knowledge base")
    if st.button("Ingest / rebuild RAG index", use_container_width=True):
        with st.spinner("Chunking & embedding documents…"):
            try: d, c = rag.ingest(); st.success(f"{d} documents → {c} chunks")
            except Exception as e: st.error(e)
    st.caption("✅ Index ready" if rag.is_ready() else "⚠️ Index empty – click ingest")
    if not config.API_KEY or config.API_KEY.startswith("your_"):
        st.error("Set GEMINI_API_KEY in the .env file, then restart.")

if st.session_state.get("sid") != sid:
    st.session_state.update(sid=sid, agent=AdvisorAgent(sid), msgs=[])
st.session_state.setdefault("agent", AdvisorAgent(sid)); st.session_state.setdefault("msgs", [])

# ---------- main ----------
st.markdown("<div class='hero'><h1>Intelligent University Academic Advisor</h1>"
            "<p>Recommendations grounded in regulations (RAG), live records (MCP) and your history (memory). "
            "Final registration always needs human advisor approval.</p></div>", unsafe_allow_html=True)


def show_trace(trace):
    for t in trace:
        with st.expander(f"🔧 {t['tool']}  ·  {t['kind']}"):
            st.markdown(f"<span class='chip {t['kind']}'>{t['kind']}</span>", unsafe_allow_html=True)
            st.code(json.dumps(t["args"], indent=2), language="json")
            st.text(t["result"][:1800])


for m in st.session_state.msgs:
    with st.chat_message(m["role"]): 
        st.markdown(m["text"]); show_trace(m.get("trace", []))

if not st.session_state.msgs:
    c = st.columns(3)
    ideas = ["Which courses can I take next semester?", "Can I take Machine Learning? What are the rules?",
             "I'm interested in NLP and prefer a light 12-credit load."]
    for col, q in zip(c, ideas):
        if col.button(q, use_container_width=True): st.session_state.pending = q

q = st.chat_input("Ask your academic advisor…") or st.session_state.pop("pending", None)
if q:
    st.session_state.msgs.append({"role": "user", "text": q})
    with st.chat_message("user"): st.markdown(q)
    with st.chat_message("assistant"):
        with st.spinner("Thinking, retrieving, calling tools…"):
            try: text, trace = st.session_state.agent.chat(q)
            except Exception as e: text, trace = f"⚠️ Error: {e}", []
        st.markdown(text); show_trace(trace)
    st.session_state.msgs.append({"role": "assistant", "text": text, "trace": trace})
    st.rerun() if any(t["kind"] == "MEMORY" for t in trace) else None
