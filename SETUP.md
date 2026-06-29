# Setup — for agents

## Prerequisites

- Python 3.10+
- Node.js 20+
- Supabase account (for auth + DB)
- SpacetimeDB running on localhost:3001

## Step-by-Step

```bash
# 1. Clone the repo
git clone https://github.com/omiinaya/spacetime-crm.git
cd spacetime-crm

# 2. Backend setup
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Supabase credentials

# 3. Start backend
python3 main.py

# 4. Frontend
cd ../web
npm install
npm run dev
# Frontend: http://localhost:5185, proxies /api to backend
```

## Environment Variables

| Var | Required | Default | Purpose |
|-----|----------|---------|---------|
| SUPABASE_URL | Yes | — | Supabase project URL |
| SUPABASE_ANON_KEY | Yes | — | Supabase anonymous key |
| SERVER_PORT | No | 8000 | Backend port |

For more details, see [AGENTS.md](./AGENTS.md).
