# Round 2 — Engineer's Rebuttal & Refinement (Priya Nair)

_Lens unchanged: differentiation per unit of build cost, judged on feasibility, maintainability,
data-availability, and true novelty. Round 1 was my survey; Round 2 is the reality check. I've
re-read all four opening positions and re-grounded every call against the code
(`lsat/events.py`, `lsat/notetypes.py`, `qt/aqt/lsat_performance.py`, `lsat/models/readiness.py`,
`lsat/seed.py`, `eval/{metrics,calibration,ablation}.py`, `lsat/interleaving.py`,
`lsat/ai/generator.py`, `lsat-taxonomy.yaml`). Good news: we have converged on the keystone.
This memo locks the plumbing, prices the set, and hands the moderator the three budget calls that
remain._

---

## 1. Concessions & validations (where I agree — and it's most of the room)

**The shared primitive is real consensus. Everyone independently converged on it.** The scientist's
"one tiny append-only capture change unlocks four features" (CF3/CF5 as _enabling capture_), the
coach's C1 Trap Profile ("we're literally throwing away the single most diagnostic byte"), and the
advocate's whole low-friction bundle ("a one-tap confidence field + the chosen-letter capture
already flagged by every memo") are **the same object I called Primitive A**: capture
`chosen` + `confidence` + `phase` on the `LSAT PerformanceEvent` log. Four debaters, four lenses,
one keystone. I concede nothing here because there's nothing to fight — I'll just **build it right**
(§3), because "additive field" hides a schema-migration/full-sync caveat the memos glossed.

**The scientist's eval-metric-per-feature is cheap and I'll enforce it as a merge gate.** This is
not aspirational — the machinery already exists. `eval/metrics.py` ships `brier`, `log_loss`,
`reliability_bins`, `ece`, `auc`, `accuracy`, `bootstrap_ci`; `eval/calibration.py` shows the
pattern (a `run()` returning `{passed, gate, …}` against `config.ECE_MAX`); `eval/ablation.py` shows
the 3-arm, equal-`STUDY_EVENTS`, N-synthetic-learner, `bootstrap_ci` template with the honesty
convention that the effect is a _parameter_ (`INTERLEAVE_BONUS`) until a real A/B. **Ruling: every
feature below ships with one `eval/<feature>.py` arm (equal _time_, primary metric = held-out
exam-style items, CI excludes 0). Cost: ~½ day each. It's the cheapest honesty we can buy, and it's
non-negotiable.** I adopt the scientist's discipline wholesale.

**The advocate's friction ceiling is implementable, and I'm turning it into build constraints on the
primitive.** Their constraints (1–11) are not soft preferences; they are a spec. I commit to these
as hard requirements on Primitive A and everything that reads it:

- **One tap, never a form; sampled, skippable.** Confidence = a 3-way `sure/likely/guess` strip,
  posted once, defaulting to _unrated_ if skipped. Sampling rate is a config knob (§5, disagreement 3).
- **Select-not-type.** Any autopsy/attribution is a tap on the `skill.trap.*` / `flaw_catalog` menu;
  free text is optional bonus, never gates anything.
- **Only on misses / confident-wrong.** No added interaction on correct answers.
- **Confidence captured at the graded moment, before the correctness reveal** — which, happily,
  respects Rhodes & Castel (rate before you know) _and_ is the cleanest append-only design (§3).
- **No punitive framing; abstain on small n** — I already reuse the readiness give-up gate everywhere.

I also concede two specific Round-1 rankings outright (see §4): **ZPD selection moves into the core
set** (the advocate's #1, the coach's changed-mind pick, the scientist's champion — I had it merely
CONDITIONAL, and they're right that it's near-free and adherence-protective), and **Structure Twins
moves _out_ of the core** into a gated phase-2 (its content-validity risk is too big to headline).

---

## 2. Feasibility rulings (I'm the reality check)

Effort scale: **S** ≈ ≤1–2 days, **M** ≈ ~1 week, **L** ≈ multi-week. Layer tags map to my Round-1
cost table. "No Rust" means the queue's `(tag, weight, perf_mastery)` contract is untouched —
re-weighting and re-ranking are pure Python, because `topic_weights_for_queue` builds the triples
and the Rust RPC only consumes them:

```255:277:lsat/events.py
def topic_weights_for_queue(
    col: Collection,
    taxonomy: Taxonomy | None = None,
    *,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    now_ms: int | None = None,
) -> list[tuple[str, float, float]]:
```

### Consensus features — firm price

| Feature                                                   | Effort  | Layer                                                                                               | Data need                                                       | Rust/proto?              |
| --------------------------------------------------------- | ------- | --------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ------------------------ |
| **Keystone: per-answer annotation store**                 | **S**   | fields + Item template + `events.py` + qt hook                                                      | `chosen` already computed in the hook; `confidence`/`phase` new | **No** (schema-only; §3) |
| **ZPD selector**                                          | **S→M** | Python re-rank (`lsat/selection.py`)                                                                | works coarse on the ordinal today; sharper with `b_difficulty`  | **No**                   |
| **Calibration + Hypercorrection queue**                   | **S–M** | `lsat/models/calibration.py` (reuse `eval/metrics.py`) + bounded boost in `topic_weights_for_queue` | `confidence`                                                    | **No**                   |
| **Trap Profile / Leech + Trap Retrieval**                 | **M**   | `lsat/error_patterns.py` + AI `card_type` + web panel                                               | `chosen` + distractor→trap labels (AI)                          | **No**                   |
| **Blind Review + pressure/knowledge gap (+ Choke Index)** | **L**   | `phase` (keystone) + phase-aware fold + qt review-mode toggle + web 2×2 + eval                      | `phase` + `confidence`                                          | **No**                   |

The AI path is already primed for Trap Retrieval: the generator's `Card` dataclass **already carries
`card_type`** and plumbs it to the checker, so a `card_type:"distractor_rejection"` is an enum +
prompt path, not new infrastructure.

### Contested features — my rulings

- **CDM (DINA/G-DINA) and DKT stay CUT.** Unanimous across the room, and correct on the merits: a
  latent-attribute EM (or an RNN) on one user's _sparse, per-skill-short_ log is the textbook
  overfitting trap (Rupp & Templin Q-matrix fragility; Khajah 2016 shows bounded BKT already matches
  DKT). They also _duplicate_ the cheaper observed-data Leech fingerprint. **No further debate needed.**
- **BKT: DEFER, gated.** Cheap to code (M, pure Python, same triples → no Rust), but the coach is
  right that it _starves and abstains_ on sparse single-user data. **Ruling: do not build
  speculatively; it earns a slot only if it beats the existing recency fold on held-out next-answer
  AUC by `PERF_MIN_DELTA_AUC` in `eval/`.** Until then, `fold_recent_performance` stands.
- **ZPD selector = a Python re-rank of the _existing_ queue. Confirmed S→M, no Rust.** Concretely:
  a new `lsat/selection.py` wraps the returned `PointsAtStakeEntry` list and scores
  `value = points · zpd(P̂)` where `P̂` comes from `PerformanceModel.predict` and `zpd` peaks at a
  config `τ≈0.85`. **v1 re-ranks the entries the RPC already returns — zero Rust.** (An optional v2
  that pushes `τ` into `best_points` in `points_at_stake.rs` is the _only_ Rust any of this could
  ever want, and it's a pure optimization we don't need.) It ships **today** on the 3-level ordinal;
  `b_difficulty` (a second, deferrable schema field) only sharpens it.
- **Blind Review needs only the `phase` field + a review-mode toggle. Confirmed.** No new notetype,
  no proto. A blind pass is simply a **second `PerformanceEvent` for the same `item_id`** stamped
  `phase="blind"`; the log stays append-only + HLC-ordered, so `resolve_lww`/sync are untouched. The
  reviewer surgery is a _session-mode flag_ (timed / blind / relaxed) that the existing hook reads
  and stamps — the Item template doesn't even change for `phase`. The Choke Index (relaxed − timed
  accuracy) then falls out **for free** as a read-out of the same data. **One caveat I'm putting on
  the record (§3): the moment `phase` exists, `fold_recent_performance` must become phase-aware or it
  will double-count the timed + blind answer for one item.**

### The section simulator / pacing engine — the REAL estimate the coach asked for

The coach wants the Section Simulator as a headline champion; the advocate fears full timed mocks
as anxiety-by-construction. **Both are answerable once you separate _code_ cost from _data_ cost —
and the data cost is the whole story.**

- **Code alone is M.** A timed reviewer session mode already has its inputs: per-item latency is
  captured (`card.time_taken`), `raw_to_scaled` equating exists in `readiness.py`, and
  `lsat/interleaving.py` gives section ordering. A `lsat/section_sim.py` that assembles a section,
  imposes a 35-min clock, and computes speededness is **M** of pure Python.
- **But a _faithful_ section is L and DATA-BLOCKED, not code-blocked.** The taxonomy wants
  `scored_questions_estimate: 76` (**50 LR + 26 RC**, `scored_sections: ["LR","LR","RC"]`) — i.e.
  ~25 calibrated items _per section_. The seed bank ships **four** `LSAT Item`s:

```114:115:lsat/seed.py
# Original multiple-choice practice questions (LSAT Item).
SEED_ITEMS: list[dict] = [
```

You cannot simulate a 25-item section from a 4-item bank. Building the bank means driving the AI
pipeline to produce dozens of _content-valid, difficulty-calibrated, original_ items per type
(with the checker/`gold_set` false-pass gate) — and **that** is the L, and it inherits the same
content-validity risk as Structure Twins. A "simulator" degraded to short sets isn't a simulator;
its realism — its entire value per memo 04-F5 — evaporates, and the advocate is right that a
half-faithful mock is just anxiety without fidelity.

- **Minimum viable version (build this now): a pacing _trainer_, not a section _simulator_. S–M.**
  It rides the keystone `phase` field and the timing we already capture: take whatever due items
  exist, impose a per-item budget + a session clock, stamp `phase="timed"`, and surface
  **(a)** a speededness metric (unattempted vs missed) and **(b)** the **Choke Index** (relaxed −
  timed accuracy) — which the Blind Review feature _already_ produces. This gives the coach the
  score-relevant pacing diagnostic and the advocate the de-shaming "you're rushing, not stupid"
  message, **with no new item bank and no new UI beyond a timer.**

**Ruling: fund the pacing MVP (S–M, folded into Blind Review); DEFER the faithful section simulator
to L behind a real item bank.** Don't headline a simulator we can't stock.

---

## 3. The keystone build — per-answer annotation store (full spec)

This is what unblocks everything, so I'm specifying it to the field. Three additive fields, one
schema migration, one template change, three new `append_event` params. **No Rust. No proto.**

### 3a. What gets added, and exactly where

Today the log stores correctness/latency/clock only, and the reviewer hook **computes the chosen
letter and the correct letter, then calls `append_event` without them** — the single most diagnostic
byte is discarded on every answer:

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

**The changes, batched into ONE schema bump:**

1. **`lsat/notetypes.py` — append three fields** to `EVENT_FIELDS`: `chosen`, `confidence`, `phase`.
   New collections get them for free via `_build`. (Ordering: append at the end; the first field stays
   the sort field.)

2. **`lsat/events.py::append_event` — three new optional params**, written to the note:
   ```python
   def append_event(col, *, item_id, skill_tags, correct, response_ms,
                    chosen: str = "", confidence: int | None = None,
                    phase: str = "timed", now_ms=None) -> NoteId:
       ...
       note["chosen"] = (chosen or "").upper()
       note["confidence"] = "" if confidence is None else str(int(confidence))
       note["phase"] = phase
   ```

3. **`lsat/events.py::PerformanceEvent` + `read_events` — carry the fields, read defensively.** Add
   `chosen: str`, `confidence: int | None`, `phase: str` to the dataclass; in `read_events`, read via
   a `try/except KeyError` helper so events written _before_ the migration (which lack the field)
   parse as `""`/`None`/`"timed"` rather than raising:

```174:215:lsat/events.py
@dataclass(frozen=True)
class PerformanceEvent:
    note_id: int
    item_id: str
    node_ids: list[str]
    correct: bool
    response_ms: int
    hlc: str
    device_id: str
    # + chosen: str = "", confidence: int | None = None, phase: str = "timed"
```

4. **`qt/aqt/lsat_performance.py` — stop discarding `chosen`; stamp `phase` from session mode.**
   `chosen` is already in hand → just pass it. `phase` is stamped from a module-level session flag
   set by the timed/blind controller — **so `phase` needs no template change at all.** Parse an
   optional `:conf=<n>` suffix off the payload for confidence.

5. **`lsat/notetypes.py::_ITEM_QFMT` — the only template change: the confidence tap.** The button
   currently posts `pycmd("lsatAnswer:" + chosen, cb)`. Change it to a **two-phase, append-only**
   flow: click choice → (if sampled) show a `sure/likely/guess` strip → the tap posts
   `pycmd("lsatAnswer:<L>:conf=<n>")`, which grades + appends **once**; the correct/wrong highlight
   comes back in the callback (i.e. _after_ the confidence tap — the desired ordering). On
   non-sampled items it posts `lsatAnswer:<L>` exactly as today. **Template HTML auto-propagates via
   `_sync_templates` to already-seeded collections** — this half is safe.

**Net: only `confidence` touches the template; `chosen` and `phase` are pure Python-side.**

### 3b. How we avoid a Rust/proto change

Everything above is Python + notetype fields + template HTML. Nothing crosses the protobuf boundary,
because the annotation store is _read_ by Python models (`calibration.py`, `error_patterns.py`,
phase-aware fold) that feed the **existing** `(tag, weight, perf_mastery)` triples. The Rust queue
never learns these fields exist. This is the whole reason the primitive is cheap.

### 3c. The schema-migration / sync caveat (on the record, because the memos skipped it)

`ensure_notetypes` **deliberately does not migrate fields** on an already-seeded notetype — it only
refreshes template HTML:

```200:217:lsat/notetypes.py
def ensure_notetypes(col: Collection) -> dict[str, int]:
    """Create any missing LSAT notetypes; return ``{name: notetype_id}``.

    Idempotent. A missing notetype is created; an existing one is left
    structurally untouched (adding/removing a field or template is a schema
    change), but its template HTML is refreshed to match the code.
    """
```

So appending to `EVENT_FIELDS` only helps _new_ collections. Retrofitting an existing user needs a
real migration — a new `migrate_event_fields(col)` that adds only the missing fields via the same
API `_build` already uses (`col.models.add_field(nt, col.models.new_field(name))` +
`update_dict`). **Adding a field is a schema change, which forces one full (one-directional) sync.**
That is cheap but non-zero and user-visible, so:

- **Batch `chosen` + `confidence` + `phase` into a single migration** → pay the full-sync cost
  **exactly once**. If we ever commit to the psychometric family, fold `b_difficulty` (ZPD's second
  field) into the _same_ window so we never force a second full sync.
- **Old events lack the new fields → readers must treat missing/empty as "unknown".** Hence the
  defensive `read_events` above; calibration/leech must **abstain** on events with no `confidence`,
  not impute one.
- **`phase` changes fold semantics.** Once a Blind Review writes a second event per item,
  `fold_recent_performance` (which today counts every event once) will **double-count** the timed +
  blind answer. The migration ships **with** a phase-aware fold (default: count `phase="timed"` for
  mastery; use `blind`/`relaxed` only for the Choke Index and the honest-mastery filter). This is the
  one behavioral change reviewers must sign off on.

**Effort: S. Unlocks: ZPD's confidence-free cousin aside, all four downstream features.**

---

## 4. Revised final set + build order (staged cheap → heavy)

Four features + the keystone, each sharing the primitive, each with an eval arm. **What changed from
my Round 1 is marked.**

| #         | Feature                                                            | Effort  | Layer                               | Novelty                       | Δ from R1                                  |
| --------- | ------------------------------------------------------------------ | ------- | ----------------------------------- | ----------------------------- | ------------------------------------------ |
| **0**     | **Per-answer annotation store** (`chosen`+`confidence`+`phase`)    | **S**   | fields+template+py+qt               | infra (keystone)              | unchanged — now spec'd to the field (§3)   |
| **1**     | **ZPD selector**                                                   | **S→M** | Python re-rank                      | 3 (fixes a real queue defect) | **PROMOTED** from conditional → core       |
| **2**     | **Calibration + Hypercorrection queue**                            | **S–M** | py + queue boost                    | 4                             | unchanged (still cheapest real win)        |
| **3**     | **Trap Profile / Leech + Trap Retrieval**                          | **M**   | py + AI + web                       | 5                             | unchanged (flagship differentiator)        |
| **4**     | **Blind Review + pressure/knowledge gap + Choke Index/pacing MVP** | **L**   | phase-fold + qt toggle + web + eval | 5                             | **ABSORBED** the pacing MVP (was separate) |
| _(cond.)_ | **Transfer Meter** (report-only honesty layer)                     | **S–M** | eval + web                          | 4                             | kept conditional; **Twins split off**      |

**Build order and the reasoning:**

1. **Keystone (0).** Cheapest, partly pre-wired, one schema bump; unblocks 2–4. First, always.
2. **ZPD selector (1).** _Now first among the features_ — it doesn't even need the keystone (it reads
   the performance model + item difficulty), it's a pure Python re-rank, it fixes the documented
   "hardest-card-in-weakest-topic" defect, and all three other debaters rank it top for
   adherence/evidence. Ship it in parallel with the keystone migration.
3. **Calibration + Hypercorrection (2).** Smallest feature that consumes the new `confidence` field;
   `calibration.py` reuses `eval/metrics.py` verbatim and the hypercorrection boost is a bounded tweak
   in `topic_weights_for_queue`. Delivers a visible dashboard win and validates the confidence tap.
4. **Trap Profile / Leech + Trap Retrieval (3).** The headline differentiator on `chosen`; extends the
   AI pipeline (`card_type:"distractor_rejection"`) and adds trap-granular queue weighting.
5. **Blind Review (4).** The heavy flagship for `phase`; reuses the confidence tap already shipped in
   steps 0–2, so its marginal cost is the session-mode toggle + phase-aware fold + 2×2 dashboard. The
   **pacing MVP (Choke Index + speededness) folds in here for free**, satisfying the coach's pacing
   priority without the data-blocked simulator.
6. **Parallel, conditional: Transfer Meter** (report-only, reuses `eval/leakage.py` cosine +
   `bootstrap_ci`). The honesty layer that must exist _before_ anyone funds Twins.

**Net changes from Round 1:** ZPD in, Twins out (to phase-2 gate), pacing MVP absorbed into Blind
Review, BKT explicitly gated-not-built, section simulator explicitly deferred as data-blocked. The
set is tighter (4 core, sharing one primitive) and every item is now priced with its layer.

---

## 5. Remaining disagreements for the moderator (scope / budget calls)

1. **Structure Twins: fund or defer?** The scientist wants it (best transfer _evidence_); I keep it
   **out of the core** because its cost is content validity, not code — the AI must mint two arguments
   surface-different yet structurally identical, gated by a checker whose own false-pass rate is a
   research task, on a **new notetype + compare UI (real M)**. My position: ship the **Transfer Meter
   first**, fund Twins only once the meter proves the AI can mint valid twins. _Moderator call: is
   the transfer camp's evidence worth an M build on the set's biggest unmitigated risk?_

2. **Faithful Section Simulator: fund the item bank, or ship only the pacing MVP?** Code is M; the
   blocker is a ~25-item-per-section calibrated bank vs. the **4** items we have. Building it is an L
   AI-content project inheriting the twin content-validity risk. _Moderator call: pay for the bank
   (unlocks a true mock) or accept the S–M pacing trainer as sufficient for v1?_ My vote: pacing MVP
   now, simulator when the bank exists.

3. **Confidence-tap sampling rate.** The advocate wants ≤1 tap, sampled every Nth, skippable; the
   scientist needs enough rated items to compute a stable calibration curve / hypercorrection signal.
   These trade off directly against how fast features 2/4 get their `n`. _Moderator call: set the
   default sample rate (e.g. every item on misses + every Nth on hits) — it's a config knob, but
   someone has to pick the default and the abstain-floor._

4. **BKT: build or gate?** I rule _gate_ (must beat the recency fold on held-out AUC before it earns a
   slot). The scientist agrees in principle; if anyone wants it built speculatively, that's a budget
   call to overrule me.

5. **Is Transfer Meter in the v1 four, or a fifth?** It's cheap (S–M) and it's the honesty layer, but
   it only earns its keep if a transfer feature (Twins) is on the roadmap. _Moderator call: 4 features
   or 5?_

---

## Summary (for the record)

- **Revised buildable set (4 core + keystone, sharing one primitive, cheap→heavy):** (0) per-answer
  **annotation store** → (1) **ZPD selector** (Python re-rank, promoted into core) → (2) **Calibration
  - Hypercorrection queue** → (3) **Trap Profile/Leech + Trap Retrieval** → (4) **Blind Review +
    Choke Index/pacing MVP**; with **Transfer Meter** as the cheap conditional honesty layer.
- **Keystone fields, exactly:** add **`chosen`**, **`confidence`**, **`phase`** to `EVENT_FIELDS`
  (`lsat/notetypes.py`), thread three new params through `append_event` + `PerformanceEvent`/`read_events`
  (`lsat/events.py`), pass the already-computed `chosen` (and parse `:conf=<n>`, stamp `phase` from
  session mode) in the qt hook (`qt/aqt/lsat_performance.py`). Only `confidence` touches the Item
  template; `chosen`/`phase` are pure Python-side.
- **No Rust, no proto** anywhere in the set — re-weighting/re-ranking ride the existing
  `(tag, weight, perf_mastery)` triples.
- **Schema/sync caveat:** adding fields bypasses `ensure_notetypes` and needs a real
  `migrate_event_fields` (a schema change → one full sync), so **batch all annotation fields into a
  single migration**, read old events defensively, and ship a **phase-aware fold** so Blind Review's
  second event doesn't double-count mastery.
- **Firmest feasibility ruling:** the **Section Simulator is data-blocked, not code-blocked** —
  taxonomy wants ~25 items/section, `seed.py` has **4** — so ship the **S–M pacing MVP** (rides the
  keystone `phase` + existing timing) now and **defer the faithful L simulator** behind a real,
  checker-gated item bank. Confirmed CUTs: **CDM/DKT** (overfit sparse single-user). Confirmed cheap:
  **ZPD = pure Python re-rank, no Rust; Blind Review = `phase` field + a review-mode toggle.**
