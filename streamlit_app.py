"""
MF FAQ Assistant — Streamlit app for deployment on Streamlit Cloud.
Run from repo root: streamlit run streamlit_app.py
Uses the same chat logic as Phase 4 (handle_chat); no FastAPI.
"""

import os
import sys
from pathlib import Path

# Repo root = directory containing this file
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

# Load .env for GOOGLE_API_KEY (Streamlit Cloud uses Secrets instead)
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

# SSL fix for Gemini
try:
    import ssl
    import certifi
    ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
except Exception:
    pass

import streamlit as st
from Phase4_Backend_API.chat import handle_chat

st.set_page_config(
    page_title="Mutual Fund FAQ Assistant",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------- UI THEME ---------------- #

st.markdown("""
<style>

/* ---------- MAIN APP BACKGROUND ---------- */

.stApp{
background: linear-gradient(180deg,#f8f6f2 0%, #efe8da 100%);
font-family: "Segoe UI", system-ui, sans-serif;
}

/* ---------- MAIN CONTAINER ---------- */

.block-container{
max-width:900px;
margin:auto;
padding:2rem;

background:white;

border-radius:14px;

box-shadow:
0 6px 18px rgba(0,0,0,0.08);

border:1px solid #e6dcc8;
}

/* ---------- TITLE ---------- */

h1{
text-align:center;
font-weight:700;
color:#6b4c1e;
letter-spacing:0.5px;
}

/* ---------- CAPTION ---------- */

.stCaption{
text-align:center;
color:#6f6f6f;
font-size:0.9rem;
}

/* ---------- CHAT MESSAGE STYLE ---------- */

[data-testid="stChatMessage"]{
padding:14px;
border-radius:10px;
margin-bottom:10px;
border:1px solid #ece6db;
}

/* USER MESSAGE */

[data-testid="stChatMessage"]:has(div[data-testid="user-avatar"]){
background:#faf8f4;
}

/* ASSISTANT MESSAGE */

[data-testid="stChatMessage"]:has(div[data-testid="assistant-avatar"]){
background:#f3efe7;
}

/* ---------- INPUT BOX ---------- */

textarea{
border-radius:8px !important;
border:1px solid #cbbf9e !important;
background:white !important;
}

/* ---------- BUTTON ---------- */

.stButton>button{
background:#b8963f;
color:white;
border:none;
border-radius:8px;
padding:6px 14px;
font-weight:600;
}

.stButton>button:hover{
background:#a48332;
}

/* ---------- SIDEBAR ---------- */

section[data-testid="stSidebar"]{
background:#faf7f1;
border-right:1px solid #e6dcc8;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3{
color:#6b4c1e;
}

section[data-testid="stSidebar"] a{
color:#7a5b2e;
font-weight:500;
}

/* ---------- DIVIDER ---------- */

hr{
border:none;
border-top:1px solid #e6dcc8;
margin:1.2rem 0;
}

</style>
""", unsafe_allow_html=True)

# ---------------- SESSION STATE ---------------- #

if "messages" not in st.session_state:
    st.session_state.messages = []

if "context_fund" not in st.session_state:
    st.session_state.context_fund = None

# ---------------- HEADER ---------------- #

st.title("📊 Mutaul Fund FAQ Assistant")

st.caption(
    "<p style='text-align: center; color: brown; font-size: 0.8rem;'>"
    "Factual Answers Only - Mutual Fund FAQ Assistant • Expense Ratio • NAV • SIP • Riskometer • Benchmark"
    "</p>", 
    unsafe_allow_html=True
)


# ---------------- CHAT HISTORY ---------------- #

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("source_url"):
            st.markdown(f"**Source:** [Link]({msg['source_url']})")

# ---------------- CHAT INPUT ---------------- #

if prompt := st.chat_input("Ask about expense ratio, NAV, SIP, riskometer..."):

    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
        "source_url": None
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🔎 Searching official AMC documents..."):

            try:
                result = handle_chat(
                    prompt,
                    context_fund=st.session_state.context_fund
                )

            except Exception as e:
                result = {
                    "answer": f"Sorry, an error occurred: {str(e)}. Please check the AMC website.",
                    "source_url": "https://www.icicipruamc.com",
                    "refused": False,
                }

        answer = result.get("answer", "")
        source_url = result.get("source_url", "")

        if result.get("context_fund"):
            st.session_state.context_fund = result["context_fund"]

        st.markdown(answer)

        if source_url:
            st.markdown(f"**Source:** [Link]({source_url})")

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "source_url": source_url
        })

# ---------------- FOOTER ---------------- #



st.caption(
    "<p style='text-align: center; color: brown; font-size: 0.8rem;'>"
    "⚠️ Do not enter PAN, Aadhaar, account numbers, folio number, OTP, email or phone."
    "</p>", 
    unsafe_allow_html=True
)

# ---------------- SIDEBAR ---------------- #

with st.sidebar:

    st.header("📚 Investor Resources")

    st.markdown("### Official Sources")

    st.markdown("🔗 [ICICI Prudential AMC](https://www.icicipruamc.com)")
    st.markdown("🔗 [INDmoney – Mutual Funds](https://www.indmoney.com/mutual-funds)")
    st.markdown("🔗 [KIM & SID Documents](https://www.icicipruamc.com/media-center/downloads)")
    st.markdown("🔗 [AMFI Investor Corner](https://www.amfiindia.com/investor-corner)")

    st.markdown("---")

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.session_state.context_fund = None
        st.rerun()
