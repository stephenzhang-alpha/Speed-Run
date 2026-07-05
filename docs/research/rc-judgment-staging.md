# Staging report — RC Judgment Module (DECISION-round3 rank 4)

**Status: deferred, not shipped this session. This is the honest "write a report
for what you skip" note the goal asks for.**

## What it is

The round-3 debate's rank-4 winner: authored Reading-Comprehension stimuli each
carrying (a) 5 main-point candidates with hidden `{correct | too_broad |
too_narrow | detail | distortion}` labels, and (b) an optional highlighted-clause
`{author | others | neither}` viewpoint-attribution map. The learner picks the
main point (and optionally taps the trap / the attribution); grading is
deterministic against the labels and fails closed. It would extend
`lsat/taxonomy.py` + `lsat-taxonomy.yaml` with additive RC trap families and mirror
the conditional/quantifier drill endpoints.

## Why it is NOT shipped this session

The value of this feature lives **entirely in the quality of the authored content
and its labels** — and the honesty discipline (and the debate ruling itself)
require that content to be **human-calibrated before any item is admitted**:

1. **Label correctness needs a human.** Whether a main-point candidate is truly
   "too broad" vs "distortion", or whether a highlighted clause voices the author
   vs a cited other, is a judgment call. An AI-authored label is exactly the kind
   of unverified content the project refuses to trust without a gold-set checker
   **and** a human spot-check. I can build the deterministic _grader_ (verifiable),
   but a grader keyed to un-calibrated labels would confidently teach whatever the
   labels say — the same "confident mis-teach" failure mode the conditional-parser
   review just caught. Shipping that would violate the discipline.

2. **The viewpoint sub-metric needs cue-ABSENT items.** To avoid teaching mere
   word-spotting ("the author argues…"), a substantial share of the attribution
   stimuli must infer voice from clause position/contrast with **no** attribution
   verb. Authoring a balanced, genuinely cue-absent set is a content-design task
   that itself needs human review before it can be trusted.

3. **It ships study-only until its own eval CI clears.** Per the ruling, the
   main-point arm is the sole pre-registered claim and the viewpoint component
   stays study-only until its held-out CI (on real-style items) excludes 0.
   Without calibrated held-out items there is nothing honest to measure yet.

## What would unblock it (concrete next steps)

- A human-authored (or human-reviewed) gold set: ≥30 main-point items with the 5
  labelled candidates, plus ≥20 viewpoint items of which a substantial share are
  cue-absent.
- `lsat/rc_judgment.py`: the deterministic grader (pick vs labels; optional
  trap-tap / attribution-tap), fail-closed on any unlabelled item — this part is
  buildable and unit-testable now; it is the _content_ that is the blocker.
- Additive `too_broad / too_narrow / detail_as_main` trap families in the taxonomy
  (no schema migration).
- `eval/mainpoint.py`: paired {drill, generic-RC-review, plain} arms at equal study
  events; PRIMARY = held-out main-point/primary-purpose accuracy, drill−generic
  bootstrap CI; viewpoint sub-metric gated on a cue-absent held-out CI.

## Decision

Deferred honestly rather than shipped with AI-authored, un-calibrated content. The
four other round-3 winners (quantifier, growth, rush, time-leak) _were_ shipped
because their correctness does not depend on authored content: their engines are
provable (the Venn model-checker) or their claims are self-referential/diagnostic
with CI gates. RC Judgment is the one winner whose integrity hinges on human
calibration, so it waits for that input.
