# HepVar — Setup & Run

## 0. Prerequisites

- Python 3.11+ (3.13/3.14 OK)
- Node.js 20+ and npm
- Git

## 1. One-time setup

```bash
# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e backend
# (optional) pip install -e backend[dev,alphagenome]

# Frontend
cd frontend
npm install
cd ..

# Environment
cp .env.example .env
# Edit .env with your real keys:
#   ANTHROPIC_API_KEY=sk-ant-...
#   NCBI_API_KEY=...
#   NCBI_EMAIL=you@example.com
#   ALPHAGENOME_API_KEY=...        (skip if you don't have it)
```

## 2. Quick smoke test of Opus 4.7 (verifies key + cache hits)

```bash
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)   # load env into shell
python -m backend.scripts.test_opus
```

Expected output: two completions; the **second** call should show `cache_read_input_tokens > 0`.

## 3. Run the unit tests

```bash
pip install pytest pytest-asyncio
pytest backend/tests -q
```

## 4. Run the app

Terminal 1 (backend):
```bash
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
uvicorn backend.api.main:app --reload --port 8000
```

Terminal 2 (frontend):
```bash
cd frontend
npm run dev
# http://localhost:3000
```

Open `http://localhost:3000`, click the **ABCB4 — LPAC / PFIC3** demo chip, hit `→`.

## 5. Pre-cache the demo variant (offline-safe demo)

After running the pipeline once against the demo variant with real internet, every external response is persisted under `evidence/fixtures/GRCh38_chr7_87408188_T_C/`. To force the demo to read fixtures only (no network calls during the recording):

```bash
HEPVAR_DEMO_MODE=1 uvicorn backend.api.main:app --port 8000
```

Anthropic calls still go to the API (Opus 4.7 reasoning is live).

## 6. Health check

```bash
curl -s http://localhost:8000/health | python -m json.tool
```

You should see `anthropic_configured: true` and `alphagenome_configured: true`.
