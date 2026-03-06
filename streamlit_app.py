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

# Load .env for GOOGLE_API_KEY (Streamlit Cloud uses Secrets instead; this helps local run)
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

# SSL for Gemini (e.g. on some cloud environments)
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
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Session state for chat history and context_fund
if "messages" not in st.session_state:
    st.session_state.messages = []
if "context_fund" not in st.session_state:
    st.session_state.context_fund = None

# Header and disclaimer
st.title("MF FAQ Assistant")
st.caption("Facts-only FAQ for ICICI Prudential mutual fund schemes. No investment advice.")
st.markdown("---")

# Chat container
chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("source_url"):
                st.markdown(f"**Source:** [Link]({msg['source_url']})")

# Chat input
if prompt := st.chat_input("Type your question..."):
    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt, "source_url": None})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get bot response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = handle_chat(prompt, context_fund=st.session_state.context_fund)
            except Exception as e:
                result = {
                    "answer": f"Sorry, an error occurred: {str(e)}. Please try again or check the AMC website.",
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
            "source_url": source_url,
        })

st.markdown("---")
st.caption("Do not enter PAN, Aadhaar, account numbers, folio, OTP, email or phone.")

# Sidebar: Resources
with st.sidebar:
    st.header("Resources")
    st.markdown("[ICICI Prudential AMC](https://www.icicipruamc.com)")
    st.markdown("[INDmoney – Mutual Funds](https://www.indmoney.com/mutual-funds)")
    st.markdown("[KIM & SID Documents](https://www.icicipruamc.com/media-center/downloads)")
    st.markdown("[AMFI Investor Corner](https://www.amfiindia.com/investor-corner)")
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.session_state.context_fund = None
        st.rerun()
