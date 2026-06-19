---
title: "Vercel Hobby + private repo: production deploys stall as UNKNOWN and never promote"
date: 2026-06-19
tags: [vercel, deployment, hobby-plan, private-repo, build-queue, gotcha]
category: gotcha
module: deployment
symptoms: ["production deployment status UNKNOWN", "vercel alias set: deployment is not ready", "production domain stuck on an old deploy", "vercel deploy --prod hangs / no output", "preview builds Ready in seconds but production never promotes", "PR merge production deploy Blocked"]
---

# Vercel Hobby + private repo: production deploys stall and never promote

## Symptom

Adding a serverless function (`/api/personal`) to the static calendar app and
deploying it never reached the production domain `calendar-sand-zeta.vercel.app`.
For ~an hour, every attempt to ship looked broken in a confusing way:

- `vercel ls` showed **every production-target deployment as `UNKNOWN`** (not
  Ready, not Error) — while **preview** deployments built and went Ready in ~10s.
- `vercel deploy --prod` and `vercel alias set` **hung** (no output written) or
  returned `Error: The deployment ... is not ready`.
- The production domain stayed pinned to a **5-day-old deploy that predated the
  function**, so `/api/personal` returned 404 there.
- A PR-merge production deploy showed status **"Blocked"** in the dashboard.

The function itself was fine — some earlier production deploys *did* serve it
(returned proper 401s) before the stall set in; the problem was promotion.

## Root cause

The Vercel project was on the **Hobby plan with a private GitHub repo**. In that
configuration, **production builds don't complete** — they sit in `UNKNOWN`/queued
and never promote the production domain. Preview builds are unaffected, which
masks the issue and sends you debugging the function, env vars, and aliases
instead of the plan/repo-visibility constraint.

## Fix

**Make the repo public** (or upgrade the Vercel plan). The moment the
`Acj3392/calendar` repo was switched to public, a pushed commit triggered a
production deploy that built, promoted `calendar-sand-zeta`, and served the
function within seconds. Verified immediately after:

```
wrong password  -> 401 {"error":"Incorrect password"}
Rosebud23!      -> 200  (real data, 167 days)
/data/spending.json -> 404 (real file never publicly served)
```

## How to recognize it next time (don't re-chase the wrong layer)

The tell is the **asymmetry**: previews Ready in seconds, *every* production
deploy stuck `UNKNOWN`. That is not an env var, alias, body-parsing, or function
bug — it's a plan/repo-visibility gate. Check, in order:

1. Is the repo private **and** the project on Hobby? → make public or upgrade.
2. Only then look at the dashboard **Build Logs** of a production deploy for a
   real build error.

Do **not** keep firing `vercel deploy --prod` from the CLI — they pile up as
stuck `UNKNOWN` deploys and the CLI calls hang. Use the dashboard to cancel
stuck builds and read logs.

## Caveat

If the repo is ever made **private again**, production deploys will stall the
same way unless the Vercel plan is upgraded. The daily refresh (which pushes data
to the private Blob, not to git) is unaffected either way — it doesn't depend on
a redeploy.
