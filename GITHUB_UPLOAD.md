# Upload this project to GitHub

Git is initialized and the first commit is done. Follow these steps to push to GitHub.

---

## 1. Set your Git identity (one-time, if not already set)

Git needs your name and email for commits. Run **one** of these:

**For this repo only:**
```bash
cd "/Users/srivenurajulu/Documents/RAG Bot for MF"
git config user.name "Your Full Name"
git config user.email "your-email@example.com"
```

**For all repos on this machine:**
```bash
git config --global user.name "Your Full Name"
git config --global user.email "your-email@example.com"
```

Use the **same email** as your GitHub account (or your GitHub no-reply email).

---

## 2. Create a new repository on GitHub

1. Go to **https://github.com** and sign in.
2. Click **+** (top right) → **New repository**.
3. **Repository name:** e.g. `rag-bot-for-mf` or `mf-faq-assistant` (no spaces).
4. **Description (optional):** e.g. "Facts-only FAQ for ICICI Prudential mutual fund schemes."
5. Choose **Public** (or Private if you prefer).
6. **Do not** check "Add a README", "Add .gitignore", or "Choose a license" — the project already has these.
7. Click **Create repository**.

---

## 3. Connect your local repo and push

GitHub will show commands under "…or push an existing repository from the command line." Use these, with **your** repo URL.

**Replace `YOUR_USERNAME` and `YOUR_REPO` with your GitHub username and repo name.**

```bash
cd "/Users/srivenurajulu/Documents/RAG Bot for MF"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

**Example:** If your repo is `https://github.com/srivenurajulu/rag-bot-for-mf`:
```bash
git remote add origin https://github.com/srivenurajulu/rag-bot-for-mf.git
git branch -M main
git push -u origin main
```

- If GitHub asks for credentials, use your **username** and a **Personal Access Token** (not your password).  
  Create a token: GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)** → **Generate new token**; enable `repo`.
- Or use **GitHub CLI** (`gh auth login`) and then `git push` will use it.

---

## 4. Optional: Update commit author

If the first commit used a placeholder name/email, update it and amend:

```bash
git config user.name "Your Full Name"
git config user.email "your-email@example.com"
git commit --amend --reset-author --no-edit
git push --force-with-lease origin main
```

---

## 5. What was not pushed (on purpose)

- **`.env`** — Ignored; contains `GOOGLE_API_KEY`. Never commit it. Others clone the repo and add their own `.env` (see `.env.example`).
- **`.venv/`** — Ignored; virtual environment. Others run `python -m venv .venv` and `pip install -r ...`.
- **`Phase1_Corpus_and_Scope/data/`** and **`Phase2_RAG_Pipeline/data/`** — May be ignored by phase `.gitignore`. If you need them on GitHub (e.g. for Streamlit deploy), remove those paths from the phase `.gitignore` and commit; otherwise keep them ignored and use external storage or document "run Phase 1 and Phase 2 after clone."

---

## Quick reference

| Step | Command / action |
|------|-------------------|
| 1 | Set `git config user.name` and `user.email` |
| 2 | On GitHub: New repository (no README/.gitignore) |
| 3 | `git remote add origin https://github.com/USER/REPO.git` |
| 4 | `git push -u origin main` |
| 5 | (Optional) Amend author and force-push |

After the first push, use `git add`, `git commit`, and `git push` as usual for future updates.
