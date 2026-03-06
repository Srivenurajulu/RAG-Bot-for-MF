# What to do on Streamlit and Vercel — quick checklist

After pushing the new Streamlit app and Vercel landing page to your repo, follow these steps on each platform.

---

## 1. Streamlit Cloud — get the chatbot live

### Before you start
- **GitHub:** Push your repo (with `streamlit_app.py`, `requirements-streamlit.txt`, `.streamlit/config.toml`, and your **data**: `Phase1_Corpus_and_Scope/data/funds.json` and `Phase2_RAG_Pipeline/data/chroma/`) to GitHub.
- **Data:** Streamlit Cloud must see the RAG index and funds. Either:
  - **Option A:** Commit `Phase1_Corpus_and_Scope/data/funds.json` and `Phase2_RAG_Pipeline/data/chroma/` (if not in `.gitignore` and size is acceptable), or  
  - **Option B:** Add code in `streamlit_app.py` to download them from external storage (e.g. GCS/S3) at startup and set secrets for credentials.

### On Streamlit Cloud (share.streamlit.io)

1. **Sign in** with your GitHub account.
2. **New app**
   - Click **“New app”**.
   - **Repository:** select your repo (e.g. `your-username/rag-bot-for-mf`).
   - **Branch:** e.g. `main`.
   - **Main file path:** `streamlit_app.py` (must be at repo root or the path you chose).
   - **App URL:** You’ll get something like `https://your-app-name.streamlit.app`.
3. **Secrets**
   - Open your app → **Settings** (gear) or **Secrets**.
   - Add:
     - `GOOGLE_API_KEY` = your Gemini API key (from https://aistudio.google.com/apikey).
   - Save.
4. **Advanced settings** (if needed)
   - **Python version:** 3.9 or 3.10.
   - **Install command:**  
     `pip install -r requirements-streamlit.txt`  
     (If Streamlit expects a file named `requirements.txt`, either rename `requirements-streamlit.txt` to `requirements.txt` in the repo root for deploy, or set this install command explicitly in Streamlit Cloud.)
5. **Deploy**
   - Click **Deploy**. Wait for the build. Fix any errors from the logs (e.g. missing module, wrong path).
6. **Test**
   - Open the app URL. Ask e.g. “What is the expense ratio of ELSS?” and confirm you get an answer and a source link.
7. **Copy the app URL**
   - You’ll need it for the Vercel landing page (e.g. `https://your-app-name.streamlit.app`).

### If the build fails
- **Missing ChromaDB or funds.json:** Ensure those paths exist in the repo (Option A) or that your app downloads them (Option B).
- **Module not found:** Add the missing package to `requirements-streamlit.txt` and push.
- **GOOGLE_API_KEY:** Ensure it’s set in **Secrets** (not in code).

---

## 2. Vercel — host the landing page

### Before you start
- **Streamlit URL:** Have your live Streamlit app URL (e.g. `https://your-app-name.streamlit.app`).
- **Landing page:** The repo has a `vercel-landing` folder with `index.html` and `vercel.json`.

### Update the landing page link
1. Open **`vercel-landing/index.html`** in the repo.
2. Replace `https://YOUR_STREAMLIT_APP_URL` with your real Streamlit app URL (e.g. `https://your-app-name.streamlit.app`) in:
   - The `<a class="btn" href="...">` tag (around line 28).
   - The JavaScript variable `streamlitUrl` (around line 38) if you use it.
3. Commit and push.

### On Vercel (vercel.com)

1. **Sign in** with GitHub.
2. **Import project**
   - **Add New** → **Project**.
   - Import your GitHub repo.
3. **Configure**
   - **Root Directory:** Click **Edit** and set to **`vercel-landing`** (so Vercel uses only that folder).
   - **Framework Preset:** Other (or leave default).
   - **Build command:** Leave empty (static site).
   - **Output directory:** Leave default (`.` or empty).
   - **Install command:** Leave empty.
4. **Deploy**
   - Click **Deploy**. Vercel will build and give you a URL (e.g. `https://your-project.vercel.app`).
5. **Test**
   - Open the Vercel URL. Click **“Try the chatbot”** and confirm it opens your Streamlit app.

### Optional: custom domain
- In the Vercel project → **Settings** → **Domains**, add your domain and follow the DNS instructions.

---

## 3. Summary checklist

| Step | Where | Action |
|------|--------|--------|
| 1 | Repo | Push `streamlit_app.py`, `requirements-streamlit.txt`, `.streamlit/config.toml`, and data (or download logic). |
| 2 | Streamlit Cloud | New app → repo, branch, main file `streamlit_app.py`. |
| 3 | Streamlit Cloud | Secrets → add `GOOGLE_API_KEY`. |
| 4 | Streamlit Cloud | Install command: `pip install -r requirements-streamlit.txt` (or use `requirements.txt`). Deploy. |
| 5 | Repo | In `vercel-landing/index.html`, replace `YOUR_STREAMLIT_APP_URL` with your Streamlit app URL. Push. |
| 6 | Vercel | Import repo, Root Directory = `vercel-landing`, Deploy. |
| 7 | Both | Test: Vercel page → “Try the chatbot” → Streamlit chat works. |

---

## 4. Run Streamlit locally (optional)

From the **repo root**:

```bash
pip install -r requirements-streamlit.txt
streamlit run streamlit_app.py
```

Open the URL shown (e.g. http://localhost:8501). Ensure `.env` has `GOOGLE_API_KEY` and that `Phase1_Corpus_and_Scope/data/funds.json` and `Phase2_RAG_Pipeline/data/chroma/` exist (run Phase 1 and Phase 2 first if needed).
