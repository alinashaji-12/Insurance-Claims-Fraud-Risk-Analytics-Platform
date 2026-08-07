# Deploy ClaimGuard AI on Render

This repo ships a [Render Blueprint](https://render.com/docs/infrastructure-as-code) at `render.yaml` with two web services from the same Git repository:

| Service | `rootDir` | Runtime | Role |
|---------|-----------|---------|------|
| `claimguard-api` | `backend` | Python | FastAPI + uvicorn on `$PORT` |
| `claimguard-web` | `frontend` | Node | Next.js (`npm run build` → `npm start`) |

---

## Option A — Blueprint (recommended)

1. Push this repo to GitHub/GitLab (already configured if you follow the project README).
2. Open [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
3. Connect the repository that contains `render.yaml`.
4. Review the two services (`claimguard-api`, `claimguard-web`) and click **Apply**.
5. Wait for both deploys. Note each service’s public URL (`https://….onrender.com`).
6. Complete the **post-deploy checklist** below (models, seed data, CORS verify).

Blueprint env wiring:

- **API** `ALLOWED_ORIGINS` ← `claimguard-web`’s `RENDER_EXTERNAL_URL`
- **Web** `NEXT_PUBLIC_API_URL` ← `claimguard-api`’s `RENDER_EXTERNAL_URL`

If cross-service sync is empty on first create, set those two values manually in the Dashboard (see [Environment variables](#environment-variables)), then **Clear build cache & deploy** the frontend so `NEXT_PUBLIC_*` is rebuilt.

---

## Option B — Manual services

### 1. API (`claimguard-api`)

- **New** → **Web Service** → same repo
- **Root Directory:** `backend`
- **Runtime:** Python 3.11
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env vars: see table below

(`backend/Procfile` mirrors the start command for platforms that read Procfiles.)

### 2. Frontend (`claimguard-web`)

- **New** → **Web Service** → same repo
- **Root Directory:** `frontend`
- **Runtime:** Node 20
- **Build Command:** `npm install && npm run build`
- **Start Command:** `npm start`
- Set `NEXT_PUBLIC_API_URL` to the API’s public URL **before** the first successful build

---

## Environment variables

### Backend (`claimguard-api`)

| Variable | Example / notes |
|----------|-----------------|
| `DATABASE_URL` | Default Blueprint value: `sqlite:///./claimguard.db`. For Postgres, use the Render DB **Internal Database URL** (see [Postgres](#postgres-recommended-for-anything-beyond-a-demo)). |
| `ALLOWED_ORIGINS` | Comma-separated frontend origins, e.g. `https://claimguard-web.onrender.com`. Must match the browser origin (scheme + host, no path). |
| `PYTHON_VERSION` | `3.11.11` (set in Blueprint) |

No API keys or secrets are required for the hackathon demo stack.

### Frontend (`claimguard-web`)

| Variable | Example / notes |
|----------|-----------------|
| `NEXT_PUBLIC_API_URL` | `https://claimguard-api.onrender.com` (no trailing slash). **Build-time** — change it → redeploy frontend. |
| `NODE_VERSION` | `20` (set in Blueprint) |

Local examples live in `backend/.env.example` and `frontend/.env.local.example`. Never commit real `.env` / `.env.local` files.

---

## CORS

The API reads `ALLOWED_ORIGINS` (comma-separated) in `app/core/config.py` and passes them to FastAPI `CORSMiddleware`.

After deploy:

1. Open the frontend URL in a browser.
2. If API calls fail with CORS errors, set `ALLOWED_ORIGINS` on the API to the **exact** frontend origin and redeploy (or restart) the API.
3. You can list multiple origins: `https://claimguard-web.onrender.com,http://localhost:3000`.

---

## ML models (important blocker)

Scoring loads:

- `backend/ml_training/models/fraud_model.pkl`
- `backend/ml_training/models/anomaly_model.pkl`

These `*.pkl` files are **gitignored** (see root `.gitignore`) so they are **not** present in a fresh Render clone. Metrics JSON files are tracked; the binaries are not.

**You must supply models on the server** using one of:

1. **Train on Render (one-shot)** after uploading/training data is available:
   ```bash
   # From the API service shell / one-off job, with cwd = backend
   python -m ml_training.train_fraud_model
   python -m ml_training.train_anomaly_model
   ```
   Requires `backend/data/raw/claims.csv` (also gitignored — upload via shell, S3, or a private artifact store).
2. **Upload artifacts** into `backend/ml_training/models/` via Render Shell / SCP-style workflow after deploy (ephemeral disk: lost on free-tier spin-down unless you re-upload or move to persistent storage).
3. **Carefully adjust `.gitignore`** only if your team decides small demo `.pkl` files should be committed. Do **not** force-commit huge binaries; prefer training or object storage for large artifacts.

Until models exist, fraud/anomaly scoring endpoints will fail when they try to `joblib.load` the missing files.

---

## Database seed / sample data

- SQLite file paths and `backend/data/raw/*.csv` are gitignored.
- After first API deploy, use **Render Shell** on `claimguard-api` (with models + CSV in place):

  ```bash
  python -m app.seed
  ```

- Or upload claims via `POST /claims/upload` from the UI once the API is healthy (`GET /health`).

---

## Postgres (recommended beyond a quick demo)

SQLite on Render **free tier** uses the instance’s ephemeral filesystem:

- Data **disappears** when the free service spins down or redeploys.
- Concurrent writers and multi-instance scaling are unsafe.

**Better path:**

1. Create a **Render Postgres** instance (paid plans; free Postgres may be unavailable depending on account).
2. On `claimguard-api`, set `DATABASE_URL` to the Postgres **connection string** (Internal URL from the same region is preferred).
3. Install a Postgres driver on the API service, e.g. add to `requirements.txt` or build:
   ```text
   psycopg2-binary>=2.9.9
   ```
   SQLAlchemy already accepts `postgresql://…` via `DATABASE_URL` (`app/core/database.py`).
4. Redeploy API, then run `python -m app.seed` (or rely on `init_db()` for empty schema + upload CSV).

The Blueprint defaults to SQLite so a zero-cost demo can boot; swap `DATABASE_URL` when you add Postgres (optionally wire `fromDatabase` in `render.yaml`).

---

## Free-tier caveats

- **Cold starts:** Free web services sleep after idle traffic; the first request can take 30–60+ seconds.
- **Ephemeral disk:** SQLite DB, uploaded CSVs, and trained `.pkl` files are wiped on restart/redeploy unless stored elsewhere.
- **Build minutes / spin-down:** Heavy ML deps (`xgboost`, `shap`, etc.) make API builds slow and memory-hungry; free instances may OOM during train or large uploads.
- **Two services:** Frontend and API can sleep independently — wake the API first (`/health`) if the UI shows network errors after idle.
- **`NEXT_PUBLIC_*`:** Changing the API URL requires a **frontend rebuild**, not only an API restart.

---

## Smoke test

1. `GET https://<api>/health` → `{"status":"ok"}`
2. Open `https://<web>/` — dashboard loads without console CORS/API errors
3. Upload `docs/sample_upload.csv` (or seeded data) and open a claim detail page

---

## Troubleshooting

| Symptom | Likely fix |
|---------|------------|
| CORS blocked | Set `ALLOWED_ORIGINS` to the frontend `https://…onrender.com` origin |
| Frontend calls `localhost:8000` | `NEXT_PUBLIC_API_URL` missing at build time → set + redeploy web |
| Model / joblib errors | Supply `.pkl` files (see [ML models](#ml-models-important-blocker)) |
| Empty DB after redeploy | Expected with SQLite on free tier → re-seed or use Postgres |
| Build OOM on API | Upgrade instance, slim deps for deploy, or train models offline |
