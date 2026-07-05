# ROUND 2 — Rebuttal & Refinement: The LSAT Coach

**Speaker:** Marcus Webb — veteran LSAT coach, score-obsessed pragmatist.
**Round-2 job:** _converge._ Concede what the others got right, hold the lines that
actually buy points, and re-cut my designs so they survive Sorensen's evidence bar,
Nair's build budget, and Okafor's adherence/anxiety floor.

> **Source shorthand** (as in Round 1): **M1** = `research/01-memory-retrieval.md` ·
> **M3** = `research/03-metacognition-srl.md` · **M4** = `research/04-adaptive-psychometrics-lsat.md` ·
> **B** = `research/proposals/B-metacognition-blind-review.md` ·
> **C** = `research/proposals/C-transfer-argument-schemas.md` ·
> **R2** = `docs/research/R2-error-trap-analysis.md`.
> Debaters: **Sorensen** (cognitive scientist), **Nair** (engineer), **Okafor** (student-advocate).

I read all four Round-1 openings in full. The good news for the moderator: we are
**closer than the rhetoric suggests.** Four independent lenses converged, unprompted, on
the _same substrate_ — capture the chosen distractor and one tap of confidence — and on
the _same daily difficulty target_ (~85%). The real fights left are narrow and fundable.

---

## 1. Concessions — where the others moved me

I came in Round 1 saying "if it doesn't move a timed 120–180 score, I don't care how
elegant it is." I still believe that. But three arguments landed, and one reframing
genuinely changed my build.

### 1a. Sorensen is right: score claims must be MEASURED on held-out items. (My biggest concession.)

My Round-1 tell was "I've watched Blind Review work too many times to rank it below a
lab-clean feature." That's a coach's gut, and a gut is not an eval. Sorensen's discipline
is correct and I adopt it wholesale: **every score claim we make must move a held-out,
_unseen_, exam-style metric at _equal study time_, with a bootstrap CI that excludes 0 —
never the drilled items.** Kulik & Fletcher's 0.73-on-local-vs-0.13-on-standardized gap
(M4) is the exact trap I was courting. And I concede the ceiling: the honest number is
**~4–7 scaled points / single-digit percentiles** (Dustman/Camilli/Gallagher's +4.3 at ES
0.40 and +7.26 for 9–10 practice exams, M4; Nickow tutoring d≈0.37; VanLehn ITS d≈0.76),
**not "2 sigma."** I will still fight for the features I think move the score most — but I
now agree the burden of proof is a CI, not my war stories. My champions ride into the
`eval/ablation.py` harness like everyone else's, and if Blind Review's routing doesn't beat
the "all-correct = mastery" baseline on held-out timed accuracy, I lose it. Fair.

### 1b. Okafor is right: a daily 50%-success engine kills adherence — so ZPD ~85% runs the day, and the clock is a deliberate tool, not the water supply.

This is the reframing that actually changed my design. In Round 1 I treated the **ZPD
~85% selector** (M4-F1) as cheap "plumbing" and buried it in my conditional tier. Okafor
(and Sorensen, and Nair) are right that it is not plumbing — it is the **adherence
backbone**, and it resolves a tension I had left unresolved. Metcalfe & Kornell's region
of proximal learning (8 experiments, M4) says humans learn fastest and _persist_ on the
easiest-not-yet-mastered material; our current queue serves the _hardest card in the
weakest topic_, which is an adherence catastrophe. So I concede the structure: **the daily
practice engine targets ~85% success, and timed pressure is applied deliberately and by
consent — not constantly.** My Round-1 instinct to "make it timed and tighten it" courted
exactly the failure Beilock & Carr document (M3): pressure eats the working memory the
ablest rely on. I was about to weaponize the clock. I'm pulling back: pressure _tolerance_
is trained on a ramp, always with an untimed mode available, and the clock's main job early
is _diagnosis_ (the Choke Index), not daily punishment.

### 1c. Sorensen (and M3/R2) are right: hypercorrection without a SPACED re-test is a fake fix.

I championed the Hypercorrection Queue in Round 1 but flagged the caveat almost in
passing. Sorensen put the word in the feature name and she's right to: Butler, Fazio &
Marsh (M3) show high-confidence corrections **return unless re-practiced**, and Metcalfe
(R2) warns of the same reversion. So the spaced re-test is **not optional** — it is the
feature. A confident miss gets corrected, then re-tested on a _fresh_ item of the same
trap on a spaced schedule (our FSRS layer), and we ship the guard as an eval assertion:
delayed-retest accuracy on corrected high-confidence traps ≥ immediate (B's H3).

### 1d. Nair is right on two build facts I was hand-waving.

(i) **Fund the cheap pressure/knowledge diagnostic before the full section simulator.**
The timed↔untimed gap — my whole "do you not know it or did you run out of time" thesis —
falls out of Blind Review's `phase` data essentially for free; the faithful 2LR+1RC
simulator is an effort-L UI build _gated on an item bank we may not have at section
length_. Nair's sequencing is correct: ship the diagnostic first, gate the simulator.
(ii) **The queue is Python-steerable** (`topic_weights_for_queue` → the Rust RPC), so
hypercorrection boosts, trap-granular priority, and the ZPD re-rank are **no-Rust**. I
accept that, and I accept batching `chosen` + `confidence` + `phase` into **one** schema
migration so we pay the full-sync cost once. I also concede Macnamara's point (M3/B): "just
do more PrepTests" is a weak lever; volume is not the play, _targeted_ practice is.

**What I did NOT concede:** that "cheap to code" or "not an RCT" is grounds to cut a
score-mover. See §2.

---

## 2. Held positions — the lines that buy points and must survive

### 2a. Capture the chosen distractor (Trap Profile). Non-negotiable, and nearly free.

This is now **near-unanimous** — me (C1), Sorensen (CF3), Nair (#1), Okafor (C2 insight
quadrant) — so I'm mostly _banking a win_ rather than fighting. But I want it on the record
as the one thing the moderator must not trade away in horse-trading. The chosen letter is
_already computed in `qt/aqt/lsat_performance.py` and thrown away on every answer_ (M1, R2,
Nair all flag this). A distractor is a diagnosis, not noise (Sadler 1998, R2), and _which_
distractor is formally modelable (Thissen 1989, R2). We are discarding the single most
diagnostic byte in the app. Capturing it is the highest-leverage ~20 lines in the project.
It is the substrate every other feature I care about feeds on. Do it first.

### 2b. Blind Review's timed→untimed "Gap Map" is the signature high-scorer technique. It stays a headline.

Sorensen wants to demote it because it's "7Sage community best-practice, not a controlled
trial" (B says so plainly). I concede the label — and I still refuse the demotion. Here's
the argument, on her terms: the _mechanisms underneath_ Blind Review are exactly the ones
she champions — miscalibration (Kruger–Dunning), learning-from-confident-error (Metcalfe),
withheld-feedback retrieval that blocks the re-reading fluency illusion (Dunlosky). Blind
Review is the _only_ feature on the board that produces the pressure-vs-knowledge
counterfactual, and that counterfactual is what makes our mastery signal **honest** (today
a lucky timed guess counts as mastery and suppresses a topic that still needs work, B).
"Not an RCT" is a reason to **measure it**, which I've conceded (1a) — it is not a reason
to cut the one diagnostic that tells a student which of two completely different study
plans to run. I hold it as a headline, shipped as a measured diagnostic.

### 2c. Pacing under realistic current-format conditions. You cannot cut the #1 score-killer because "policy evidence is only moderate."

This is the hill. Running out of time is the single largest source of lost points I have
ever seen, and two of the three scored sections are now LR at ~1:24/question (M4
`[market-grounding]`), so pacing is _doubly_ decisive. Sorensen argues pacing "should not
consume a headline evidence slot" because the optimal policy is `moderate`. That conflates
two different claims. The **format facts are LSAC-official STRONG** (2LR+1RC, 35-min,
speeded, in-center from Aug 2026). **That the test is speeded and that speededness costs
points is not a contested learning-science hypothesis — it is the construct.** The
`moderate` rating attaches only to the _optimization of the skip/guess policy_, and I don't
need the policy to be provably optimal — I need (i) format fidelity, (ii) a _measured_
skip-and-return / guess-and-move policy, and (iii) a **speededness metric**. Conceding the
policy is a heuristic (1d) is not the same as cutting pacing. A student who leaves four
blanks doesn't care that my guess threshold is a heuristic; they care that they're a 161
who should be a 168. Pacing stays.

---

## 3. Refined designs — reconciled with the others' constraints

### 3a. Pacing ⇄ Okafor's anxiety + Nair's build cost: split it into a cheap diagnostic, a consented ramp, and a gated simulator.

I'm cutting the "one big timed simulator" framing. Pacing becomes three pieces at three
price points:

1. **Per-item pacing + Choke Index (cheap; rides Blind Review's `phase`).** The Choke
   Index = relaxed/blind accuracy − timed accuracy per skill (M3-F5). It's a _free read-out_
   of the two-pass data Blind Review already produces. **Framed de-shamingly, always:** the
   message is _"you know this — you're rushing,"_ never _"you're too slow."_ This is the most
   humane diagnostic we have (Okafor's centerpiece, and I agree): it converts "I'm just bad"
   into a fixable pacing problem. Ships first.
2. **A consented, gradual timed ramp with an always-available untimed mode.** Per-item
   budgets tighten _only as accuracy holds_, opt-in, and there is _always_ a "learn" mode with
   no clock (Okafor's constraint 7). We build pressure _tolerance_; we don't shock. And the
   real anti-choke cure is **automaticity** (Beilock 2004: problems retrieved from memory show
   _no_ choking), not raw clock pressure — so the ramp is paired with the fluency work in 3c,
   not used as a cudgel.
3. **The faithful 2LR+1RC section simulator: CONDITIONAL on item-bank size.** I concede
   to Nair: this is the effort-L build, and if we can't assemble a faithful section it degrades
   to "short sets" and loses the realism that was its whole point. It's phase-2, gated on the
   bank — not a Round-1 headline. The **opt-in anxiety-writing** reset stays opt-in and
   _measured only_ (Ramirez & Beilock d=0.57 but Myers 2021 null, M3) — promised to no one.

That reconciles all three critiques: Okafor gets consent + untimed mode + de-shaming +
opt-in anxiety; Nair gets the cheap diagnostic first and the expensive sim gated; Sorensen
gets a measured speededness metric instead of a claimed "optimal policy."

### 3b. Blind Review ⇄ Nair's `phase` field: the two-pass loop _is_ a second event.

Nair's Primitive A already contains the mechanism: a blind pass is simply a **second
`append_event` for the same `item_id` with `phase="blind"`** — append-only, HLC-ordered,
sync-clean (B says the same). So Blind Review needs _no new data model beyond the shared
schema bump_; its marginal cost is the reviewer's two-pass flow + the honest-mastery filter

- the 2×2 dashboard. I adopt Nair's framing exactly, and I accept Okafor's scoping
  constraints as _part of the design_, not caveats: **scope the blind pass to flagged /
  low-confidence / skipped items only, cap per-item time, make the second pass optional per
  session, and enforce "don't peek" in code** (grade only after the blind answer is
  committed). The Choke Index (3a) reads this same `phase` data — one build, two features.

### 3c. Structure Sprints ⇄ everyone: fold into a Fluency/Automaticity gate, keep only if cheap.

In Round 1 this was my most provisional pick, and the room is right to be skeptical:
Sorensen notes the big PLM effects are adjacent-domain (Kellman) with LSAT transfer
_unproven_; Nair didn't headline it. So I demote it from a standalone headline and **fold
it into Fluency Gates** (R1-F2): a skill retires only when _accurate AND fast_, with a
passive Not-yet → Effortful → **Automatic** badge. This does triple duty — it's the
proven anti-choke mechanism (Beilock 2004), it's the one drill Okafor says students
actually _enjoy_ opening (game-like, seconds-long, Light friction), and it feeds pacing by
driving down recognition time. **Conditions I accept:** framed as "becoming automatic,"
never "you're too slow" (Okafor); guard RT-gaming with an accuracy co-criterion; and it
ships as a **measured ablation arm** (Sorensen) — if speeded classification doesn't lift
held-out timed accuracy, it's parked. It's in _only because it's cheap and rides existing
latency data_; the moment it needs bespoke content, it waits.

### 3d. My concession to the transfer camp, unchanged and honest.

Structure Twins (C10/CF12) remain my phase-2 olive branch to Sorensen — the best-evidenced
way to _build_ a transferable schema (Gentner 47% vs 6%, M2/C/R2) and squarely on the
post-2024 structural-matching task — but they are **untimed learning**, content-risky, and
gate behind the Transfer Meter + the fail-closed checker/`gold_set`. Not a headline; the
first thing I'd fund if we buy a phase-2 learning module.

---

## 4. Revised final set (what CHANGED from Round 1)

Still one closed loop — **diagnose → correct → automate → execute** — but re-tiered so the
daily engine is humane (~85%), the clock is deliberate, and every claim is falsifiable.

| #     | Feature                                                                                                          | Mode                                                                       | Concrete score-mechanism it targets                                                                                         | Δ from Round 1                                                                                                                                                                                         |
| ----- | ---------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **1** | **Trap Profile** (capture `chosen` → per-trap fingerprint across types)                                          | Built from **timed** data; surfaced for **untimed** review                 | Kills _repeat_ trap captures — the predictable pulls (R2) that leak points every session. Nearly free; the substrate.       | **Unchanged as #1.** Now explicitly the shared schema bump with confidence+phase (Nair).                                                                                                               |
| **2** | **Calibration + Hypercorrection Queue** (one-tap confidence → reliability curve → confident-miss re-test)        | **Untimed learning**, **spaced**                                           | Overwrites entrenched _confident_ wrong rules — the highest-ROI points (Metcalfe γ≈.51, R2/M3) — and _keeps_ them fixed.    | **Promoted into the set.** In R1 confidence-capture was a conditional prerequisite; I now name it, and the **spaced re-test is mandatory** (concession 1c).                                            |
| **3** | **Blind Review "Gap Map"** (timed → untimed second pass; 2×2 pressure/knowledge/fragile/mastered)                | The **mode-switch engine** itself                                          | Routes each miss to the _correct_ fix — pacing vs content — and makes mastery honest (drops lucky timed guesses).           | **Held as headline, now scoped + measured.** Scoped to flagged/low-conf/skipped (Okafor); rides `phase` (Nair); shipped as a measured diagnostic (Sorensen).                                           |
| **4** | **ZPD ~85% daily engine + per-item Pacing/Choke** (difficulty-targeted queue; Choke Index; consented timed ramp) | **Timed execution**, governed by an **~85% untimed/gentle daily baseline** | Attacks the #1 score-killer (speededness on 2×LR) _and_ isolates choking from ignorance — without a daily wall of failure.  | **Biggest change.** ZPD elevated from "plumbing" to the daily backbone (concession 1b); full section simulator **demoted to conditional/phase-2** (concession 1d); Choke Index now rides Blind Review. |
| **5** | **Fluency Gates** (RT-aware mastery + folded-in Structure Sprints)                                               | **Untimed learning** (automaticity)                                        | Drives recognition to automaticity — the proven anti-choke lever (Beilock 2004) and the root cause of most pacing failures. | **Refined & demoted.** Structure Sprints folded in (3c); framed de-shamingly; kept **only because it's cheap** and rides existing latency data. My most provisional pick.                              |

**How it chains:** ZPD (#4) keeps daily practice at ~85% so students _keep showing up_;
Blind Review + per-item timing (#3, #4) generate the timed/untimed data; the Trap Profile +
confidence capture (#1, #2) turn it into a personal weakness map; the Hypercorrection Queue
(#2) drills confident trap-misses on fresh, spaced items; Fluency Gates (#5) grind
recognition to automaticity so the next timed pass is faster. Every minute routes to a
named, **measured** weakness.

**What fell out of my headline set vs Round 1:** the _standalone_ Pacing Engine/full
section simulator (now conditional, gated on item bank) and _standalone_ Structure Sprints
(folded into Fluency Gates). **What climbed in:** the ZPD daily engine and the
calibration-capture I'd previously treated as a prerequisite.

---

## 5. Remaining disagreements for the moderator

1. **Build budget: full 2LR+1RC section simulator vs. per-item pacing.** _This is the live
   one._ Nair and I now agree the cheap per-item Choke/pacing diagnostic (rides Blind
   Review's `phase`) ships first. The open question is whether the **faithful section
   simulator** gets funded in this round at all, given it's effort-L and gated on item-bank
   size. My position: it's the truest rehearsal of the scored construct and belongs in
   phase-2 _the moment the bank supports a faithful section_; I'll accept parking it now, but
   I want it named as the next timed-execution build, not quietly dropped. **Decision needed:
   fund the simulator now, or gate it behind an item-bank threshold?**

2. **Is Blind Review a headline or a "measured diagnostic we don't advertise"?** Sorensen
   and I agree on the _build_ and on _measuring_ it; we disagree on billing. I say it's the
   signature high-scorer technique and should headline (2b); she says no evidence-based
   _claim_ until the routing-validity check passes. Moderator should decide how we _describe_
   it externally while the eval matures.

3. **How hard to lean on the ZPD ~85% target as a number.** The 85% figure is neural-net/
   theoretical (Wilson 2019, M4); the _human_ region-of-proximal-learning direction is strong
   (Metcalfe & Kornell). We all agree to ship `τ` as an ablatable config — but is ~85% the
   default we tune around, or do we let the harness pick it cold? (Minor, but it sets the
   daily feel of the app.)

4. **Confidence-tap friction ceiling.** Nair asked for a hard number (taps/session, max
   session-time delta) as a build constraint. Okafor wants one tap, sampled every Nth item,
   skippable. I'm fine with sampling — but the Hypercorrection Queue (#2) needs _enough_
   confidence signal on _misses_ to work. Moderator should set the sampling rule so we don't
   starve the feature that depends on it.

5. **Where the anti-choke effort goes.** Automaticity (Fluency Gates) vs. the consented
   timed ramp vs. opt-in anxiety reset — all three target choking. I rank them
   automaticity > ramp > anxiety-writing (the last is contested, Myers null). Worth an
   explicit call so we don't build all three at headline priority.

---

## Summary (≈8 lines)

- **Revised set (5, re-tiered for convergence):** (1) **Trap Profile** — capture the chosen
  distractor, near-free, the substrate; (2) **Calibration + Hypercorrection Queue** — one-tap
  confidence → _spaced_ re-test of confident misses; (3) **Blind Review "Gap Map"** — the
  timed→untimed pressure-vs-knowledge diagnostic; (4) **ZPD ~85% daily engine + per-item
  Pacing/Choke** — humane daily difficulty, deliberate clock; (5) **Fluency Gates** (Structure
  Sprints folded in) — automaticity as the real anti-choke, kept only because it's cheap.
- **Biggest concession:** score claims get **proven on held-out, unseen exam-style items at
  equal study time (CI excludes 0), honest ceiling ~4–7 points — not "2 sigma"** (Sorensen);
  and, relatedly, **ZPD ~85% runs the daily engine while the clock becomes a deliberate tool,
  not the water supply** (Okafor) — which demoted my standalone section simulator.
- **Biggest held line:** **pacing under realistic current-format conditions attacks the #1
  score-killer and cannot be cut because "policy evidence is only moderate"** — the moderate
  rating is on the _skip/guess policy_, not on _whether speededness costs points_; the format
  facts are LSAC-STRONG. Capturing the chosen distractor is the companion non-negotiable.
- **Biggest open item for the moderator:** how much build budget goes to a **full 2LR+1RC
  section simulator** vs. the **cheap per-item pacing/Choke diagnostic** that rides Blind
  Review's `phase` data.

_Marcus Webb — Round 2. I gave you the eval bar and the ~85% day. I keep the clock and the trap._
