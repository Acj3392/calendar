# Spending Calendar

A web + mobile friendly calendar that visualizes daily spending, with Today / Week /
Month / Year views. Low-spend days are celebrated (🏆); days with no spending at all
glow a special green (💚). Data comes from Monarch Money and refreshes every 6 hours.

## How it works

```
GitHub Action (every 6h)
  → scripts/fetch_monarch.py  (logs into Monarch, builds the JSON)
  → commits data/spending.json
  → push triggers a Vercel redeploy
index.html (static)
  → fetches data/spending.json on load and renders the calendar
```

No database, no backend. The only thing that changes between deploys is
`data/spending.json`. Monarch credentials live only in GitHub Actions secrets.

## Files

| Path | Purpose |
|------|---------|
| `index.html` | The calendar app (React via CDN, no build step). Fetches `data/spending.json`. |
| `data/spending.json` | Committed spending data — the refreshed artifact. |
| `scripts/fetch_monarch.py` | Logs into Monarch and writes `data/spending.json`. |
| `.github/workflows/refresh.yml` | Cron (every 6h) that runs the script and commits changes. |
| `vercel.json` | Static deploy config; marks the data file as non-cacheable. |
| `docs/pattern-recognition-roadmap.md` | Future idea: detect spending patterns (e.g. groceries up ↔ delivery down). |

## Setup

### 1. Push to GitHub (private repo)

```bash
cd calendar
git init && git add . && git commit -m "Initial spending calendar"
gh repo create calendar --private --source=. --push
```

### 2. Add GitHub Actions secrets

Repo → Settings → Secrets and variables → Actions → New repository secret:

- `MONARCH_EMAIL` — your Monarch login email
- `MONARCH_PASSWORD` — your Monarch password
- `MONARCH_MFA_SECRET` — the **TOTP setup secret** from Monarch

> **MFA note:** the Action can't tap your phone, so it generates the 6-digit code
> from a TOTP secret. In Monarch, set up an *authenticator app* for 2FA; when it
> shows the QR code, also reveal the "setup key" / "manual entry" string — that's
> `MONARCH_MFA_SECRET`. If your Monarch 2FA is SMS-only, switch it to an
> authenticator app first.

### 3. Connect to Vercel

- Import the repo at [vercel.com/new](https://vercel.com/new). Framework preset:
  **Other** (it's a static site). No build command needed.
- **Turn on password protection:** Project → Settings → Deployment Protection →
  enable for production. This is personal financial data — keep it gated.

### 4. Trigger the first refresh

Actions tab → "Refresh Monarch data" → Run workflow. It logs in, writes
`data/spending.json`, commits, and Vercel redeploys automatically.

## Run the fetch locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MONARCH_EMAIL=... MONARCH_PASSWORD=... MONARCH_MFA_SECRET=...
python scripts/fetch_monarch.py
```

Then serve the folder:

```bash
python3 -m http.server 7823
# open http://localhost:7823
```

## Caveats

- **Unofficial Monarch API.** The `monarchmoney` library is community-maintained and
  can break if Monarch changes its auth. If that happens the Action fails loudly
  (you get a GitHub email) but never corrupts existing data.
- **Spending only.** Income, transfers, and credit-card payments are excluded so
  totals reflect real outflow, not money moving between accounts.
