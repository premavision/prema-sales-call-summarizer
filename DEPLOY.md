# 🚀 Deployment Guide

## 1. Prema Sales Call Summarizer (Backend + Streamlit)

### Option A: Render.com (Recommended for Backend/API)

Render is excellent for hosting Python applications and managing databases.

1.  **Push your code** to GitHub.
2.  **Sign up/Login** to [Render.com](https://render.com).
3.  **Create a PostgreSQL Database**:
    *   Click **New +** -> **PostgreSQL**.
    *   Name: `prema-db`.
    *   Region: Frankfurt (EU Central) or closest to you.
    *   Plan: **Free**.
    *   **Copy the "Internal Database URL"** once created (starts with `postgres://...`).
4.  **Create a Web Service** (FastAPI):
    *   Click **New +** -> **Web Service**.
    *   Connect your GitHub repo.
    *   Runtime: **Python 3**.
    *   Build Command: `pip install -r requirements.txt`.
    *   Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
    *   **Environment Variables**:
        *   `PYTHON_VERSION`: `3.11.9`
        *   `DATABASE_URL`: (Paste the Internal Database URL from step 3)
        *   `OPENAI_API_KEY`: `sk-...`
5.  **Deploy**.

### Option B: Streamlit Community Cloud (Recommended for UI)

Streamlit Cloud is the easiest way to host the dashboard interface.

1.  Go to [share.streamlit.io](https://share.streamlit.io/).
2.  Click **New App**.
3.  Select your repository and branch.
4.  **Main file path**: `app/ui/streamlit/dashboard.py`.
5.  Click **Advanced Settings** (Secrets) and paste your configuration:
    ```toml
    environment = "production"
    # Use External Database URL from Render if connecting to Render DB
    database_url = "postgresql://user:pass@host:5432/db" 
    audio_dir = "data/audio"
    
    asr_provider = "whisper"
    llm_provider = "openai"
    openai_api_key = "sk-..."
    ```
6.  Click **Deploy**.

---

## 2. Prema LinkedIn Outreach (Frontend)

Vercel is the industry standard for deploying frontend apps (Next.js, React, Vue).

1.  **Push your frontend code** to a separate GitHub repository (or ensure it's in a clean folder).
2.  Go to [vercel.com](https://vercel.com) and login.
3.  Click **Add New...** -> **Project**.
4.  Import your GitHub repository `prema-linkedin-outreach`.
5.  **Configure Project**:
    *   **Framework Preset**: Vercel usually auto-detects this (Next.js, Vite, etc.).
    *   **Root Directory**: Leave as `./` if your package.json is in the root.
6.  **Environment Variables**:
    *   If your frontend needs to talk to the backend, add:
        *   `NEXT_PUBLIC_API_URL` (or your specific variable name): `https://your-render-app-name.onrender.com`
7.  Click **Deploy**.
