---
title: "Shareable fake-data prototype + password-gated personal view"
date: 2026-06-19
tags: [privacy, deployment, vercel, blob, serverless, auth, fake-data]
category: architecture
module: deployment
symptoms: ["want to share the prototype without exposing real spend", "deploy blocked as data exfiltration", "Personal App says local-only on phone", "real data findable at public /data URL", ".vercelignore ignored on git deploys"]
---

# Shareable fake-data prototype + password-gated personal view

The app needs two faces: a **public, shareable** view with believable fake data,
and a **private** view of the owner's real spend reachable from the live site and
phone. This documents the architecture and the dead ends, so we don't relearn it.

## The two-mode model

`index.html` has an `<App>` controller holding `{mode, fakeData, personalData}`.
- **Default mode is `fake`** — `data/spending.fake.json` loads on open. Safe to share.
- **`🔒 Personal App`** prompts for a password and shows the real data.
- A masthead pill toggle switches modes; a badge always shows which dataset is live.

## Fake data (`scripts/generate_fake.py`)

Two approaches were tried:
1. **From-scratch synthetic** (weighted categories, invented ranges, light days,
   injected paychecks). Fully decoupled from real data → leaks nothing. But hard
   to make feel like a *specific* person.
2. **Mirror mode (current).** Keep each real day's transaction shape (category,
   type, count), swap merchants for invented ones, and scale every amount down
   (~12%, groceries ~22% for two people) with ±8% jitter so values aren't a clean
   reversible multiple. Plus per-category fixes: cap Mortgage to one/month, scale
   pets way down. **Tradeoff:** because amounts derive from the real ones, the
   fake set *approximates* the real distribution — acceptable only because the
   owner explicitly asked for "mirror my life, a little less."

Always assert no real merchant names survive into the output.

## The privacy trap (read this before deploying)

**Deploying the real `data/spending.json` to a public URL is data exfiltration**
and is hard-blocked by the Claude Code safety classifier *even with user consent*.
A client-side password does NOT help — both the passcode and the file ship in the
public bundle; anyone can open DevTools → Network and read the file.

Also: **`.vercelignore` only applies to CLI deploys, not Git-integration deploys.**
To truly keep a file off the deployed site you must also untrack it from git
(`git rm --cached` + `.gitignore`), not just list it in `.vercelignore`.

Gotcha: `git checkout main` after the file was removed from the tree will DELETE
the local working copy (it's a tracked deletion). It's gitignored now, so checkout
no longer touches it — but if it ever vanishes, restore with
`git show <commit>:data/spending.json > data/spending.json`.

## Personal view that works on the live site (server-gated)

The secure pattern that the classifier allows and that works on phone:

- Real data lives in a **private Vercel Blob** (`personal/spending.json`,
  `addRandomSuffix:false`, `allowOverwrite:true`) — never a public static file.
- **`api/personal.js`** (Vercel Node function): `POST {password}` → compare to
  `process.env.PERSONAL_PASSCODE` **server-side** → on success stream the blob via
  `get(path, {access:'private'})` and return JSON; 401 on bad password, 404 if not
  uploaded. The passcode and data never reach the browser.
- Client unlock POSTs to `/api/personal`. On `localhost` (static `python -m
  http.server`, no functions) it falls back to reading the local file, gated by a
  client-side `PERSONAL_PASSCODE` constant — fine because it's the owner's machine.
- **Keeping it current:** `scripts/push_personal.mjs` (`npm run push-personal`)
  uploads the local real file to the blob; `refresh_local.sh` calls it after each
  Monarch fetch instead of committing data to git.

### Provisioning (one-time, interactive — needs `vercel login`)
1. `vercel blob store add <name>` → adds `BLOB_READ_WRITE_TOKEN` to the project.
2. `vercel env add PERSONAL_PASSCODE` (all environments).
3. Put `BLOB_READ_WRITE_TOKEN` in local `.env.local` (don't clobber Monarch creds)
   so the refresh job can push.
4. Turn **off** Vercel Deployment Protection — otherwise the whole site (including
   the public fake view and `/api/personal`) returns 401 to everyone. The real
   data stays protected by the password gate regardless.

## Why not just lock the whole deploy?

Vercel Deployment Protection gates the *entire* site, so the fake prototype would
no longer be publicly shareable — defeating the point. The server-gate keeps fake
public and real private in one deployment.
