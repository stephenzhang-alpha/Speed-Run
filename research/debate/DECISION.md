# DECISION — Anki-for-LSAT: Final Design Ruling

**Chair / moderator:** neutral synthesis of a completed four-lens design debate
(Dr. Vera Sorensen, cognitive scientist · Marcus Webb, LSAT coach · Priya Nair,
engineer · Sam Okafor, student-advocate), across two rounds, four research memos
(`01`–`04`), and two proposals (`B`, `C`).

**Status:** authoritative. Where the debate left an open question, this document
**rules** on it (§5) and the ruling is binding on the build order (§7). Where the
debate converged, this document records the merged design and the rationale (§3–§4).

**The one discipline that governs every ruling below.** We are buying **honest,
single-digit-percentile / ~4–7 scaled-point** gains, validated on **held-out,
unseen, exam-style items at equal study time with a bootstrap CI that excludes 0**
— *never* the drilled items, and *never* "2 sigma." The honest ceiling is
tutoring **d ≈ 0.37** (Nickow, Oreopoulos & Quan 2020), ITS **median d ≈ 0.66 but
only 0.13 on standardized vs 0.73 on local tests** (Kulik & Fletcher 2016),
mastery learning **d ≈ 0.52** (Kulik, Kulik & Bangert-Drowns 1990), and LSAT prep
**+4.3 pts at ES 0.40 / +7.26 pts for 9–10 practice exams, quasi-experimental**
(Dustman, Camilli & Gallagher 2021). Bloom's **+2σ** (Bloom 1984) is real in the
lab and **effectively debunked at scale** — no app reaches it.

**Verified LSAT format (LSAC, 2026).** Two scored Logical Reasoning sections + one
scored Reading Comprehension section + one unscored variable section; four 35-min
sections; scale 120–180; **Analytical Reasoning ("Logic Games") removed Aug 2024**
(swapping AR→LR2 moved the mean score by 1/100 pt over 218,243 sessions);
**in-center from Aug 2026**. Consequence: **LR is now ~2/3 of the scored test**,
it is **heavily speeded**, and it is **best-of-five with engineered distractors**.

---

## 1. Executive summary

### The final selected feature set

| # | Feature | One-line pitch |
|---|---------|----------------|
| **K** | **Per-Answer Annotation Store** (keystone) | Stop discarding the chosen distractor; capture `chosen` + `confidence` + `phase` per answer — the 20 lines that unlock everything else. |
| **1** | **ZPD Daily Engine (~85%)** | Serve each due topic at the difficulty where humans actually learn fastest, instead of the hardest card in the weakest topic. |
| **2** | **Distractor-Reasoning Engine** | Turn the trap you *actually* picked into a personal fingerprint, a one-tap "which trap got you?", and spaced why-is-(C)-wrong retrieval cards. |
| **3** | **Calibration + Hypercorrection Spaced Queue** | One tap of confidence exposes where you're "sure and wrong," then re-tests those confident misses on a spaced schedule so the fix sticks. |
| **4** | **Blind-Review "Gap Map" + Choke/Pacing MVP** | A timed→untimed second pass that tells you whether you *don't know it* or *ran out of time*, and routes each miss to the right fix. |
| **5** | **Fluency Gates (+ Structure Sprints)** | Retire a skill only when it's accurate **and** fast — training the automaticity that is the proven cure for choking. |
| **H** | **Transfer Meter** (honesty layer) | Refuses to call a schema "learned" until you're right on brand-new surface topics — the instrument that keeps every transfer claim honest. |

### The headline "what makes this app unique" claim (honest version)

> **"The only spaced-repetition app that reads *how* you got the LSAT question
> wrong — not just whether — and turns it into a measured study plan."**

Concretely, we are the only SRS (and unlike 7Sage / LSAT Demon / PowerScore /
LawHub) that captures, per answer, the **chosen distractor**, a one-tap
**confidence**, and the **timed-vs-untimed phase**, then converts them into (a) a
personal **trap fingerprint**, (b) a **human calibration curve** (are you as right
as you feel?), and (c) a **pressure-vs-knowledge diagnosis**. Plain Anki has none
of these axes (its ease buttons are a *prospective* self-rating never scored
against outcomes); LSAT competitors show static per-choice explanations but never
*schedule spaced distractor-rejection retrieval keyed to your trap profile* or
report a memorization-vs-transfer separation.

**What we do NOT claim.** No "2 sigma." No "think better / faster" broad transfer.
No "we adapt to your learning style" (Pashler et al. 2008 — debunked). No promised
anxiety cure. Every effect ships as a **measured `eval/` arm** (synthetic learners
first, real A/B later), reported honestly at its **time-matched** number.

---

## 2. Keystone — the Per-Answer Annotation Store

**Ruling: build this first. It is unanimous across all four debaters and both
rounds. It is the single highest-leverage change in the project — partly already
wired — and it unblocks features 2, 3, and 4.**

### Exact fields

Three additive fields on the `LSAT PerformanceEvent` notetype (`EVENT_FIELDS` in
`lsat/notetypes.py`), plus three new params on `append_event` and three new
attributes on the `PerformanceEvent` dataclass (`lsat/events.py`):

| Field | Type / values | Consumed by | Note |
|-------|---------------|-------------|------|
| **`chosen`** | selected letter `A`–`E` | Distractor-Reasoning Engine (2); Blind-Review honest-mastery filter (4) | **Already computed and discarded today** in `qt/aqt/lsat_performance.py` (`chosen = message[...]`), never passed to `append_event`. Near-free. |
| **`confidence`** | 3-way `sure`/`likely`/`guess` → probability (or 0–100) | Calibration + Hypercorrection (3); Blind-Review flagging (4) | One tap, sampled, skippable → stored empty ("unrated") when skipped. |
| **`phase`** | `timed` / `blind` / `relaxed` | Blind Review + Choke Index (4); honest-mastery filter | A blind pass is simply a **second event** for the same `item_id`; log stays append-only + HLC-ordered. Stamped from a session-mode flag — **needs no template change.** |

### Files touched

- **`lsat/notetypes.py`** — append `chosen`, `confidence`, `phase` to `EVENT_FIELDS`;
  change **only** `_ITEM_QFMT` (the confidence tap — `pycmd("lsatAnswer:<L>:conf=<n>")`,
  which auto-propagates to seeded collections via `_sync_templates`). `chosen`/`phase`
  are pure Python-side.
- **`lsat/events.py`** — three new optional params on `append_event`
  (`chosen=""`, `confidence=None`, `phase="timed"`); carry the fields on
  `PerformanceEvent`; make `read_events` read them **defensively** (`try/except
  KeyError` → `""`/`None`/`"timed"`) so pre-migration events parse instead of raising.
- **`qt/aqt/lsat_performance.py`** — stop discarding `chosen` (pass it through); parse
  the optional `:conf=<n>` suffix; stamp `phase` from the session-mode flag.
- **New `lsat/events.py::migrate_event_fields(col)`** — a real field migration
  (`col.models.add_field` + `update_dict`), because `ensure_notetypes` deliberately
  **does not** migrate an existing notetype's fields (only refreshes template HTML).

### Migration / sync caveat (on the record)

1. **Adding a field is a schema change → forces exactly one full (one-directional)
   sync.** Therefore **batch all three fields into a single `migrate_event_fields`
   bump** so we pay the full-sync cost **once**. If the psychometric family is ever
   funded, fold `b_difficulty` (ZPD's optional second field) into the **same** window
   to avoid a second full sync.
2. **Old events lack the new fields → readers must treat missing as "unknown" and
   abstain, never impute.** Calibration and the trap fingerprint skip unrated events.
3. **`phase` changes fold semantics.** Once Blind Review writes a *second* event per
   item, `fold_recent_performance` would **double-count** the timed + blind answer.
   The migration therefore ships **with a phase-aware fold** (default: count
   `phase="timed"` for mastery; use `blind`/`relaxed` only for the Choke Index and the
   honest-mastery filter). **This is the one behavioral change reviewers must sign off on.**

**No Rust. No proto.** The store is *read* by Python models that feed the existing
`(tag, weight, perf_mastery)` triples; the Rust queue never learns these fields
exist. Effort: **S**.

---

## 3. Selected features (the SHIP set)

Five features + the keystone + the Transfer Meter honesty layer. Each is presented
with (a) merged design, (b) persona/memo backing, (c) evidence + effect sizes,
(d) LSAT fit, (e) ratified UX constraints, (f) pre-registered held-out metric,
(g) implementation spec + effort/layer, (h) novelty.

---

### Feature 1 — ZPD Daily Engine (~85%)

**(a) Merged design & mechanism.** Keep the points-at-stake queue's *topic*
priorities, but among the cards it surfaces, serve the one whose predicted
P(correct) is closest to a tunable **τ ≈ 0.85** (band ~0.75–0.90, plus rare stretch
items), instead of blindly serving the hardest due card in the weakest topic. A thin
Python re-rank scores `value(card) = points(card) · zpd(P̂)` with `zpd` peaking at
τ. The learner simply experiences a winnable-but-effortful flow; the change is
silent.

**(b) Backing.** Memo `04`-F1. **Round-2 unanimous:** advocate's #1 ("if we ship one
thing, ship this"), coach's biggest changed-mind ("elevated from plumbing to the
daily backbone"), engineer promoted it from conditional into core, scientist
champion (CF18).

**(c) Evidence + effect sizes.** **STRONG (human study-choice) / MODERATE (the exact
85% figure).** Metcalfe & Kornell (2005/2003) — **8 experiments**: humans learn
fastest on the *easiest-not-yet-mastered* items and spend the most profitable time
at *medium* difficulty (a jROL stop rule), the **opposite** of the current queue.
Wilson, Shenhav, Straccia & Cohen (2019) — the "85% Rule" (15.87% error) is
*exponentially* faster than fixed difficulty, but it is a **neural-net/theoretical**
result, so we treat 85% as a tunable target, not a law.

**(d) LSAT fit.** The exam is a graded speed–accuracy task; a student stuck on
only-hardest items in their weakest type stalls, and weaker starters (who sit
furthest below their ZPD) gain the most (Dustman et al. 2021). Fixes a **real defect**:
`points = weight·(1−mastery)` ignores item difficulty entirely.

**(e) UX constraints (ratified).** **Zero added friction** (backend re-rank). Silent
framing — we *never* announce "we made this easier." Keep a band + rare stretch/reach
items so it never over-narrows. **Hard line:** the P≈0.5 mini-CAT is *not* this
selector (see §5.i, §6).

**(f) Pre-registered metric.** Δ held-out P(correct) at **equal study budget** vs
points-at-stake-only, with calibration **ECE ≤ `ECE_MAX` (0.05)** staying green; τ
ablatable; abstain to plain ordering when the performance model is thin.

**(g) Implementation.** New `lsat/selection.py` (pure Python) wrapping the returned
`PointsAtStakeEntry` list; reads `PerformanceModel.predict` (`lsat/models/performance.py`)
and item `difficulty`. **v1 re-ranks the entries the RPC already returns — zero Rust.**
Sharper with the optional `b_difficulty` field (deferred to the keystone's migration
window). `eval/ablation.py` gains a `+zpd` arm. **Effort: S→M. Layer: Python only.**

**(h) Novelty.** Anki has no difficulty-targeted selection; no LSAT product tunes
item difficulty to a per-skill ~85% target. Deliberately the **inverse** of the
(rejected) measure-at-0.5 mini-CAT.

---

### Feature 2 — Distractor-Reasoning Engine

**(a) Merged design & mechanism.** One feature on one substrate (`chosen`), fusing
three Round-1 proposals:
- **Trap Profile / Leech** — map each chosen *distractor* to a trap family
  (`skill.trap.*`: out-of-scope, extreme-language, reversal, half-right, irrelevant
  comparison) and fold errors by that label into a per-student fingerprint
  ("extreme-language owns 38% of your Strengthen misses").
- **Structured why-wrong tap** — on a **miss or confident-wrong item only**, a single
  **competitive multiple-choice** micro-question: *"which trap is (C)?"* with plausible
  trap-family options. Because the options are competitive, this is the same
  competitive-MC *retrieval* that earns the large effect — not mere recognition — and
  it is **deterministically gradeable** (no noisy free-text AI grading).
- **Trap Retrieval** — for missed items, the AI pipeline emits spaced
  why-is-(C)-wrong micro-cards, one per plausible distractor, entering FSRS +
  points-at-stake keyed to the letters you actually pick.

The immediate why-wrong tap and the spaced Trap-Retrieval card are **the same
mechanism at two moments** — one at answer time, one on an FSRS schedule.

**(b) Backing.** Memos `01`-F1, `02`-F3, `03`-F3, `B`-F3, `R2`. **Unanimous flagship:**
scientist's #1–#2 (merged), coach's C1 ("the single most diagnostic byte, thrown
away"), engineer's #3 ("biggest differentiated payoff"), advocate's insight quadrant.

**(c) Evidence + effect sizes.** **STRONG.** Multiple-choice practice testing
**g = 0.70** (Adesope, Trevisan & Sundararajan 2017; larger than short-answer 0.48).
The gain appears **only when distractors are competitive/plausible** — the learner
then retrieves *why the right answer is right AND why each wrong answer is wrong* —
and it aids the distractor-related material with **no net retrieval-induced forgetting**
in a classroom replication (Little, Bjork, Bjork & Angello 2012; Little & Bjork 2015;
Bjork, Little & Storm 2014). Articulating the rejection rationale is prompted
self-explanation, **g = 0.55 [.45, .65]** (Bisra, Liu, Nesbit, Salimi & Winne 2018;
Chi et al. 1989). **Honest caveat:** self-explanation prompts *negatively* moderated
the worked-example effect in one math meta-analysis (Barbieri et al. 2023) — so the
tap ships **A/B'd**, not assumed. Integrating the distractor with the correct answer
is the **RIF-safe** design (Anderson & McCulloch 1999; RIF exists but is bounded,
Murayama et al. 2014 g = 0.35).

**(d) LSAT fit.** The LSAT *is* best-of-five with *engineered* traps; "explain why
each wrong answer is wrong" is the canonical high-scorer habit; a distractor is a
diagnosis, not noise (Sadler 1998, via `R2`). We already ship a `skill.trap.*`
taxonomy — targeting the learner's *actual* wrong-letter distribution turns a generic
drill into a personal weakness hunter across the ~2/3-of-the-exam LR types.

**(e) UX constraints (ratified).** Trap capture = **zero added friction** (already in
the hook). Why-wrong tap = **one select-tap from the trap menu**, **on misses /
confident-wrong only**, never on correct answers, zero typing in the timed loop; one
optional free-text line as a *sampled bonus*, untimed only. Profile surfacing is
**passive** (dashboard / session boundary), **never interrupts an item**. Framing
names the **fixable habit**, never the person; abstain until ≥ N misses of a trap type;
show at most **one headline pattern per session** (§5.v).

**(f) Pre-registered metric.** Δ P(correct) on **unseen same-trap** items at equal
study time (CI excludes 0); **A/B: no-tap vs tap-only vs tap+free-text** (settles the
Barbieri risk empirically); secondary: repeat-trap rate per study-hour ↓. Generated
cards clear `CARD_CHECK_PASS_RATE_MIN` (0.70) / `CARD_CHECK_WRONG_RATE_MAX` (0.02) and
the checker's `CHECKER_FALSE_PASS_MAX` (0.02).

**(g) Implementation.** New `lsat/error_patterns.py` folds events by chosen→trap
label; AI `card_type:"distractor_rejection"` in `lsat/ai/{prompts,generator}.py`
(the generator's `Card` already carries `card_type`) gated by the existing
fail-closed `lsat/ai/checker.py` (verbatim-span requirement); trap-granular priority
via `topic_weights_for_queue` (Python-only, no Rust); the trap menu extends
`_ITEM_QFMT` → `qt/aqt/lsat_performance.py`; per-trap mastery bars in
`lsat/dashboard_data.py` → `ts/routes/lsat-dashboard/`. **Effort: M. Layer:
Python + AI pipeline + web. No Rust/proto.**

**(h) Novelty.** Anki has no distractor modelling; our AI pipeline currently
generates from *source text*, not from the learner's *own error pattern per option*.
Competitors show static per-choice explanations; **none** schedule spaced
distractor-rejection retrieval keyed to your trap profile, and Anki's "leech" is a
*card-level* flag, not an error-*type*-level diagnosis across items.

---

### Feature 3 — Calibration + Hypercorrection Spaced Queue

**(a) Merged design & mechanism.** The instrument and its controller, merged:
- **Calibration monitoring** — one-tap confidence → a **reliability curve** (stated
  confidence vs actual accuracy), a per-skill **Overconfidence Index** =
  mean(confidence) − mean(accuracy), and a **Resolution** score = `auc(confidence,
  correct)`, plus a ranked **"sure-and-wrong" list**.
- **Hypercorrection spaced queue** — the queue leads with **high-confidence misses**,
  frames the correction as a **surprise** ("you were 90% sure — here's why (E) beats
  (B)"), and **re-tests each on a spaced schedule with a fresh same-trap item** so the
  fix survives.
- **Honest-mastery filter** — the `phase` field lets `fold_recent_performance` drop
  lucky *timed* wins from the mastery estimate.

**(b) Backing.** Memos `03`-F1/F2, `B`-F2. **Unanimous:** every debater, both rounds.
Advocate promoted it optional→core once the framing was pinned down.

**(c) Evidence + effect sizes.** **STRONG (as an instrument + as hypercorrection).**
Monitoring/control is foundational (Nelson & Narens 1990). Confidence ≠ accuracy is a
robust *description* on logic tasks — bottom-quartile performers scored at the **12th
percentile but rated themselves ~62nd–68th** (Kruger & Dunning 1999). **High-confidence
errors are corrected *more* readily** (hypercorrection), driven by surprise (a P3a
ERP), immediately and at delay (Butterfield & Metcalfe 2001; Metcalfe 2017; γ ≈ .51,
Eich et al. 2013) — **but they *return* without re-practice** (Butler, Fazio & Marsh
2011), so the **spaced re-test is mandatory, not optional**. Judgments of learning are
driven by fluency, not learning (Rhodes & Castel 2008), so we capture confidence at
the *graded* moment and prefer delayed judgment (Nelson & Dunlosky 1991).
**Discipline:** we measure *the individual's* reliability curve and **never invoke
the Dunning–Kruger *mechanism***, which is mostly a statistical artefact (Gignac &
Zajenkowski 2020, Glejser r ≈ −0.05).

**(d) LSAT fit.** On a tight 120–180 curve a handful of confident misses move the
score; the best-of-five format is *engineered* to manufacture confident errors via
seductive traps (our `skill.trap.*`). The confident-and-wrong moment is the
single highest-ROI review target.

**(e) UX constraints (ratified).** Confidence = **exactly one tap** (`sure`/`likely`/
`guess` buttons, **not a slider**), captured at/after the graded answer; sampling per
§5.vi; auto-downsample on detected fatigue; always skippable. Hypercorrection adds
**zero friction** (rides the tap). Framing: **surprise/insight**, *"you were sure —
here's the trap"*, **never "wrong again."** **Blend, don't replace** — bounded boost,
capped session share, distributed (never a front-loaded wall of misses). Re-test with
a **fresh** item where possible.

**(f) Pre-registered metric.** *Monitor:* within-user **ECE ↓** and **Resolution
AUC ↑** over practice. *Control:* **delayed correction rate of high-confidence errors
(γ, target .3–.5)** with the mandatory spaced re-test; **relapse rate ↓**.
*Honest-mastery:* does dropping lucky-timed wins improve held-out next-answer prediction?
Variance/AUC check kills degenerate flat ratings; abstain below an event floor.

**(g) Implementation.** New `lsat/models/calibration.py` reusing `eval/metrics.py`
verbatim (`reliability_bins`, `ece`, `auc`, `brier`, `bootstrap_ci`); a **bounded
boost** in `lsat/events.py::topic_weights_for_queue` (Python-only, no Rust); a panel
in `lsat/dashboard_data.py` → `ts/routes/lsat-dashboard/`. **Effort: S–M. Layer:
Python + web. No Rust/proto.**

**(h) Novelty.** Anki's Again/Hard/Good/Easy is a *prospective* self-rating **never
scored against outcomes**; our built ECE measures the *model's* calibration. This
measures the *human's* — an orthogonal new axis — and adds a theory-backed new
study-priority signal (confidence-at-time-of-error) the recency queue lacks.

---

### Feature 4 — Blind-Review "Gap Map" + Choke/Pacing MVP

**(a) Merged design & mechanism.** A timed set → an **optional, untimed second pass**
over **flagged / low-confidence / skipped items only**; the learner commits a final
confident answer **before** anything is graded (grading deferred in code — the "don't
peek" rule). Then a per-skill **2×2 Gap Map**:

| | Blind ✓ | Blind ✗ |
|---|---|---|
| **Timed ✓** | **Mastered** | **Fragile/Lucky** (not credited as mastery) |
| **Timed ✗** | **Pressure/Technique** → pacing/automaticity | **Knowledge** → content/hypercorrection |

Folded in for free from the same `phase` data: the **Choke Index** = relaxed/blind
accuracy − timed accuracy, plus a **speededness** metric (unattempted vs missed) and a
**consented per-item pacing ramp** — the **pacing MVP**. (The faithful full-section
simulator is **deferred** — see §5.i, §6.)

**(b) Backing.** Proposal `B`-F1; memos `03`-F5, `04`-F5. Coach's signature headline;
engineer's flagship for `phase` + pacing MVP; advocate conceded it into core once
scoped ("the most de-shaming diagnostic we have"); scientist accepts the `phase`
honest-mastery filter as *measurement*.

**(c) Evidence + effect sizes.** **Mixed by component — billed accordingly.** Blind
Review itself is **7Sage community best-practice, NOT an RCT** — its *mechanisms* are
strong (miscalibration: Kruger & Dunning 1999; learning-from-confident-error:
Metcalfe 2017; withheld-feedback retrieval blocking the re-reading fluency illusion:
Dunlosky et al. 2013, which rates re-reading/highlighting **LOW** utility). Pacing:
the **format facts are LSAC-official STRONG** and *that* speededness costs points is
the construct, not a hypothesis; the **skip/guess policy is MODERATE** (a heuristic).
Choking is real — pressure eats the working memory the ablest rely on (Beilock & Carr
2005) — and **automaticity removes it** (Beilock et al. 2004: problems practiced 50×
showed no choking). The opt-in anxiety-writing reset is **CONTESTED** (Ramirez &
Beilock 2011 d = 0.57 → Myers, Davis & Chan 2021 clean null).

**(d) LSAT fit.** Running out of time is the #1 score-killer, and **two of three
scored sections are now LR at ~1:24/question** — pacing is doubly decisive. Blind
Review is the *only* feature that produces the pressure-vs-knowledge counterfactual and
makes mastery **honest** (today a lucky timed guess counts as mastery and suppresses a
topic that still needs work).

**(e) UX constraints (ratified).** Second pass **scoped** to flagged/low-conf/skipped,
**opt-in** (strong but skippable nudge — §5.iv), **always an untimed "learn" mode**,
consented ramp that tightens **only as accuracy holds**. The full written why-right/
why-each-wrong autopsy lives **here** (untimed friction sandbox), select-first,
type-optional. Framing: *"Untimed you're 88%, timed 71% — that gap is pacing, not
knowledge, and pacing is faster to fix"* — de-shaming, **never "you're too slow."**
Anxiety reset **opt-in, default-off, measured, promises nothing.**

**(f) Pre-registered metric.** Primary: held-out **timed** P(correct) on unseen items
at equal budget, "gap-routing + honest-mastery" vs "all-correct = mastery." Secondary:
(a) Fragile/Lucky rate ↓ over time; (b) **routing-validity** — do pressure-gap items
improve after *pacing* drills and knowledge-gap items after *content*?; (c) timed→blind
convergence for coached skills. Choking: does automaticity training shrink the Choke
Index?

**(g) Implementation.** New `lsat/blind_review.py` (builds the BR set, joins the two
phases per `item_id`, emits the 2×2 + per-skill gap, drives the honest-mastery filter);
the **phase-aware fold** from the keystone; a session-mode toggle (timed/blind/relaxed)
in `qt/aqt/lsat_performance.py` (the hook stamps `phase`); a **Timed vs Blind** 2×2
panel in `ts/routes/lsat-dashboard/`; Choke Index + speededness fall out of the same
data (a small `lsat/pacing.py` or folded in). `eval/blind_review.py` ablation arm. The
queue change is **Python-only**. **Effort: L. Layer: Python + qt reviewer + web + eval.
No Rust/proto.**

**(h) Novelty.** Vanilla Anki has a single graded pass, a prospective ease button, no
confidence, and no untimed counterfactual; our `timing_z` covariate knows you were
slow but cannot tell "slow-but-capable" from "incapable." No general SRS models the
timed/untimed distinction; competitors sell timed PrepTests but not an *optimized,
measured* pacing policy or a pressure-vs-knowledge split.

---

### Feature 5 — Fluency Gates (+ Structure Sprints)

**(a) Merged design & mechanism.** A skill retires only when the learner is **accurate
AND fast** (RT-aware mastery), shown as a passive **Not-yet → Effortful → Automatic**
badge. Folded in: **Structure Sprints** — seconds-long, game-like "name the
type/flaw/conclusion" classification drills, RT-scored — which drive recognition time
down and feed pacing. Kept **only because it is cheap and rides existing latency data**;
the most provisional pick.

**(b) Backing.** Memo `R1` (perceptual learning / ARTS). Coach's #5 (Structure Sprints
folded in); advocate's champion (the drill students actually enjoy opening + the
anti-choke lever); scientist/engineer accept it **as a measured ablation arm**, not a
headline.

**(c) Evidence + effect sizes.** **MODERATE, LSAT-transfer unproven.** Automaticity is
the proven **anti-choke** mechanism (Beilock et al. 2004: 50×-practiced problems show
*no* choking); RT-aware adaptive scheduling (ARTS) beats fixed schedules (Mettler,
Massey & Kellman 2016); the large perceptual-learning classification effects
(Kellman et al., d ≈ 0.84–2.69 adjacent) are **adjacent-domain (aviation/medical/math),
with LSAT transfer inferred, not proven** — and bounded by an honest ultrasound null.
So it ships as an ablation arm, parked if it doesn't lift held-out timed accuracy.

**(d) LSAT fit.** "Accurate but slow" is the exact mid-160s plateau; expert LR advice
is literally "classify the question type in under ~3 seconds." Non-automatic
recognition is the root cause of most pacing failures, so this composes directly with
Feature 4.

**(e) UX constraints (ratified).** Badge is **passive (zero friction)**; sprints are
**Light** friction, game-like, genuinely fun. Framing: **"becoming automatic" /
"Automatic!"**, **never "you're too slow"** (no speed-shaming). Guard RT-gaming with an
accuracy co-criterion + timeout.

**(f) Pre-registered metric.** Does speeded classification / RT-aware retirement lift
**held-out *timed* P(correct)** at equal study time (CI excludes 0)? If not, it is
parked. Must not degrade calibration (`ECE_MAX`).

**(g) Implementation.** Extend the mastery notion to RT-aware (reads the
already-captured `response_ms`); a small drill surface + a passive dashboard badge in
`lsat/dashboard_data.py` → `ts/routes/lsat-dashboard/`; `eval/` arm on held-out timed
accuracy. **Effort: S–M (rides existing latency data). Layer: Python + web. No Rust.**
The moment it needs bespoke content, it waits.

**(h) Novelty.** Anki's mastery is memory-of-a-card (FSRS), never speed-gated; no LSAT
product applies RT-aware retirement or an automaticity badge; LSAT courses give generic
"pacing tips," not a per-skill fluency gate.

---

### Honesty layer — Transfer Meter (report-only)

**(a) Merged design & mechanism.** Per argument-structure schema, a two-state badge:
**"Memorized here"** vs **"Transferred."** Compute **surface distance** `d = 1 −
cosine_surface(item, seen)` (existing tf-idf vectors, logical-marker tokens
down-weighted), then report the **memorization gap** = P(correct|near) − P(correct|far),
the **transfer index** = P(correct|far), and the **structure slope** β in
`P(correct) ~ ability + β·d + difficulty`. It refuses to call a schema learned until
you're right on **new surface**.

**(b) Backing.** Memos `02`-F5, `C`. Scientist's honesty instrument (a **precondition**,
not optional); engineer's cheap report-only layer; advocate's endorsed backend
instrument; coach's scoreboard for any transfer feature.

**(c) Evidence + effect sizes.** **STRONG (measurement caution) / MODERATE (variability
drill).** Structure-vs-surface sorting is the classic expertise read-out (Chi,
Feltovich & Glaser 1981); transfer must be reported as a **distance-graded curve, never
a single number** (Barnett & Ceci 2002 — 9 dimensions, "a single far-transfer effect
size is misguided"); schema quality predicts transfer (Gick & Holyoak 1983).

**(d) LSAT fit.** The exam *is* one-skill-across-endless-topics; a student right on
"the vaccine causal flaw" but wrong on "the ad-revenue causal flaw" has memorized, not
learned. The meter measures the exact thing the test measures.

**(e) UX constraints.** **Feather / backend**; abstains until enough new-surface items
exist; badge names the schema, not the person.

**(f) Pre-registered metric.** Report-only first (like `eval/paraphrase.py`): the gap,
the transfer index, and β with `bootstrap_ci`; the leakage cosine gate (`LEAK_COSINE_MAX`
0.90) ensures no surface wording leaks into the held-out set. **It is the gate on
Structure Twins** (§5.ii).

**(g) Implementation.** New `eval/transfer.py` (report-only, reuses `eval/leakage.py`
cosine + `bootstrap_ci`); a `struct.*` tag namespace in `lsat/taxonomy.py` +
`lsat-taxonomy.yaml` (just more node ids — no schema migration); a dashboard badge.
**Effort: S–M. Layer: eval + web. No Rust/proto.**

**(h) Novelty.** Extends `eval/paraphrase.py` from same-item rewording to cross-item,
same-structure, distance-graded transfer. **No competitor reports a memorization-vs-
transfer separation per argument schema.**

---

## 4. How the selection EVOLVED (the rationale record)

### Round 1 — four lenses, four different straw-men

| Lens | Round-1 straw-man | Strongest cut |
|------|-------------------|---------------|
| **Scientist** (Sorensen) | Distractor-Reasoning Engine (Trap Retrieval + Trap Autopsy, **free-text**), Successive Relearning, Calibration Monitoring, Hypercorrection Spaced Queue, ZPD + Transfer Meter; Structure Twins as conditional 6th | Single-user **CDM** |
| **Coach** (Webb) | Trap Profile, Blind Review, **full Pacing Engine/section simulator**, Hypercorrection, Structure Sprints | CDM, BKT, mini-CAT, mastery-gating |
| **Engineer** (Nair) | Keystone + Trap Retrieval/Leech, Calibration+HC, Blind Review, Transfer Meter→Twins; **ZPD only conditional** | CDM / DKT |
| **Advocate** (Okafor) | ZPD, Confidence+Calibration+Trap-profile, Fluency Gates+Structure Sprints, Choke/Pacing; Hypercorrection optional | **Daily P≈0.5 mini-CAT** |

The scientist's Round-1 opener already noted the ~25 candidates collapse onto a
handful of mechanisms, and that a tiny capture change (`chosen` + `confidence`)
unlocks four features — the seed of the keystone.

### Round 2 — the concessions that produced convergence

- **Scientist conceded:** (1) the engineer's **one-schema-bump keystone** and
  **evidence-per-build-hour** ordering (cheap Python wins ship before heavy AI/relearning
  features); (2) **her biggest change — "select-not-type":** the flagship autopsy moved
  from *free-text* to a **one-tap competitive-MC why-wrong selection** (misses-only),
  free-text demoted to a *measured optional bonus*, because a stressed learner won't type
  a paragraph per item for three months and typing eats the working memory Beilock &
  Carr document; (3) the advocate's **P≈0.5 hard rule** — the daily engine runs at ~85%;
  (4) the coach's **timed-vs-untimed mode declaration**; (5) Blind Review's `phase`
  honest-mastery filter as *measurement*. She **merged 5 ships → 4 core + 1 conditional**.
- **Coach conceded:** (1a) **his biggest concession** — score claims must be **measured
  on held-out items at equal time (CI excludes 0), honest ceiling ~4–7 points, not "2
  sigma"**; (1b) **ZPD ~85% runs the daily engine** and the clock is a deliberate tool
  "not the water supply" — which **demoted his own standalone section simulator**; (1c)
  hypercorrection's **spaced re-test is mandatory** (Butler, Fazio & Marsh); (1d) fund
  the cheap pacing diagnostic before the simulator, the queue is Python-steerable, batch
  the migration, and volume ("more PrepTests") is the weak lever (Macnamara). He **held**
  pacing under realistic format and capturing the chosen distractor.
- **Engineer conceded:** **ZPD into core** (from conditional) and **Structure Twins out
  of core** (to a gated phase-2). Locked the keystone spec (`migrate_event_fields`,
  defensive reads, phase-aware fold), ruled the section simulator **data-blocked** (seed
  has 4 items; a faithful section needs ~25), and ruled **BKT gate-not-build**.
- **Advocate conceded:** (1) **timed pressure is necessary and can be *protective*** —
  Blind Review and a consented pacing ramp moved **into core**, reversing his "adherence
  poison" stance; (2) **select-not-type** structured why-wrong is fine; (3) the
  confidence tap is one tap and **earns its friction**; (4) **felt-fluency is a liar** —
  optimize for *sustainable effort*, not comfort (so the daily engine sits at ~85%, a
  desirable difficulty, and the substrate stays graded retrieval, never re-reading). He
  promoted hypercorrection (optional→core) and delivered the binding **Friction Budget**.

### What MERGED

- **Trap Autopsy + Trap Retrieval + Trap Profile/Leech → the Distractor-Reasoning
  Engine** ("the same competitive-MC mechanism at two moments, one substrate: `chosen`").
- **Calibration Monitoring + Hypercorrection Queue → one stack** ("the instrument and
  its controller").
- **Blind Review + Choke Index + per-item pacing MVP → one feature** (all ride `phase`;
  the Choke Index is a free read-out).
- **Structure Sprints folded into Fluency Gates.**
- Memo duplicates resolved: `02`-F1 ≡ `C`-Twins (**Structure Twins**); `02`-F5 ≡ `C`
  (**Transfer Meter**); `03`-F5 (choke) ⊂ Blind Review's `phase` data.

### What was CUT, DEMOTED, or DEFERRED — and why (see §6 for the full list)

- **CUT (unanimous):** single-user **CDM/DINA/G-DINA** and **DKT** (overfit one sparse
  user); **daily P≈0.5 mini-CAT** as a study engine; **feedback-timing as doctrine**
  (kept as a knob); **expressive/anxiety writing as a promise**; **mandatory typed
  articulation**; **punitive gamification**.
- **DEMOTED:** the **full section simulator** (→ pacing MVP now); **Successive
  Relearning** (kept in backlog, demoted in priority — it *consumes* the scarce prep
  window and is time-matched **d ≈ 0.28**, not the headline 4.19).
- **DEFERRED / gated:** **Structure Twins** (behind the Transfer Meter); **BKT** (must
  beat the recency fold on held-out AUC first); the **faithful section simulator**
  (behind a real item bank).

---

## 5. Moderator rulings on the open questions

Each debater's Round-2 memo forwarded a list of open questions. I rule firmly.

**(i) Full section simulator vs. cheap pacing/Choke MVP now.**
**Ruling: ship the pacing/Choke MVP now; DEFER the faithful 2LR+1RC section simulator
behind a real, checker-gated item bank.** The engineer's decisive finding: the
simulator is **data-blocked, not code-blocked** — the taxonomy wants ~25 calibrated
items per section (76 scored), and `lsat/seed.py` ships **four** `LSAT Item`s. A
simulator degraded to short sets loses the realism that was its entire value, and a
half-faithful mock is "anxiety without fidelity" (advocate). The MVP — a per-item
budget + session clock stamping `phase="timed"`, plus speededness and the Choke Index —
rides the keystone and the timing we already capture, gives the coach the score-relevant
pacing diagnostic, and gives the advocate the de-shaming message, with **no new item
bank**. The simulator is named as the **next timed-execution build the moment the bank
supports a faithful section** — not quietly dropped.

**(ii) Structure Twins fund-now vs. gate-on-Transfer-Meter.**
**Ruling: gate on the Transfer Meter.** Ship the Meter (report-only) first; fund Twins
**only once the Meter proves (a) the AI can mint valid twins** — surface-distinct,
same-`struct`, verbatim-span, clearing `CHECKER_FALSE_PASS_MAX` (0.02) — **and (b)
twin-training lifts far-surface P(correct) with a CI excluding 0.** The transfer
*evidence* is the strongest in the set (Gentner et al. 2003: 47% vs 6%; Loewenstein et
al. 1999: ~3×), but its top risk is **AI content-validity** — a secretly
structure-mismatched twin teaches the *wrong* schema — and that risk is unmitigated
until the Meter can see it. This is not a phase-1 ship. (Untimed mode only,
fill-by-select, per the advocate's working-memory constraint.)

**(iii) Blind Review as measured diagnostic vs. marketing.**
**Ruling: build it as a headline feature, describe it as a *measured diagnostic*.** The
coach is right that it is the signature high-scorer technique and the only feature
producing the pressure-vs-knowledge counterfactual; the scientist is right that it is
**7Sage community practice, not an RCT.** We resolve the billing dispute cleanly: the
**honest-mastery filter** (dropping lucky timed wins) is pure *measurement* and ships
unconditionally; the **routing claim** ("pressure items improve after pacing, knowledge
items after content") is an **empirical hypothesis that must pass the routing-validity
eval before any evidence-based claim is made externally.** Headline the *capability*
("see whether you don't know it or ran out of time"), never an unproven outcome.

**(iv) Pacing default-on vs. opt-in.**
**Ruling: opt-in, with an always-available untimed "learn" mode and a strong,
skippable nudge toward timed practice.** Pacing is the #1 score-killer (coach), so the
nudge is strong; but pressure hurts the ablest most (Beilock & Carr 2005) and the
advocate is right that a weaponized clock manufactures the exact choking we're trying to
cure. The ramp tightens per-item budgets **only as accuracy holds**, by consent. The
**Choke Index runs passively** on whatever timed/blind data exists — diagnosis is free
and never punitive. Anti-choke effort is prioritized **automaticity (Fluency Gates) >
consented ramp > opt-in anxiety writing** (the last is contested; Myers 2021 null).

**(v) How much insight before it demoralizes (dosage).**
**Ruling: one headline "fixable pattern" + its route per session; the fuller diagnostic
lives on a pull-not-push dashboard.** The insight quadrant is the app's motivational
engine, but three simultaneous "here's what you get wrong" signals tip into
discouragement. Every signal **names the fixable habit, never the person**
("extreme-language owns your Strengthen misses," never "you're bad at Strengthen"),
frames errors as **surprise/insight** (never "wrong again"), and **abstains below the
evidence floor** — never "you're bad at X" from 4 data points. No streak-shaming, no
speed-shaming.

**(vi) Confidence sampling rate.**
**Ruling: capture confidence on *every miss and confident-wrong item*, sample every Nth
hit (default N = 3), auto-downsample under detected fatigue, always skippable →
"unrated," and readers abstain on unrated events.** The features that depend on the
signal (hypercorrection, calibration) need it *precisely on misses*, so misses are
never sampled out; hits are sampled to protect the friction budget. The rate is a
config knob with this pre-set default and an abstain-floor, so we neither starve
Feature 3 nor make the tap "the thing people quit over."

---

## 6. Cut & deferred list

| Item | Disposition | Reason |
|------|-------------|--------|
| **CDM — DINA / G-DINA attribute profile** | **CUT** (unanimous; the strongest cut of scientist, coach & engineer) | Strong psychometrics (de la Torre 2009/2011) that **overfits one sparse single-user log**; the Q-matrix is unvalidatable on one person (Rupp & Templin 2008), posteriors go wide, a wrong "attribute not mastered" flag **mis-gates** other features, and it **duplicates** the cheaper observed-data Leech fingerprint (Feature 2). |
| **DKT — Deep Knowledge Tracing** | **CUT** | The famous 25% AUC edge (Piech et al. 2015) was largely an **evaluation artifact**; a properly-run, extended **BKT is statistically indistinguishable** (Khajah, Lindsey & Mozer 2016). A single user's per-skill sequences are far too short for an RNN — it would fit noise. |
| **Daily P≈0.5 mini-CAT** (as the study engine) | **REJECTED as a daily driver** (advocate's strongest cut; scientist adopted as a hard rule) | Serving items calibrated to make you wrong **half the time, every day** is the *opposite* of the region of proximal learning (Metcalfe & Kornell 2005) and the 85% rule (Wilson et al. 2019) → collapsing self-efficacy, learned helplessness, abandonment. **Measuring** and **practicing** are opposite-difficulty jobs. Survives **only** as a rare, opt-in, explicitly-labeled "level check." |
| **Full 2LR+1RC section simulator** | **DEFERRED** (behind an item bank) | **Data-blocked, not code-blocked:** needs ~25 calibrated items/section; `seed.py` has **4**. Building the bank is an L AI-content project inheriting the twin content-validity risk. Ship the **pacing MVP** now (§5.i). |
| **Structure Twins** | **DEFERRED** (gated on the Transfer Meter) | Best transfer *evidence* in the set, but the top risk is **AI content-validity** — a mismatched twin teaches the wrong schema — unmeasurable until the Meter exists (§5.ii). New notetype + compare UI = a real M build on the set's biggest unmitigated risk. |
| **BKT — Bayesian Knowledge Tracing** | **DEFERRED** (gated, not built) | Interpretable and cheap (Corbett & Anderson 1995), and the *correct* choice over DKT — but it **starves and abstains** on sparse single-user data and has identifiability issues (van de Sande 2013). **Earns a slot only if it beats the recency fold (`fold_recent_performance`) on held-out next-answer AUC by `PERF_MIN_DELTA_AUC` (0.05).** Until then, the recency fold stands. |
| **Successive Relearning (priority)** | **DEMOTED / DEFERRED in priority** (kept in backlog) | Durable-learning heavyweight — ~80% vs ~20% recall at 1 week, **d ≈ 4.19** (Rawson et al. 2018); +≥10% course exams, ds 0.54–1.10 (Janes et al. 2020) — **but time-matched it collapses to d ≈ 0.28** (Higham et al. 2022 via Rawson et al. 2013), and our users have **fixed prep hours**. It *consumes* the scarce resource, so it drops below the cheap Python wins and the flagship. When funded, the "pattern" is the **trap schema** so it composes with Feature 2 (no second loop); cap concurrent loops; **no streak-reset shaming**. |
| *Also parked* (evidence real, ROI/fit lower now) | **DEFERRED** | Prime-then-Read prequestions (no generalization to untested, Pan & Carpenter 2023); Commit-First / productive failure (heterogeneous, **g = −0.03 for procedural**, Sinha & Kapur 2021); Faded Parallels (MODERATE fading specifics, rarest LR types); Skeleton Builder / argument mapping (advocate-led quasi-experimental, van Gelder 2005; Willingham 2007; heaviest UI); Spot-the-Structure Sort (Transfer Meter gives the same read-out from logged answers); SRL loop, DP micro-loops, mastery-gated advanced types (thin/duplicative on one user). |
| **Feedback-timing as doctrine** | **CUT as a headline** (kept as a config knob) | Genuinely **CONTESTED** — 16 delayed / 12 immediate / 11 null (Smith & Kimball 2010) vs Butler, Karpicke & Roediger 2007 vs Kulik & Kulik 1988. Ship as a measured toggle; let `eval/` pick the default. |
| **Expressive / anxiety writing as a promise** | **CUT as a claim** (opt-in, default-off, measured) | d = 0.57 (Ramirez & Beilock 2011) → **clean null** across four authentic exams (Myers, Davis & Chan 2021). Promised to no one. |
| **Learning-styles / modality matching** | **VETOED on sight** | Debunked (Pashler, McDaniel, Rohrer & Bjork 2008). |

---

## 7. Implementation build order

Staged **keystone → cheap Python → AI-pipeline flagship → heavy flagship → cheap
add-on**, following the engineer's evidence-per-build-hour ordering. Every stage ships
with an `eval/<feature>.py` ablation arm (equal **time**, primary metric = held-out
exam-style items, `bootstrap_ci` excluding 0) — the honesty convention of the existing
`INTERLEAVE_BONUS`. **No stage touches Rust or proto.**

### Stage 0 — Keystone (do first; unblocks 2, 3, 4)
- **`lsat/notetypes.py`:** append `chosen`, `confidence`, `phase` to `EVENT_FIELDS`;
  add the confidence tap to `_ITEM_QFMT` (only template change).
- **`lsat/events.py`:** new params on `append_event`; carry fields on
  `PerformanceEvent`; **defensive `read_events`**; new **`migrate_event_fields(col)`**;
  make **`fold_recent_performance` phase-aware** (count `timed` for mastery).
- **`qt/aqt/lsat_performance.py`:** pass the already-computed `chosen`; parse
  `:conf=<n>`; stamp `phase` from a session-mode flag.
- **Effort S.** Batch into one schema migration (one full sync).

### Stage 1 — ZPD Daily Engine (parallel with Stage 0; doesn't need the keystone)
- **New `lsat/selection.py`** re-ranking the `PointsAtStakeEntry` list by
  `points · zpd(P̂)`; reads `lsat/models/performance.py`.
- **`eval/ablation.py`:** `+zpd` arm. Dashboard: silent. **Effort S→M.**

### Stage 2 — Calibration + Hypercorrection (cheapest real feature; consumes `confidence`)
- **New `lsat/models/calibration.py`** (reuses `eval/metrics.py`); bounded boost in
  **`lsat/events.py::topic_weights_for_queue`**; panel in `lsat/dashboard_data.py` →
  `ts/routes/lsat-dashboard/`.
- **`eval/`:** calibration-recovery + hypercorrection-γ arm. **Effort S–M.**

### Stage 3 — Distractor-Reasoning Engine (the flagship differentiator; consumes `chosen`)
- **New `lsat/error_patterns.py`** (fold by chosen→trap); AI
  `card_type:"distractor_rejection"` in **`lsat/ai/{prompts,generator}.py`** gated by
  **`lsat/ai/checker.py`**; trap-select tap in `_ITEM_QFMT` → `qt/aqt/lsat_performance.py`;
  trap-granular weighting in `topic_weights_for_queue`; per-trap bars in the dashboard.
- **`eval/`:** unseen-same-trap arm + the **A/B (no-tap / tap / tap+free-text)**;
  reuse `card_check` gates. **Effort M.**

### Stage 4 — Blind-Review "Gap Map" + Choke/Pacing MVP (heavy flagship; consumes `phase`)
- **New `lsat/blind_review.py`** (join phases per `item_id`, 2×2, honest-mastery
  filter); session-mode toggle in `qt/aqt/lsat_performance.py`; 2×2 + gap panel in
  `ts/routes/lsat-dashboard/`; Choke Index + speededness + consented ramp (small
  `lsat/pacing.py` or folded in).
- **New `eval/blind_review.py`** (routing-validity + honest-mastery). **Effort L.**

### Stage 5 — Fluency Gates (+ Structure Sprints) (cheap add-on; rides existing latency)
- RT-aware mastery + Not-yet→Effortful→Automatic badge (reads `response_ms`); a
  seconds-long classification drill; dashboard badge.
- **`eval/`:** held-out **timed**-accuracy arm (parked if null). **Effort S–M.**

### Parallel track — Transfer Meter (honesty layer; must exist before any Twins funding)
- **New `eval/transfer.py`** (report-only; reuses `eval/leakage.py` + `bootstrap_ci`);
  `struct.*` namespace in `lsat/taxonomy.py` + `lsat-taxonomy.yaml`; dashboard badge.
- **Effort S–M.**

### Gated / deferred backlog (only when their gate clears)
1. **Structure Twins** — after the Meter proves valid twins + far-surface lift (§5.ii):
   `LSAT Structure Twin` notetype + `lsat/ai/` twin generator/checker + compare UI. **M.**
2. **BKT** — only if `lsat/models/knowledge_tracing.py` beats the recency fold on
   held-out AUC by `PERF_MIN_DELTA_AUC`. **M.**
3. **Faithful section simulator** — after a checker-gated ~25-item/section bank exists:
   `lsat/section_sim.py` + timed reviewer UI + `readiness.raw_to_scaled`. **L.**
4. **Successive Relearning** — `lsat/relearning.py` keyed on distinct HLC wall-days,
   the "pattern" = the trap schema; capped concurrent loops; reported at **d ≈ 0.28**. **M–L.**

---

### Appendix — evidence-rating legend

`STRONG` = meta-analytic / independently replicated · `MODERATE` = a few consistent
labs · `WEAK` = single study / wide CIs · `CONTESTED` = the literature actively
disagrees. Every planning number in this document is the **weakest necessary link /
time-matched** figure, not the headline — and every shipped effect is **synthetic until
a real A/B**, labeled as such per the `eval/ablation.py` honesty convention.
