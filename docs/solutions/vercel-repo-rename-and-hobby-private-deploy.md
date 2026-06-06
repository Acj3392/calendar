---
title: "Vercel: a GitHub repo rename + a Hobby account broke auto-deploy (and how)"
date: 2026-06-06
tags: [deployment, vercel, github, auth]
category: gotcha
module: deployment
symptoms: ["deployments stopped after a GitHub repo rename", "Project Link not found", "Build Failed: No python entrypoint found", "Deployment Blocked: commit author did not have contributing access", "Hobby Plan does not support collaboration for private repositories", "app 404s on the old vercel URL"]
---

# A GitHub repo rename + a Hobby account broke Vercel auto-deploy

A multi-layered failure chain that took far too long because I kept fixing
symptoms instead of reading the build log. Documented so the next session reads
the log first.

## The chain (each layer masked the next)

1. **GitHub repo renamed** `annajay778/calendar` → `Acj3392/calendar`. Vercel's
   Git connection went stale → **"Project Link not found"**, auto-deploys silently
   stopped. (GitHub still redirects pushes, so `git push` *looked* fine.)
2. **Reconnecting re-imported the project**, and Vercel **auto-detected it as
   Python** (because `requirements.txt` exists) → build failed:
   **"No python entrypoint found."** It's a static site, not Python.
3. Pinning `framework: null` in `vercel.json` did NOT fix it, because the real
   blocker was deeper:
4. The project was reconnected under a **personal Hobby (free)** Vercel account.
   **Hobby refuses to deploy a PRIVATE repo when the commit author isn't the
   account owner** → **"Deployment Blocked: commit author did not have
   contributing access."** Commits were authored `anna@campminder.com`; the Vercel
   owner is the personal account. Manual redeploys worked (owner-triggered);
   git-push auto-deploys were blocked.

## The fixes

- **Reconnect Git** after a rename: Project → Settings → Git → Reconnect → pick the
  renamed repo. (May require re-authorizing the Vercel GitHub App on the new
  account — an OAuth step.)
- **Pin the build config in `vercel.json`** so re-imports can't auto-detect Python:
  ```json
  { "framework": null, "buildCommand": "", "outputDirectory": "." }
  ```
- **The actual unblock (Hobby + private repo):** author commits with the **Vercel
  account owner's GitHub identity**. Use the GitHub noreply email so attribution is
  guaranteed:
  ```bash
  git config user.email "<id>+<login>@users.noreply.github.com"   # e.g. 206156394+Acj3392@...
  ```
  This is repo-local (`.git/config`) — it covers this clone's future commits AND
  `refresh_local.sh` (which uses ambient config). Re-set it if the repo is re-cloned.
  Alternatives: upgrade to Pro (paid), or move back to a Team account. **Do NOT make
  the repo public** — `data/spending.json` holds real financial data.

## Why It Works

Vercel attributes a git deployment to the GitHub user who authored the commit, then
checks if that user is a member of the Vercel team. On Hobby (a one-person "team"),
only the owner counts, and private-repo collaboration is disabled — so a commit
authored by any other identity is blocked. Matching the author to the owner's GitHub
identity makes every push an "owner" deploy.

## Lessons
- **Read the build/deployment log FIRST.** "No python entrypoint" and "Deployment
  Blocked" are different failures; I burned two wrong fixes (preset, vercel.json)
  guessing before reading the log that said "blocked."
- A repo rename is a silent deploy-killer: pushes succeed (via redirect) while
  nothing deploys. Check the Vercel↔Git link after any rename/transfer.
- Old `*.vercel.app` URLs 404 after a project is deleted/moved — update bookmarks.

## Related
- `docs/solutions/backfill-vs-window-on-overwriting-jobs.md`, `monarch-auth-and-refresh.md`
- Production now: `calendar-sand-zeta.vercel.app` (personal `anna-c-projects`, Hobby)
- `vercel.json` (pinned static config)
