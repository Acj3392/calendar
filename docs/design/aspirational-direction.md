# Aspirational Design Direction — Spending Calendar

> Who we want to be when we grow up.
> Written from the chair of a senior fintech designer (20 yrs), synthesizing a
> 12-site reference scout. This is a **direction doc**, not a spec — it sets the
> north star and offers three routes to it. Pick one (or the recommended blend),
> then we translate it into tokens and build.
>
> Date: 2026-06-02 · Status: **for your review** · Decision owner: Anna

---

## TL;DR

Twelve aspirational sites, four independent scouts, **one thesis they all
landed on**:

> **Make the shell quiet and the money loud. Render the number like a
> typographer, not a dashboard. Spend your whole motion budget on two moments.
> And run warm, never cold — this is the opposite of every blue-gray bank app.**

Everything below is in service of that sentence.

---

## What every scout agreed on (the non-negotiables)

These showed up in *all four* reports, studying completely different sites. When
the evidence converges this hard, it stops being taste and starts being the
brief. These are settled:

1. **Silent chrome, loud signal.** The interface stays near-monochrome and calm;
   **color means "money moved here," never decoration.** Spend intensity is the
   *only* thing allowed to be saturated. (Phosphor's black-on-white icons,
   ufo's colorless shell, Tilda's accents quarantined inside tiles, Godly's
   achromatic UI — unanimous.) In fintech, restraint *reads as competence*.
   Calm earns trust for free.

2. **The number is the hero — set it like display type.** One protagonist per
   view: today's total, the month's figure. Rendered huge, beautiful, and
   typographic — not as a widget. (Acanski's giant glyph, Tilda's serif total,
   Ujjo's Neue Machina hero, antlii's full-bleed stage.)

3. **Extreme type-scale contrast.** Enormous hero figure + *tiny, wide-tracked,
   uppercase* labels ("JUNE", "DAILY AVG", weekday). Almost nothing in between.
   **The gap itself is the hierarchy** — and it's what reads as "expensive."

4. **Warm, not clinical. Light + tinted, not white, not dark.** Every Godly pick
   was tagged *Light + Pastel*; Quake ran a sunset gradient; the studios stayed
   warm-neutral. **Sit on a soft, slightly-tinted cream/paper ground — not stark
   white, not dark mode.** This is the single biggest lever for "warm but
   trustworthy," and it's the antidote to the cold-blue cliché of finance UIs.

5. **A two-face type system: grotesk for numbers, a character face for voice.**
   The pattern was unanimous (Work Sans; Founders Grotesk + JHA Times Now;
   Neue Machina + Good Sans). **Clean grotesk for every numeral and UI label +
   one warm "voice" face for human moments** (greetings, "$0 spent today 🌱",
   month-in-review). The modern serif is the safe premium choice; a characterful
   display face is the riskier, more delightful one.

6. **Motion is contained and meaningful — budget exactly two moves.** Never
   decorative. The recurring winners:
   - **Digits count/redraw** when a total changes (Acanski's contained-glyph
     animation applied to money).
   - **Shared-element clip-reveal** when a day cell *expands* into its detail —
     not a modal that cuts in (antlii). This one move alone reads "premium."
   - *(Optional third:)* inertial month-to-month scroll so moving through time
     feels physical.

Everything past this point is where the scouts *diverged* — and that divergence
is exactly what gives us three distinct personalities to choose from.

---

## Three directions

Same non-negotiables above; three different souls. Each is viable. They differ
in **what the app's emotional center of gravity is.**

### Direction A — "The Ledger" 📒  *(trust-first)*

**The pitch:** A beautiful accounting book. Editorial restraint, hairline rules
dividing days like a ledger, a high-contrast modern **serif** for the hero
number, paper-cream ground with a whisper of texture. Reads like *Kinfolk*
meets a private bank.

- **Anchored in:** Tilda/Acanski (serif hero on calm gray), Sackville (Founders
  Grotesk + Times Now serif), ufo (restraint as luxury), atozsurfing (hairline
  ledger-rule framing).
- **Type:** Modern serif (Times Now / Canela / Fraunces) for figures + a quiet
  grotesk for labels.
- **Color:** Cream/paper ground, ink-black type, one warm accent. Spend
  intensity as a *muted* warm ramp inside cells.
- **Motion:** Minimal — count-up digits, gentle clip-reveal. Holds very still.
- **Feels like:** Calm, premium, grown-up, trustworthy. "My money is in good
  hands."
- **Risk:** Could tip *too* quiet — needs the celebratory moments (below) so it
  doesn't read austere.

### Direction B — "The Landscape" 🌅  *(emotion-first)*

**The pitch:** Your spending as a warm, living terrain. Borrowed wholesale from
Quake (the routemakers.org render): a month or year of daily spend rendered as a
**horizontal waveform/seismograph** — amplitude = dollars — in an aubergine →
magenta → coral → peach → pale-lime gradient. A glowing center seam = today, or
your budget baseline. Dry transaction data becomes an emotional, beautiful
"year in spending" hero that looks like *nothing else in personal finance.*

- **Anchored in:** Quake (data-as-landscape, sunset gradient), Ujjo
  (characterful display hero number).
- **Type:** Geometric display face (Neue Machina-ish) for the hero figure +
  grotesk for the grid.
- **Color:** The warm sunset gradient *is* the system — used as the spend
  heatmap and the waveform hero.
- **Motion:** The waveform breathes/ripples; digits count up; day-cells reveal.
- **Feels like:** Alive, distinctive, emotionally warm, share-worthy.
- **Risk:** Highest-effort (the waveform is a real build); gradient must stay
  *sophisticated*, not Instagram-filter. Trust comes from execution quality.

### Direction C — "The Playground" 🎛️  *(tactility-first)*

**The pitch:** A spending calendar that feels like an instrument. From Phosphor:
**every control re-skins the whole calendar instantly** — change "color by"
(category / amount / merchant), cell size, time grain, and the grid re-paints in
real time with motion. Springy day-cells that lift and preview on hover/press
(Godly), a "Surprise me" palette, "copy this view as a link" (shareable state),
**Phosphor icons** with their 6-weight axis as a feelings dial (Thin = future/
projected, Regular = normal, Bold/Fill = overspend), and playful, human
category names (Pattern Library's "Kale Salad" energy) instead of bank nouns.

- **Anchored in:** Phosphor (live playground, weight axis), Godly (hover-alive
  pill-button grid), Pattern Library (playful naming, celebratory full-bleed
  moments).
- **Type:** Friendly grotesk throughout, weight contrast for hierarchy.
- **Color:** Quiet shell, user-tunable spend palette.
- **Motion:** Lots — but all *responsive to touch* (instant, reversible,
  springy). The grid rewards poking.
- **Feels like:** A toy you can't stop fiddling with. Delightful, personal,
  "mine."
- **Risk:** Most likely to drift from "trustworthy" toward "playful" if the
  restraint slips. Tunability adds build + decision complexity.

---

## My recommendation 🧭

**Anchor on A (The Ledger) as the resting state, graft B's Landscape as the one
hero moment, and borrow C's touch-physics for micro-interactions.**

Here's the reasoning, as the fintech designer in the room:

- **Trust is the floor, not the ceiling.** A money app has to *first* feel safe
  and competent. The Ledger's calm, editorial restraint buys that on contact —
  it's the foundation. So the **default screen is quiet**: cream ground,
  hairline rules, serif hero number, muted warm spend ramp.

- **But calm alone is forgettable.** The thing that makes this app *yours* and
  share-worthy is **The Landscape** — so we deploy it as the **hero/payoff**,
  not the everyday chrome. A "Year in Spending" (or month-in-review) view that
  renders your data as the warm Quake waveform. Contrast is the delight: quiet
  daily grid ⇄ gorgeous landscape moment.

- **Touch is what makes it loved.** Borrow C's *physics* — springy cells,
  hover-to-preview, shared-element reveal, count-up digits, Phosphor icons on
  the weight axis — without adopting the full re-skinnable-playground
  complexity. (The live "color by" toggle is a great **phase 2**, not day one.)

In one line: **a private-bank ledger that opens into a sunset, and springs back
when you poke it.**

This blend is deliberately staged so we can build it in order of trust →
emotion → play, and ship value at each step.

---

## Who we are / who we're not

*A gut-check to hold every future design decision against.*

| We are… | We're not… |
|---|---|
| Warm cream paper | Cold blue-gray bank dashboard |
| One huge serif number | A wall of equal-weight widgets |
| Color = money moved | Color = decoration |
| Hairline ledger rules | Heavy spreadsheet gridlines |
| Two motion moments, perfected | Animation sprayed everywhere |
| Tiny tracked-out labels | Chunky UI chrome competing for attention |
| Phosphor icons, one family | Mixed emoji + icon sets |
| Human category names | Bank-statement nouns |
| Quiet daily, celebratory at milestones | The same flat intensity always |
| Restraint as confidence | Minimalism as emptiness |

---

## What this means for the current build

Honest gap analysis — where `index.html` is today vs. the aspiration:

| Element | Today | Aspiration |
|---|---|---|
| Ground | `#f7f7f5` near-white | Warm tinted **cream/paper** |
| Hero number | Inter 800, sans | **Modern serif** display figure |
| Labels | Inter, mixed sizes | Tiny, **wide-tracked uppercase** grotesk |
| Spend ramp | green→amber→red (cool-ish) | **Warm** aubergine→coral→peach |
| Accent | coral `#F4623A` | Keep — it's already warm & on-brief ✅ |
| Markers | 🏆 💚 emoji | **Phosphor icons** on weight axis |
| Day-open | DayDetail card appears | **Shared-element clip-reveal** |
| Total change | hard swap | **Count-up digits** |
| Hero view | none | **"Year in Spending" waveform** |

Good news: the bones (single-file, token-driven `THEMES`, tier system, warm
coral accent) are already pointed the right way. This is a *refinement and a
soul*, not a teardown.

---

## Open questions for Anna

1. **Direction:** the recommended blend, or commit to one pure direction?
2. **Serif appetite:** are you up for a modern serif hero number (premium,
   editorial), or keep it all-sans (safer, more neutral)?
3. **The waveform:** worth the build as a hero moment, or is that phase 2?
4. **Light + dark:** the references skew light/warm. Keep dark mode, or go
   light-only to commit fully to the warm-paper identity?

---

## Appendix — the 12 sites & what each taught us

| Site | The one steal |
|---|---|
| tilda.cc/madeontilda | Serif hero number on calm gray; color quarantined in tiles |
| atozsurfing.com | Hairline ledger-rule framing → trustworthy & tactile |
| routemakers.org (Quake) | **Spend-as-landscape** waveform in a warm sunset gradient |
| acanski.co | Animated/count-up number as the single contained delight |
| antlii.work | **Shared-element clip-reveal** for day → detail (premium transition) |
| ufo.studio | Colorless chrome, content supplies all color; whitespace as luxury |
| phosphoricons.com | **Phosphor icon family** + 6-weight axis as a feelings dial; live playground |
| thepatternlibrary.com | Playful human naming; subtle paper texture; full-bleed celebration moments |
| godly.website | Curatorial restraint; pill buttons w/ `+`; hover-to-come-alive cards |
| 3oo.store* | Pastel-bright-on-light grid logic for cells |
| sackville.co* | **Grotesk + modern-serif pairing** = the "warm but trustworthy" sweet spot |
| ujjo.com* | A characterful display face for the one hero number |

\* *Godly sites are 4-yr-dead links; learnings reconstructed from Godly's
authoritative metadata (typefaces, style tags) + design knowledge. A Wayback
Machine pass could recover their live motion if we want it.*

*antlii.work was down during the scout; its notes are directional, not freshly
observed.*
