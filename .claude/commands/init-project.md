Initialize the project for local development — set up environment, install dependencies, start services, run migrations, and verify the dev server.

---

## Initialization Steps

### Step 1 — Environment Setup
```bash
cp .env.example .env
```
Open `.env` and fill in any required secrets (database URL, API keys, etc.) before proceeding.

### Step 2 — Install Dependencies

Detect and use the correct package manager:
```bash
# Node.js projects
npm install        # if package-lock.json exists
pnpm install       # if pnpm-lock.yaml exists
bun install        # if bun.lockb exists
yarn install       # if yarn.lock exists

# Python projects
uv sync            # if pyproject.toml + uv exists
pip install -r requirements.txt  # fallback
```

### Step 3 — Start Required Services
```bash
# If docker-compose.yml exists
docker-compose up -d

# Or start specific services
docker-compose up -d db        # database only
docker-compose up -d redis     # cache only
```

### Step 4 — Run Database Migrations
```bash
# Drizzle ORM (Node.js)
npx drizzle-kit migrate

# Prisma (Node.js)
npx prisma migrate dev

# Alembic (Python)
uv run alembic upgrade head

# Raw SQL
psql $DATABASE_URL -f schema.sql
```

### Step 5 — Start Development Server
```bash
# Next.js / Node.js
npm run dev

# Python FastAPI
uv run uvicorn app.main:app --reload --port 8000

# Other
{dev-command from package.json or Makefile}
```

### Step 6 — Verify Setup
Check the following are working:
- [ ] Dev server responds at `http://localhost:{PORT}`
- [ ] Database connection is healthy (check health endpoint or run a query)
- [ ] No errors in the terminal output

Report the access points:
- App: `http://localhost:{PORT}`
- API docs (if applicable): `http://localhost:{PORT}/docs`
- Database: `localhost:{DB_PORT}`

If any step fails, stop and report the specific error — do not proceed to the next step.
