# Deployment instructions — Backend (Streamlit) + Frontend (Vercel)

This document gives **clear steps** to host your project with the **backend on Streamlit** and the **frontend on Vercel**. No implementation is done here; follow these when you are ready to deploy.

---

## Important: How “backend” and “frontend” fit together

- **Current setup:** A **FastAPI** app (Phase 4) serves both the API (`POST /chat`, `GET /api/sources`, `GET /api/funds-by-type`, `GET /health`) and the static Phase 5 frontend from one server.
- **Streamlit** does not expose REST APIs like FastAPI. A Streamlit app is a web app with its own UI (forms, chat, etc.) that runs your Python code in the cloud.
- **Vercel** is good for **static sites** (HTML/JS/CSS). Your Phase 5 frontend is static and expects an **API base URL** to call (e.g. `POST /chat`).

So you have two deployment patterns:

| Pattern | Backend | Frontend | Use when |
|--------|---------|----------|----------|
| **A** | **Streamlit** (chat UI + all logic in one app) | **Vercel** = landing page that links to the Streamlit app | You want one “chat app” on Streamlit and a separate marketing/landing site on Vercel. |
| **B** | **FastAPI** on Railway/Render (API only) | **Vercel** = Phase 5 static site calling that API | You want to keep the existing Phase 5 chat UI and only move it to Vercel; the “backend” is the FastAPI API. |

**“Backend on Streamlit”** in this doc means: **Pattern A** — the chat and all backend logic (RAG, fast_lookup, classifier, etc.) run **inside a Streamlit app** on Streamlit Cloud. There is no separate REST API from Streamlit unless you add one (e.g. a separate FastAPI service).

**“Frontend on Vercel”** means: deploy your **Phase 5 static files** (or a landing page) on Vercel. If that frontend is the **chat UI** that calls `POST /chat`, it needs an API URL — which Streamlit does not provide. So for the **existing Phase 5 chat UI on Vercel** you need **Pattern B** (FastAPI hosted elsewhere). For **Pattern A**, Vercel hosts a **landing page** that links to the Streamlit app.

Below: **Part 1** = Streamlit (backend + chat). **Part 2** = Vercel (frontend: either landing page for Streamlit, or Phase 5 + API URL). **Part 3** = Optional FastAPI hosting if you choose Pattern B.

---

## Part 1 — Host backend (chat + logic) on Streamlit

**Goal:** One Streamlit app that provides the chat and runs your existing Python logic (classifier, RAG, fast_lookup, answer generation). No FastAPI in this path.

### 1.1 What you need before deploy

- **Code:** A Streamlit entrypoint (e.g. `streamlit_app.py` or `home.py`) at the **repo root** or in a folder you will set as the app root in Streamlit Cloud. This file will:
  - Import your chat handler (e.g. `handle_chat` from Phase 4) or the Phase 2 + Phase 3 + Phase 4 logic.
  - Use `st.chat_input`, display messages, and call that logic (no HTTP; in-process).
- **Dependencies:** A single `requirements.txt` at the repo root (or in the app root) that lists:
  - `streamlit`
  - All Phase 1–4 dependencies (e.g. from Phase 1–4 `requirements.txt`), including `google-generativeai`, `chromadb`, `fastapi`, `uvicorn`, etc., as needed by the code the Streamlit app imports.
- **Secrets:** `GOOGLE_API_KEY` (for Gemini). You will add this in Streamlit Cloud’s “Secrets” (not in code).
- **Data and index:** ChromaDB and `Phase1_Corpus_and_Scope/data/funds.json` must be available to the app at runtime. Options:
  - **Include in repo:** If the ChromaDB folder and `funds.json` are small enough and not gitignored, commit them so Streamlit Cloud can read them.
  - **External storage:** If too large, upload ChromaDB and `funds.json` to a bucket (e.g. GCS, S3) and add code in the Streamlit app to download them at startup (and set secrets for credentials if required).

### 1.2 Streamlit Cloud deploy steps

1. **Push your repo to GitHub** (if not already). Streamlit Community Cloud deploys from GitHub.
2. Go to **https://share.streamlit.io** and sign in with GitHub.
3. **New app:**
   - Connect the repo.
   - **Branch:** e.g. `main`.
   - **Main file path:** e.g. `streamlit_app.py` (the file that runs `streamlit run`).
   - **App URL:** You get `https://<your-app>.streamlit.app`.
4. **Secrets:** In the app’s “Settings” or “Secrets”, add:
   - `GOOGLE_API_KEY` = your Gemini API key.
   - Any other env vars your app expects (e.g. for external storage).
5. **Advanced settings (if needed):**
   - Python version (e.g. 3.9 or 3.10).
   - Install command: e.g. `pip install -r requirements.txt`.
6. **Deploy.** Streamlit will build and run. Check logs for import errors or missing files (e.g. ChromaDB path, `funds.json` path). Fix paths in code so they work in Streamlit Cloud’s environment (often repo root = working directory).

### 1.3 After deploy

- Open `https://<your-app>.streamlit.app` and test the chat.
- If the app uses relative paths (e.g. `Phase1_Corpus_and_Scope/data/funds.json`), ensure the app’s working directory is the repo root (Streamlit Cloud usually runs from repo root).
- **NAV:** On Streamlit Cloud you typically do not run a long-lived scheduler. Options: run `fetch_nav` in a **scheduled job** (e.g. GitHub Actions cron) and commit updated `funds.json` or upload to storage; or run a one-time fetch at app startup if acceptable.

---

## Part 2 — Host frontend on Vercel

**Goal:** Deploy the Phase 5 static frontend (or a landing page) on Vercel.

### 2.1 Option A — Vercel as landing page (when backend is on Streamlit)

- **Content:** A simple static site (e.g. one HTML page or a small site) with:
  - Short description of the MF FAQ Assistant.
  - A clear “Try the chatbot” (or similar) link/button that goes to **your Streamlit app URL** (`https://<your-app>.streamlit.app`).
- **Deploy:**
  - Put the landing page in a folder (e.g. `landing/` or `vercel-frontend/`) with `index.html` (and optional CSS/JS).
  - Connect the repo to Vercel, set **Root Directory** to that folder (or deploy that folder only).
  - No API base URL needed; the only “frontend” action is to open the Streamlit link.

### 2.2 Option B — Vercel hosts Phase 5 chat UI (needs an API)

- **Content:** Your existing **Phase 5** static files (`Phase5_Frontend/`: `index.html`, `app.js`, `config.js`, `styles.css`, etc.).
- **API:** The Phase 5 app calls:
  - `POST /chat`
  - `GET /api/sources`
  - `GET /api/funds-by-type`
  - `GET /health`
  So it **must** have an API base URL. Streamlit does not provide these endpoints. You need to host the **FastAPI backend** somewhere (see Part 3) and point the frontend to that URL.
- **Config:** Set `window.MF_FAQ_API_BASE` to your **FastAPI** base URL (e.g. `https://your-api.railway.app` or `https://your-api.onrender.com`) **before** the app loads. Options:
  - Build-time: in `config.js` or in a small script that injects the URL from an env var (Vercel lets you set env vars; you can build a small step that replaces a placeholder with the API URL).
  - Or serve a small `config.js` that is generated (e.g. by a Vercel serverless function or a build step) with the API URL.
- **Deploy on Vercel:**
  1. Connect the repo.
  2. **Root Directory:** `Phase5_Frontend` (or the folder that contains `index.html` and assets).
  3. **Framework Preset:** Other / None (static).
  4. **Build command:** Leave empty or a simple copy; **Output directory** = `.` or the folder that contains `index.html`.
  5. Add **Environment variable** (e.g. `MF_FAQ_API_BASE` = `https://your-fastapi-url.com`) and use it in your build or in `config.js` so the frontend calls the right API.
  6. Deploy. Open the Vercel URL and test chat (ensure the API is deployed and CORS allows the Vercel domain).

---

## Part 3 — (Optional) Host FastAPI backend for Option B

If you deploy the **Phase 5 chat UI on Vercel** and want it to call your **existing** API, you need to host the **FastAPI app** (Phase 4) on a service that runs Python and allows long-running processes.

**Typical options:**

- **Railway**
  - Connect repo, set **Root Directory** to repo root (or where `Phase4_Backend_API` and Phase 1–3 code live).
  - **Start command:** e.g. `PYTHONPATH=. uvicorn Phase4_Backend_API.app:app --host 0.0.0.0 --port $PORT`. Railway sets `PORT`.
  - **Env vars:** `GOOGLE_API_KEY`, and any needed for SSL/certifi.
  - ChromaDB and `funds.json` must be on the same filesystem or loaded from external storage (e.g. download at startup from a bucket).

- **Render**
  - New **Web Service**, connect repo.
  - **Build:** `pip install -r Phase4_Backend_API/requirements.txt -r Phase2_RAG_Pipeline/requirements.txt -r Phase3_LLM_Prompts/requirements.txt -r Phase1_Corpus_and_Scope/requirements.txt` (and certifi if needed).
  - **Start:** `PYTHONPATH=. uvicorn Phase4_Backend_API.app:app --host 0.0.0.0 --port $PORT`.
  - Set **env vars** (e.g. `GOOGLE_API_KEY`). Again, ChromaDB and `funds.json` must be present or fetched at startup.

- **Fly.io**
  - Use a `Dockerfile` or `fly.toml` to run the FastAPI app; expose port; set env vars and ensure ChromaDB and `funds.json` are available.

**CORS:** Your FastAPI app already uses `CORSMiddleware` with `allow_origins=["*"]`. For production you can restrict `allow_origins` to your Vercel domain (e.g. `https://your-app.vercel.app`).

---

## Checklist summary

**Backend on Streamlit (Pattern A)**  
- [ ] Create a Streamlit app entrypoint that uses your chat/RAG logic.  
- [ ] Single `requirements.txt` with Streamlit + all Phase 1–4 deps.  
- [ ] ChromaDB and `funds.json` in repo or downloadable at startup (with secrets if needed).  
- [ ] Add `GOOGLE_API_KEY` (and any other secrets) in Streamlit Cloud.  
- [ ] Deploy on share.streamlit.io; test the chat URL.

**Frontend on Vercel**  
- [ ] **Option A:** Landing page that links to the Streamlit app; deploy that folder on Vercel.  
- [ ] **Option B:** Phase 5 static files; set `MF_FAQ_API_BASE` to your FastAPI URL; deploy Phase5_Frontend as static site on Vercel.

**If using Option B (Phase 5 + API)**  
- [ ] Host FastAPI (Phase 4) on Railway, Render, or Fly.io.  
- [ ] Ensure ChromaDB and `funds.json` are available to the API.  
- [ ] Set CORS (and env vars).  
- [ ] Use the API base URL in Vercel frontend config.

---

## Quick reference

| Item | Where |
|------|--------|
| Streamlit app URL | `https://<your-app>.streamlit.app` (after deploy) |
| Vercel frontend URL | `https://<your-project>.vercel.app` (after deploy) |
| FastAPI API URL (Pattern B) | e.g. `https://<your-service>.railway.app` or `.onrender.com` |
| API key | Never in code; use Streamlit Secrets / Vercel env / Railway or Render env |
| ChromaDB + funds.json | In repo (if small) or external storage + download at startup |

Once you implement the Streamlit app and (if needed) the FastAPI host, use this document as the deployment checklist.
