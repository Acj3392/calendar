#!/usr/bin/env bash
# refresh_local.sh — pull fresh Monarch data, commit, and push to trigger Vercel redeploy.
# Designed to run as a launchd job (daily at 7am) or manually: bash scripts/refresh_local.sh
set -euo pipefail

REPO="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$REPO"

# ── Credentials ──────────────────────────────────────────────────────────────
if [[ ! -f "$REPO/.env.local" ]]; then
  echo "[ERROR] $REPO/.env.local not found." >&2
  echo "        Copy .env.local.example to .env.local and fill in your credentials." >&2
  exit 1
fi
set -a; source "$REPO/.env.local"; set +a

# ── Python: use PersonalOS venv (has monarchmoney 1.3.0) → system fallback ────
# The calendar project's .venv has an old monarchmoney (0.1.x) that breaks with
# token auth. The PersonalOS venv has the working 1.3.0 build.
PERSONALOS_VENV="/Users/anna/Desktop/Home/PersonalOS/Ideas/Project/.venv/bin/python"
if [[ -x "$PERSONALOS_VENV" ]]; then
  PYTHON="$PERSONALOS_VENV"
else
  PYTHON="python3"
fi

# ── Fetch ─────────────────────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Fetching Monarch transactions..."
"$PYTHON" "$REPO/scripts/fetch_monarch.py"

# ── Commit + push only if data changed ───────────────────────────────────────
if git diff --quiet data/spending.json; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] No new transactions — nothing to push."
  exit 0
fi

git add data/spending.json
git commit -m "chore: refresh spending data $(date '+%Y-%m-%d')"
git push origin main
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pushed. Vercel will redeploy shortly."
