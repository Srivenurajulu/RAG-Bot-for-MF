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
    page_title="MF FAQ Assistant",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------- UI THEME ---------------- #

st.markdown("""
<style>

/* Animated red-gold gradient background */
.stApp{
background: linear-gradient(-45deg,#6b0000,#b30000,#ffcc33,#ffd700);
background-size:400% 400%;
animation:gradientMove 12s ease infinite;
}

@keyframes gradientMove{
0%{background-position:0% 50%;}
50%{background-position:100% 50%;}
100%{background-position:0% 50%;}
}

/* Glass container */
.block-container{
background: rgba(0,0,0,0.35);
padding:2rem;
border-radius:20px;
backdrop-filter: blur(10px);
border:1px solid rgba(255,215,0,0.4);
box-shadow:0 10px 40px rgba(0,0,0,0.6);
}

/* Title */
h1{
color:#FFD700 !important;
text-align:center;
font-weight:800;
letter-spacing:1px;
}

/* Caption */
.stCaption{
color:#fff4cc !important;
text-align:center;
}

/* Chat bubbles */
[data-testid="stChatMessage"]{
border-radius:14px;
padding:14px;
margin-bottom:10px;
border:1px solid rgba(255,215,0,0.4);
}

/* Assistant message */
[data-testid="stChatMessage"]:has(div[data-testid="assistant-avatar"]){
background:rgba(255,215,0,0.15);
}

/* User message */
[data-testid="stChatMessage"]:has(div[data-testid="user-avatar"]){
background:rgba(255,0,0,0.25);
}

/* Chat input */
textarea{
border-radius:10px !important;
border:2px solid #FFD700 !important;
background:rgba(0,0,0,0.4) !important;
color:white !important;
}

/* Buttons */
.stButton>button{
background:linear-gradient(135deg,#FFD700,#ff4d4d);
color:#5a0000;
font-weight:700;
border-radius:10px;
border:none;
}

.stButton>button:hover{
transform:scale(1.05);
box-shadow:0 0 12px gold;
}

/* Sidebar */
section[data-testid="stSidebar"]{
background:linear-gradient(180deg,#7a0000,#b30000);
color:white;
}

section[data-testid="stSidebar"] a{
color:#FFD700;
font-weight:600;
}

hr{
border:1px solid rgba(255,215,0,0.5);
}

</style>
""", unsafe_allow_html=True)

# ---------------- SESSION STATE ---------------- #

if "messages" not in st.session_state:
    st.session_state.messages = []

if "context_fund" not in st.session_state:
    st.session_state.context_fund = None

# ---------------- HEADER ---------------- #

st.title("📊 ICICI Prudential MF FAQ Assistant")

st.caption(
"Facts-Only Mutual Fund FAQ Assistant • Expense Ratio • NAV • SIP • Riskometer • Benchmark"
)

st.markdown("---")

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

st.markdown("---")

st.caption(
"⚠️ Do not enter PAN, Aadhaar, account numbers, folio numbers, OTP, email or phone."
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
