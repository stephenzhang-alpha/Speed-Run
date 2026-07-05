# Round 1 — Engineer's Opening Position (Priya Nair)

_Lens: pragmatic product/systems engineer. I rank features by **differentiation per
unit of build cost**, judged on feasibility, maintainability, data-availability, and
**true novelty** vs plain Anki. I reward features that reuse existing hooks (the Item
`pycmd`, the append-only event log, the AI generate→check pipeline, the points-at-stake
queue, the Rasch model, the eval harness) and I am ruthless about killing
over-engineering, duplication, and anything that demands a Rust/proto rebuild when
Python suffices._

I read the brief, all four memos (01–04), and proposals B and C, then grounded every
feasibility call against the actual code: `lsat/events.py`, `lsat/notetypes.py`,
`qt/aqt/lsat_performance.py`, `lsat/models/{performance,readiness}.py`,
`lsat/dashboard_data.py`, `lsat/interleaving.py`, `lsat/ai/{pipeline,generator,prompts}.py`,
`rslib/src/scheduler/points_at_stake.rs`, and `lsat-taxonomy.yaml`.

---

## 1. Priorities — my cost/novelty rubric

I score each candidate on five axes and rank by **(evidence × novelty) / build-cost**:

1. **Reuse of existing hooks (cost down).** The cheapest features ride machinery we
   already have: the Item template's server-side grading via `pycmd("lsatAnswer:…")`,
   the append-only HLC event log, the `(tag, weight, perf_mastery)` triples that feed
   the Rust queue, the generate→check→gate AI pipeline with its verbatim-span defense,
   the `eval/` ablation harness. Anything that reuses these is S/M; anything that needs
   a new notetype + new UI + new AI path is M/L; anything needing **proto + Rust** is a
   red flag.
2. **True novelty (value up).** Not spacing, not interleaving, not basic IRT — we ship
   those. I score 5 = a construct with no Anki/competitor analog (e.g. distractor-error
   mining, timed↔untimed counterfactual, cross-surface schema transfer); 1 = reskinned
   spacing.
3. **Data-availability.** Does the feature run on data we **capture today**
   (correctness, latency, tags) or does it need new capture? New capture is fine **once**
   if it's shared; new capture per-feature is waste.
4. **Maintainability / anti-overfitting.** A single desktop user produces **sparse,
   per-skill-short** sequences. Low-parameter, bounded, abstain-when-thin models only.
   Deep/latent models that overfit one user's log are disqualified on principle.
5. **Evidence honesty.** Contested evidence (feedback timing, expressive writing, the
   85% figure, variability drilling) → ship as a **measured knob with an eval arm**,
   never as a headline.

**Which layer each kind of feature touches** (this drives cost):

| Layer                                          | What lives here                                                | Cost signal                                                            |
| ---------------------------------------------- | -------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **Notetype _fields_** (`lsat/notetypes.py`)    | event schema, per-item difficulty                              | **schema change → one full sync**; batch these                         |
| **Notetype _templates_** (`_ITEM_QFMT`)        | answer capture UI, confidence tap                              | cheap — `_sync_templates` auto-propagates HTML to existing collections |
| **Python lib** (`lsat/…`, models, folds)       | calibration, error-mining, relearning, selection, blind-review | cheap iteration; **most features belong here**                         |
| **Qt reviewer** (`qt/aqt/lsat_performance.py`) | pycmd routing, timed/blind session flow                        | moderate                                                               |
| **Web** (`ts/routes/lsat-dashboard`)           | dashboard panels                                               | moderate                                                               |
| **Rust core** (`rslib/`)                       | the queue only                                                 | **avoid** — re-weighting/re-ranking is Python                          |
| **proto/**                                     | new RPC                                                        | **avoid** — nothing I champion needs it                                |
| **eval/**                                      | ablation arms, gates                                           | required per feature, cheap                                            |

Key consequence: **the queue is Python-steerable.** `topic_weights_for_queue` builds the
triples and the Rust RPC just consumes them, so hypercorrection boosts, trap-granular
priority, prereq gates, and ZPD re-ranks are all **Python, no Rust change**:

```255:277:lsat/events.py
def topic_weights_for_queue(
    col: Collection,
    taxonomy: Taxonomy | None = None,
    *,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    now_ms: int | None = None,
) -> list[tuple[str, float, float]]:
```

```54:59:rslib/src/scheduler/points_at_stake.rs
pub(crate) fn points_at_stake_queue(
    &mut self,
    deck_id: DeckId,
    limit: usize,
    topics: &[(String, f32, f32)],
) -> Result<Vec<PointsAtStakeEntry>> {
```

---

## 2. Enabling primitives — build the shared plumbing once

Reading across all six proposal documents, **the same small piece of plumbing appears in
most of the high-value features**: capture _what the learner did_ on each answer, not just
_whether they were right_. I call this **Primitive A**, and it is the thing to build
first because it unlocks the most features for the least code — and because part of it is
**already computed and thrown away today.**

### Primitive A — the per-answer annotation store (`chosen` + `confidence` + `phase`)

Today the event log stores only correctness, latency, tags, and clock:

```50:57:lsat/notetypes.py
EVENT_FIELDS = [
    "item_id",
    "skill_tags",
    "correct",
    "response_ms",
    "answered_at_hlc",
    "device_id",
]
```

But the reviewer hook **already knows the chosen letter and the correct letter**, and then
calls `append_event` **without** them — the distractor the learner actually picked is
discarded on every single answer:

```60:79:qt/aqt/lsat_performance.py
chosen = message[len(ANSWER_PREFIX) :].strip().upper()
correct_letter = (note["correct"] or "").strip().upper()
is_correct = bool(chosen) and chosen == correct_letter
...
    append_event(
        context.mw.col,
        item_id=str(note.id),
        skill_tags=node_ids,
        correct=is_correct,
        response_ms=response_ms,
    )
```

**Three additive fields on `LSAT PerformanceEvent` + three args on `append_event`** give us:

- **`chosen`** (the selected letter) — needed by **Trap Retrieval** [01-F1], **Reasoning-Bug
  / Leech diagnosis** [03-F3], and the honest-mastery filter in **Blind Review** [B-F1].
  _Near-free: it's already in the hook._
- **`confidence`** (one tap: sure/likely/guess → probability) — needed by **Human
  Calibration** [03-F1/B-F2], **Hypercorrection queue** [03-F2/B-F2], the **SRL loop**
  [03-F6], and blind-review flagging.
- **`phase`** (`timed` / `blind` / `relaxed`) — needed by **Blind Review** [B-F1], the
  **Choke Index** [03-F5], and the **Section Simulator** [04-F5]. A blind pass is simply a
  _second event_ for the same `item_id`; the log stays append-only + HLC-ordered, so sync
  and `resolve_lww` are untouched.

**Feasibility nuance the memos gloss over (I want this on the record):** adding fields is a
_schema_ change, and `ensure_notetypes` deliberately **does not** migrate the fields of an
already-seeded notetype — it only refreshes template HTML:

```200:217:lsat/notetypes.py
def ensure_notetypes(col: Collection) -> dict[str, int]:
    """Create any missing LSAT notetypes; return ``{name: notetype_id}``.

    Idempotent. A missing notetype is created; an existing one is left
    structurally untouched (adding/removing a field or template is a schema
    change), but its template HTML is refreshed to match the code.
    """
```

So merely appending to `EVENT_FIELDS` only helps _new_ collections. Retrofitting an
existing collection needs a real `mm.add_field` migration, which **forces one full sync**.
That is cheap but non-zero — therefore **batch all annotation fields (chosen, confidence,
phase) into a single schema bump** so we pay the full-sync cost exactly once, not three
times. The _template_ half (the confidence tap in `_ITEM_QFMT`, a `lsatAnswer:<L>:conf=<n>`
payload) is the safe half — it auto-propagates via `_sync_templates`.

**Effort: S. Unlocks: Clusters 2, 3, 4 below (7+ proposed features).**

### Primitive B — continuous per-item difficulty (`b_difficulty` on `LSAT Item`)

`LSAT Item` carries only a 3-level ordinal `difficulty`; the performance model maps
easy/medium/hard → +1/0/−1 (`_difficulty_ord`). A scalar `b` is the enabling change for
**ZPD selection** [04-F1] and the **mini-CAT probe** [04-F4]. It is a _second_ schema bump.
Smaller constituency than A, so **defer it** — and if we commit to the psychometric family,
fold it into the _same_ migration window as A to avoid a second full sync.

### Primitive C — the `struct.*` schema-id tag namespace

The transfer family [02/C] needs argument-structure tags (`struct.causal_overgeneralization`,
`struct.necessary_sufficient_swap`, …) that group items **across surface topics**. This is
**not** a schema change — it's just more node ids riding Anki's tag/sync system, exactly like
`flaw_catalog`. Cheap, but it only unlocks Cluster 5. Add it when we fund transfer.

> **Sequencing insight:** A is the keystone. It's the cheapest, it's partly already wired,
> and it is the shared substrate for the three strongest non-transfer clusters. Build A
> first; C in parallel if transfer is funded; B only if the psychometric selection family
> survives the debate.

---

## 3. Consolidated candidate list (merged across memos, deduped, cited)

I merged obvious duplicates first (the memos flag many themselves):

- **02-F1 ≡ C-"Structure Twins"** → one feature (**Twins**).
- **02-F5 ≡ C-"Transfer Meter"** → one feature (**Transfer Meter**).
- **02-F3 ≡ B-F3** ("self-explanation / trap autopsy") → one feature (**Autopsy**).
- **03-F1 + 03-F2 ≡ B-F2** (calibration + hypercorrection) → one feature (**Calibration+HC**).
- **03-F4 ⊂ 04-F1** (DP micro-loop is ZPD selection + a stop-rule) → folded into **ZPD**.
- **03-F5 (choke) ⊂ B-F1** (the timed↔untimed gap _is_ the choke read-out) → folded into **Blind Review**; **04-F5** is the heavier timed harness that _feeds_ it.

Novelty = 1 (reskinned spacing) … 5 (no Anki/competitor analog). Data column: ✅ have today ·
🅰/🅱/🅲 needs Primitive A/B/C · 🤖 needs AI-generated content.

| #  | Feature (sources)                                                     | Effort                          | Layers                            | Data: need vs have                   | Nov.                         |
| -- | --------------------------------------------------------------------- | ------------------------------- | --------------------------------- | ------------------------------------ | ---------------------------- |
| 0  | **Per-answer annotation store** (A) [01,03,B]                         | **S**                           | fields+template+py+qt             | 🅰 (chosen already computed)          | infra                        |
| 1  | **Trap Retrieval + Leech diagnosis** [01-F1 + 03-F3]                  | **M**                           | py + ai + web                     | 🅰 chosen + 🤖 distractor→trap labels | **5**                        |
| 2  | **Human Calibration + Hypercorrection queue** [03-F1/F2, B-F2]        | **S–M**                         | py (reuse `eval/metrics`) + web   | 🅰 confidence                         | **4**                        |
| 3  | **Blind-Review loop + pressure/knowledge gap (+choke)** [B-F1, 03-F5] | **L**                           | fields+py+qt+web+eval             | 🅰 phase+confidence                   | **5**                        |
| 4  | **Structure Twins** [02-F1/C]                                         | **M** (content-validity risk ↑) | notetype+ai+web                   | 🅲 + 🤖 valid isomorphs               | **5**                        |
| 5  | **Transfer Meter** [02-F5/C]                                          | **S–M**                         | eval + web (reuse leakage cosine) | 🅲 + ✅                               | **4**                        |
| 6  | **ZPD item selector** (+DP micro-loop) [04-F1, 03-F4]                 | **S–M**                         | py re-rank                        | 🅱 (coarse w/o it) + ✅               | 3                            |
| 7  | **Pattern Mastery Loops** (successive relearning) [01-F3]             | **M–L**                         | py + queue + 🤖 fresh items       | ✅ + 🤖                              | 4                            |
| 8  | **Prime-then-Read prequestions** [01-F4]                              | **M**                           | ai + qt flow                      | 🤖 + ✅                              | 4                            |
| 9  | **SRL predict→reconcile loop** [03-F6]                                | **S–M**                         | py + qt/web                       | 🅰 confidence                         | 3                            |
| 10 | **Section Simulator + pacing policy** [04-F5]                         | **M–L**                         | py + qt timed UI                  | 🅰 phase + ✅ (needs item bank)       | 3                            |
| 11 | **Delayed elaborated feedback** [01-F2]                               | **M**                           | py scheduler + qt                 | ✅                                   | 3 (contested)                |
| 12 | **Commit-First drills** (productive failure) [01-F5]                  | **M**                           | qt two-phase + ai                 | 🅰 + 🤖                               | 3                            |
| 13 | **Bayesian Knowledge Tracing** [04-F2]                                | **M**                           | py model                          | ✅                                   | 2 (improvement, not novelty) |
| 14 | **Adaptive measurement probe (mini-CAT)** [04-F4]                     | **M**                           | py selector                       | 🅱 + ✅                               | 3                            |
| 15 | **Faded Parallels** (worked-example fading) [02-F2]                   | **M–L**                         | notetype+ai+adaptive              | 🤖 step decompositions               | 3                            |
| 16 | **Skeleton Builder** (argument mapping) [02-F4]                       | **M–L**                         | span-select UI + ai               | 🅲 + 🤖                               | 3 (MODERATE evid.)           |
| 17 | **Spot-the-Structure Sort** [C-Sort]                                  | **M** (S for v0)                | drag-drop UI + py                 | 🅲 + ✅                               | 4                            |
| 18 | **Mastery-gated advanced types** [04-F6]                              | **S–M**                         | py queue multiplier               | depends on #13/#19                   | 2                            |
| 19 | **CDM attribute profile (DINA/G-DINA)** [04-F3]                       | **M–L**                         | py EM + Q-matrix                  | ✅ but **data-hungry**               | 2                            |
| —  | **Deep Knowledge Tracing** (named to reject)                          | —                               | —                                 | overfits sparse user                 | 1                            |

---

## 4. Ranked verdict — CHAMPION / CONDITIONAL / CUT

### CHAMPION (max differentiation per build cost; share Primitive A)

- **#0 Per-answer annotation store.** Not glamorous, but it's the keystone and `chosen`
  is _already sitting in the hook_. Build first. **S.**
- **#1 Trap Retrieval + Leech diagnosis.** The most LSAT-shaped feature we can build and
  the strongest on-target evidence: competitive-MC distractor retrieval (Little et al.
  2012; Bjork/Little/Storm 2014 — MC practice g≈0.70, no net RIF) + self-explanation
  (Bisra 2018, g=0.55). Reuses the AI pipeline (add a `card_type:"distractor_rejection"` —
  the generator already carries a `card_type` field and enumerates types in `prompts.py`)
  and the `skill.trap.*` taxonomy. The _diagnosis_ ("you pick extreme-language on 38% of
  Strengthen misses") and the _drill_ (spaced why-is-(C)-wrong cards) are one feature on
  one substrate (`chosen` + trap labels). **M. Nov 5. Biggest differentiated payoff.**
- **#2 Human Calibration + Hypercorrection queue.** Cheapest real win. `eval/metrics.py`
  already ships `ece/brier/auc/reliability_bins/bootstrap_ci`; a new `calibration.py`
  reads the `confidence` field and the hypercorrection boost is a **bounded Python tweak
  in `topic_weights_for_queue`** (no Rust). Orthogonal new axis (student calibration vs
  the model calibration we already compute). Strong theory (Kruger–Dunning _description_;
  Metcalfe hypercorrection). **S–M. Nov 4.**
- **#3 Blind-Review loop + pressure/knowledge gap.** The signature high-scorer technique
  (7Sage), made quantitative. It's the only thing that separates _"slow/cracked under
  pressure"_ from _"doesn't know"_, and it makes the queue **honest** by letting
  `fold_recent_performance` drop fragile/lucky timed wins. Natural home for `phase`; the
  choke index [03-F5] is a free read-out of the same data. Bigger build (data + two-pass
  reviewer + honest-mastery filter + 2×2 dashboard + eval arm) but flagship-level
  differentiation. **L. Nov 5.**

### CONDITIONAL (fund if budget/dependencies allow; each has a real gate)

- **#5 Transfer Meter** — _do this before #4._ Cheap (eval-only + a dashboard badge,
  reusing the `eval/leakage.py` tf-idf cosine and `bootstrap_ci`), and it's the honesty
  layer that keeps the whole transfer family from fooling us. Ship report-only first.
  **Condition:** enough same-`struct` items across surfaces (give-up gate).
- **#4 Structure Twins** — best-evidenced _transfer_ intervention (Gick & Holyoak;
  Gentner ~3×, 47% vs 6%) and squarely on the post-2024 structural-matching task. **But**
  its real cost is content validity: the AI must manufacture two arguments that are
  surface-different yet structurally identical, gated only by a checker whose own
  false-pass rate is itself a research task. **Condition:** the checker + `gold_set` clear
  a twin-validity false-pass bar before it ships. New notetype + compare UI = genuine M.
- **#6 ZPD selector (+ DP micro-loop)** — fixes a _real defect_: the queue ignores item
  difficulty and tends to serve the hardest card in the weakest topic (opposite of the
  region of proximal learning; Metcalfe & Kornell). Python re-rank of the returned
  entries. **Condition:** ships coarse on the ordinal today; only worth polishing once
  Primitive B (`b_difficulty`) exists. Folds in 03-F4 — **do not build two
  difficulty-targeting engines.**
- **#7 Pattern Mastery Loops** — durable-learning heavyweight (successive relearning
  ~80%@1wk vs ~20%). Genuinely new above FSRS. **Condition:** honest about the _time_ cost
  (time-matched d≈0.28) and dependent on AI fresh-item supply; cap concurrent loops.
- **#8 Prequestions / #9 SRL / #10 Section Sim / #11 Delayed feedback / #14 mini-CAT /
  #13 BKT** — all defensible, all _later_. Notes: **#13 BKT** must **empirically beat the
  existing recency fold on held-out next-answer AUC** before it earns a place — don't build
  it speculatively. **#11** ships as a _measured toggle_ (evidence contested). **#10** is
  gated on having an item bank large enough for a faithful section (else its realism
  evaporates).

### CUT / defer (over-engineered, duplicative, or wrong-layer for Round 1)

- **#19 CDM attribute profile (DINA/G-DINA) — my single strongest cut.** Fitting a
  latent-attribute EM with a Q-matrix on **one user's sparse, per-skill-short** log is the
  textbook overfitting trap; classification is Q-matrix-sensitive (Rupp & Templin) and the
  memo _itself_ concedes "MODERATE on single-user fit / abstain when thin." It also
  **duplicates cheaper signals we're already building**: the Leech fingerprint (#1) tells
  you _what_ you get wrong from _observed_ data, and BKT/the perf model estimate per-skill
  mastery. CDM adds heavy machinery to infer "latent holes" we cannot validate for a single
  user. **Cut** (at most a report-only research toy, never gating anything).
- **Deep Knowledge Tracing** — reaffirm the memo's own self-cut: an RNN overfits sparse
  single-user sequences and extended BKT is statistically indistinguishable (Khajah 2016).
  **Do not build.**
- **#15 Faded Parallels** — worked-example fading is real, but it needs authored step
  decompositions, a new `fade_level` notetype, adaptive fade logic _and_ expertise-reversal
  handling, on MODERATE evidence for the fading specifics, for the _rarest_ LR types
  (~4–6%). High build, narrow payoff — **defer.** Twins already trains the same structure
  more cheaply.
- **#16 Skeleton Builder** — the biggest UI in the set (span selection) on the weakest
  (advocate-led, quasi-experimental) evidence; the memo ranks it last and gates it on the
  Transfer Meter. **Defer** (if wanted, ship only the S "select-the-conclusion" sliver).
- **#17 Spot-the-Structure Sort** — striking, but a bespoke drag-drop grid + ARI index for
  a construct whose validity is itself unproven. The **Transfer Meter (#5) gives the same
  "are you structural?" read-out from already-logged answers with no new UI.** **Defer.**
- **#18 Mastery-gating** — depends on mastery signals (#13/#19) we don't yet trust for one
  user, risks starving the coverage the readiness model needs, and largely duplicates what
  the weakness-ordered queue already does. **Defer** behind a proven mastery signal.
- **#12 Commit-First drills** — productive-failure evidence is heterogeneous with sharp
  boundary conditions (no help for procedural; needs strong feedback), and it's real
  reviewer surgery (two-phase reveal). The "predict-before-tell" step already lives inside
  Twins. **Defer.**

**Anti-duplication rule (applies to everything):** the points-at-stake queue already
exists. Any feature that "reprioritizes study" is a **Python weight/re-rank tweak**
(hypercorrection boost, trap granularity, ZPD, prereq gate) — nobody gets to build a second
queue, and nobody touches Rust to do it.

---

## 5. My straw-man final set (differentiation per build cost, shared plumbing)

Four features + the keystone, sharing **one** primitive, staged so each ships value before
the next:

0. **Per-answer annotation store** (Primitive A: `chosen`+`confidence`+`phase`) — **S**, one
   schema bump. _The keystone._
1. **Human Calibration + Hypercorrection queue** — **S–M**. Cheapest real feature; validates
   the `confidence` tap and reuses `eval/metrics.py`; queue tweak is Python-only.
2. **Trap Retrieval + Leech diagnosis** — **M**. The flagship differentiator on `chosen`;
   strongest on-target evidence; reuses the AI pipeline + trap taxonomy.
3. **Blind-Review loop + pressure/knowledge gap (+choke index)** — **L**. The signature
   LSAT technique; the payoff feature for `phase`; makes queue mastery honest.
4. **Transfer Meter → Structure Twins** — **S–M then M**, on Primitive C. The strongest
   _true-novelty_ transfer play; ship the Meter (honesty layer) first, then Twins **only
   once the twin-validity checker clears its gate.**

**Rough build order (and why):**

1. **Primitive A** — unblocks everything; `chosen` is nearly free.
2. **Calibration + Hypercorrection** — smallest surface, proves the confidence tap, delivers
   a visible dashboard win immediately.
3. **Trap Retrieval + Leech** — the headline differentiator; AI-pipeline extension +
   trap-granular queue weighting.
4. **Blind Review** — the heavy flagship; reuses `phase` + the confidence tap already
   shipped in steps 1–2, so its marginal cost is the reviewer flow + honest-mastery filter.
5. **Parallel track (Primitive C):** Transfer Meter (report-only) → Structure Twins (gated).
6. **Then, only if proven/needed:** ZPD selector (after Primitive B), BKT (only if it beats
   the recency fold on held-out AUC), Section Sim, prequestions.

Every step ships with an `eval/` ablation arm (equal-**time**, `bootstrap_ci`), mirroring the
existing `INTERLEAVE_BONUS` honesty convention — synthetic learners first, real A/B later.

---

## 6. Pre-emptive critiques of my fellow debaters

**To the Cognitive Scientist (evidence without feasibility).** You'll rank by effect size
and push successive relearning (d≈4.19), Twins (~3×), prequestions (d up to >2), faded
examples. Three corrections. (a) **Most of those effect sizes are _not_ time-matched** — your
own memo 01 notes successive relearning collapses to d≈0.28 when time-on-task is held equal,
and _time is the scarcest resource in LSAT prep_. Rank by evidence-per-build-**hour** and
per-study-**minute**, not raw g. (b) **Effect size ≠ shippability.** Twins and faded examples
live or die on the AI reliably manufacturing _content-valid_ structural isomorphs / step
decompositions — the single biggest unmitigated risk in the whole set, gated only by a
checker whose own false-pass rate is a research project. That's why I gate Twins and ship the
Transfer _Meter_ first. (c) You under-weight the free win: **`chosen` is already computed and
discarded**, so the highest-evidence MC-distractor-retrieval feature is _nearly free_ while
your darlings need new notetypes and UI. Bring me an equal-time eval arm or it doesn't ship.

**To the Coach (impact without buildability).** You'll want the score-movers now — blind
review, a full section simulator, a readiness ceiling — all at once. (a) **Impact is gated by
build cost and the data we actually have.** The Section Simulator + adaptive pacing policy is
an L timed-UI build resting on an item bank we may not have at faithful section length; degrade
it to "short sets" and you've killed the realism that was its entire value. So I fund the
_cheap diagnostic_ (pressure-vs-knowledge gap from `phase` data, which the Blind-Review loop
already produces) **before** the simulator. (b) **"More PrepTests / more volume" is the weak
lever** (Macnamara; the Khan result is quasi-experimental and self-selected) — I'll spend on
_targeted_ practice and diagnosis, not volume. (c) **Cap the promise.** The honest ceiling is
~4–7 points / single-digit percentiles, validated on **held-out exam-style** items (ITS gains
are 0.73 on local vs 0.13 on standardized tests) — every impact claim ships as a measured eval
arm, never a marketing number. The readiness honesty contract already enforces this; don't ask
me to break it.

**To the Student-Advocate (UX / friction / motivation).** You're right that a confidence tap
on _every_ item is fatigue, that a blind-review second pass + autopsy writing + commit-first
double session time, and that mastery-gating locks and forced multi-day relearning loops
demotivate. I've already designed to your budget: the primitive is **one tap, sampled every
Nth item, skippable**; blind review is scoped to **flagged/low-confidence/skipped only**; and I
**cut the hard mastery gate and cap concurrent relearning loops.** Two pushbacks, though. (a)
Don't let "frictionless" smuggle back _passive re-reading_ — re-reading explanations feels
great and is LOW-utility (Dunlosky); the substrate must stay **graded retrieval**, not more
prose. (b) Motivation is a _reason to build the diagnostics_, not skip them: calibration and the
pressure/knowledge split turn a demoralizing "I'm just bad" into "you _know_ this, you're
rushing" — that's the motivating message, and it's cheap. Give me your hard friction ceiling
(taps/session, max session-time delta) and I'll treat it as a build constraint on Primitive A.

---

### Summary (for the record)

- **Championed set:** (0) the per-answer **annotation store**; (1) **Trap Retrieval + Leech
  diagnosis**; (2) **Human Calibration + Hypercorrection queue**; (3) **Blind-Review loop +
  pressure/knowledge gap**; with **Transfer Meter → Structure Twins** as the conditional
  true-novelty transfer track.
- **Build the primitive first:** capture **`chosen` + `confidence` + `phase`** on the
  `LSAT PerformanceEvent` log in **one** schema bump — `chosen` is already computed in the
  reviewer hook and thrown away, so it's nearly free, and it unlocks 7+ downstream features
  across three memos with no Rust or proto change.
- **Single strongest cut:** the **Cognitive-Diagnostic Model (DINA/G-DINA) attribute
  profile** [04-F3] — a data-hungry latent-attribute EM that overfits one sparse user, is
  Q-matrix-fragile, and duplicates the cheaper, observed-data Leech fingerprint we're already
  building. (Deep Knowledge Tracing is cut on the same grounds.)
