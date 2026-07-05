# Round 2 — Rebuttal & Refinement: The Student Advocate

**Speaker:** Sam Okafor, learning-experience designer & student advocate
**Judged by:** cognitive load · adherence · motivation · psychological well-being (test anxiety / choking)
**Round-2 thesis:** _In Round 1 I protected the student by cutting. In Round 2 I protect the student by **constraining**. Almost every feature my colleagues want is safe for a tired human at 10pm — if we fix its UX so it can never drift into homework. My job now is to say "yes, and here is the exact shape it must take," not "no."_

I have re-read all four Round-1 openings (`round1-cognitive-scientist.md`, `round1-lsat-coach.md`, `round1-engineer.md`, and my own) and re-consulted memos `03` and `04`. The good news for convergence: my colleagues have already done most of my work for me. The Coach scoped Blind Review to flagged items and kept the anxiety tool opt-in. The Scientist insists on measuring everything on held-out items and only wants the confidence tap because it's one tap. The Engineer literally offered to treat my friction ceiling as a build constraint on Primitive A and asked me for the numbers. So here they are.

---

## 1. Concessions — where my colleagues moved me

I came in fearing that "effective" would be allowed to mean "heavy." My colleagues showed me it doesn't have to. Five genuine movements:

1. **The Coach is right that some timed pressure is necessary — and can be _protective_.** In Round 1 I treated the clock mostly as a threat (Beilock & Carr: pressure eats the working memory the ablest rely on). I still believe that. But Marcus's core point lands: the LSAT _scores execution under a stopwatch_, and the timed↔untimed decomposition is the single most **de-shaming** diagnostic we can hand a student — "you _know_ this, you're just rushing." That is exactly the message my own Choke Index was built to deliver. And the Scientist's own evidence closes the loop: automaticity (Beilock 2004, `03`) is the _proven_ anti-choke mechanism, and you cannot build automaticity without ever practicing under time. **I concede: timed pressure belongs in the core, not the margins — _if_ it is opt-in, gently ramped, and framed to reduce self-blame rather than manufacture panic.**

2. **The Scientist's structured "why-wrong" is fine — because it can be SELECT-not-type.** In Round 1 I was ready to cut self-explanation as a homework trap (Bisra g=0.55 comes from short, supervised, compliant sessions). The resolution the Coach proposed and the Scientist implicitly accepted is the one I can enthusiastically ship: a **one-tap trap-menu** ("which trap got you?") in the timed loop preserves the _diagnostic and discrimination_ act — the learner still has to identify the reasoning bug — at Feather friction, and it _feeds the trap profile for free_. **I concede the mechanism I was most hostile to, in its select-first form.** (Honest caveat I owe the Scientist: a menu tap is recognition, not full generation, so it captures _most_ of the g=0.55 benefit, not all of it. That's why the _full written_ autopsy still exists — parked where friction is affordable, in untimed Blind Review — and why I'll back A/B'ing the prompt against a no-prompt arm to check the Barbieri 2023 risk.)

3. **The Engineer can make the confidence tap literally one tap — so it earns its friction.** The Scientist said it best: the confidence tap is "the highest engagement-to-value ratio in the set." One tap (sure/likely/guess), sampled, skippable, captured at the _graded_ answer (Rhodes & Castel), unlocks the entire calibration + hypercorrection + SRL stack. **I concede it in full and hand over exact numbers (§3).** In Round 1 I rated it Light; now I'll actively defend it as the _one_ piece of per-item friction worth having.

4. **Felt-fluency is a liar — I will not let "adherence" become "make it easy."** The Scientist pre-empted my weakest instinct, and fairly. Desirable difficulties feel worse but teach better (Soderstrom & Bjork); re-reading feels great and is low-utility (Dunlosky). **I concede the framing correction: my lens optimizes for _sustainable effort_, not _comfort_.** This is precisely why I anchor the daily engine at ~85% success (hard-but-surmountable — a desirable difficulty), not at "easy," and why I accept **graded retrieval, never passive re-reading, as the substrate.** Adherence is the delivery mechanism for effortful practice, not an excuse to dilute it.

5. **Blind Review is worth the second pass — once it's scoped.** In Round 1 I called doubling session length "adherence poison." I still would — for a _full_ second pass. But the Coach and Engineer both scoped it to **flagged / low-confidence / skipped items only**, and the Engineer showed the marginal cost is just the reviewer flow (the `phase` field and confidence tap are already there). Scoped like that, the 2×2 "pressure vs knowledge" map _buys_ the student something — a reason each extra minute exists. **I concede Blind Review into my core set (§4), with UX guardrails (§3).**

---

## 2. Held positions — my non-negotiables

Convergence is not capitulation. Four lines I will not move off, because they are what keep an effective app from becoming an abandoned one.

1. **The friction budget is real and it is quantified. No feature may add a _typing form_ to the timed loop.** Timed practice gets at most **one discretionary tap per item** (confidence), plus **one optional trap-select tap on a miss** — both from menus, both skippable, zero free-text, zero multi-step forms. Typing lives _only_ in untimed modes. This is not a vibe; it's a build constraint (see §3's budget), and I'm handing it to the Engineer as requested.

2. **Anxiety tooling stays opt-in and MEASURED — never "this will calm you."** The evidence is genuinely split: Ramirez & Beilock (2011) got d=0.57; Myers, Davis & Chan (2021) got a clean null across four authentic exams (`03`). So the worry-dump / reset ships **default-off**, discloses the contested evidence in-product, shows _our own_ harness numbers, and **promises nothing**. Anyone who wants to headline "reduces your anxiety" as a benefit gets a veto from me. A feature that _claims_ to calm you and doesn't is worse than no feature — it teaches the student their anxiety is unfixable.

3. **The daily engine targets ~85% success (ZPD), not 50%.** This is my Round-1 strongest cut and it stands. Metcalfe & Kornell (8 experiments, `04`) show humans thrive on the _easiest-not-yet-mastered_ material; the Fisher-information optimum for _measurement_ (P≈0.5) is the _opposite-difficulty job_ (`04`, Myth 3). A student served items calibrated to make them wrong half the time, every day, for months, will experience exactly the helplessness the literature predicts, and quit. The mini-CAT probe is a **rare, opt-in, explicitly-labeled "level check,"** capped at a small share of a session — never the daily driver.

4. **Insight must be framed non-punitively: name the fixable habit, never the person.** "Extreme-language traps own 38% of your Strengthen misses" externalizes the error to a habit the student can beat. "You're bad at Strengthen" is an identity verdict that demoralizes and predicts nothing actionable. Same data, opposite effect. This law binds _every_ feature — especially the trap profile, the hypercorrection queue, and the fluency/pacing signals (no speed-shaming). No streak-reset guilt, no "wrong again," no manufactured loss-aversion.

_(Carried from Round 1, still binding: abstain honestly on small samples — never render "you're bad at X" from 4 data points; and every loop has a stop-rule and a celebrated finish — no infinite queues.)_

---

## 3. Refined designs — the exact low-friction UX to ratify (my main contribution)

This is the heart of my Round-2 offer. For **each consensus feature**, I specify the tap count, _when_ friction is permitted, and the framing — so implementation cannot silently drift from "one-tap insight" into "type a paragraph after every question." If we ratify this table, I can stop being the person who says no.

### Sam's Friction Budget (hand this to the Engineer as a build constraint)

| Context                            | Allowed per-item friction                                                           | Typing?            | Notes                                                                                             |
| ---------------------------------- | ----------------------------------------------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------- |
| **Timed loop**                     | ≤ **1** discretionary tap (confidence) + **1** optional trap-select tap _on a miss_ | **Never**          | Both sampled/skippable; answer selection itself is the task, not "friction."                      |
| **Untimed "learn" / Blind Review** | Whatever the learning move needs (written autopsy, skeleton-build)                  | **Yes, here only** | This is the friction sandbox. Friction is _appropriate_ when building the tool.                   |
| **Dashboard / between sessions**   | Unlimited passive insight                                                           | n/a                | No per-item cost; this is where profiles/curves live.                                             |
| **Session shape**                  | —                                                                                   | —                  | Stop-rule + celebrated finish on every loop; confidence tap auto-downsamples on detected fatigue. |

### Per-feature UX specs

**A. Trap capture + profile** _(everyone's #1 substrate)_

- **Friction: ZERO added.** The chosen letter is _already computed and discarded_ in the reviewer hook (Engineer's find) — capturing it is free and adds no interaction.
- **Profile surfacing:** passive, dashboard + session-boundary only. **Never interrupts an item.**
- **When friction is allowed:** none. This is pure insight-from-data-we-already-have — my favorite quadrant.
- **Framing:** _"Extreme-language traps own 38% of your Strengthen misses"_ + 2–3 exemplar misses + a one-tap route to fix. **Never** _"you're bad at Strengthen."_
- **Guard:** abstain until ≥ N misses of that trap type; show a confidence band; name at most **one headline pattern** at a time (dosage — see §5).

**B. One-tap confidence + calibration**

- **Friction: exactly 1 tap.** Three buttons — **sure / likely / guess** (mapped to probabilities). **Not a slider** (a slider is a fiddle, not a tap; "the moment it's a slider mid-section it's dead" — the Coach, and I agree). Captured _at/after the graded answer_, not as a pre-answer fluency judgment.
- **Sampling:** every item is acceptable _because it's one tap_, but **auto-downsample to every Nth item** if fatigue is detected (rapid identical taps / speeding); always skippable with no penalty.
- **When friction is allowed:** the one tap, in any mode.
- **Framing:** _"Your guesses are better calibrated than your 'sures' on Necessary Assumption"_ — fascinating self-knowledge, not a report card. Measure the **individual's own reliability curve**; never invoke the Dunning–Kruger "the incompetent are uniquely blind" mechanism (Gignac & Zajenkowski artifact caveat, `03`).

**C. Hypercorrection queue** _(promoted to my core this round)_

- **Friction: ZERO added.** It rides entirely on the confidence tap (B); it is an invisible re-rank.
- **When friction is allowed:** none.
- **Framing (I hold hardest here):** confident-wrong resurfacing is a **surprise/insight** — _"You were sure on this one — here's the trap that got you"_ — **never** _"wrong again."_
- **Guards:** (1) **Blend, don't replace** — bounded boost, capped share of the session; leading every session with your worst misses is punishing. (2) **Spacing is mandatory** (Butler/Fazio/Marsh: confident errors return without re-practice, `03`), but **re-test with a _fresh_ item of the same trap/skill** where possible, so it reads _"let's nail this pattern,"_ not _"here's your failure, redo it."_ (3) Distribute across the session, never front-load a wall of misses.

**D. ZPD selection** _(the daily engine — my Round-1 #1, unchanged)_

- **Friction: ZERO added** (backend re-rank of the existing queue).
- **Target:** predicted **~85%** success — hard-but-surmountable, a _desirable difficulty_, **not** dumbing down. Keep a band (~75–90%) plus rare stretch/reach items so it never over-narrows (addresses the Scientist's "don't soften the content" and the Engineer's "keep a band").
- **When friction is allowed:** none.
- **Framing:** _silent._ The student simply experiences a winnable-but-effortful flow; we **never** announce "we made this easier." ~85% is a tunable, ablatable target (Wilson 2019 is theoretical), and we **abstain to plain ordering when the model is thin.**
- **Hard line:** the P≈0.5 mini-CAT is **not** this selector. Different job, different difficulty, capped and labeled (§2.3).

**E. Blind Review** _(conceded into my set — here's how it stays humane)_

- **Scope:** second, **untimed** pass on **flagged / "guess"-confidence / skipped / answer-changed items only** — **never** the whole section. This is the difference between a diagnostic and a doubling of work.
- **Cadence:** **opt-in**, offered (not forced) after a timed set. Default-_suggested_, one-tap to start or skip.
- **When friction is allowed:** _here._ This is the home of the **full written why-right/why-each-wrong autopsy** (Bisra's g=0.55 gets its full expression in untimed mode) — but even here, keep it **select-first, type-optional**.
- **Payoff / framing:** the 2×2 map (**pressure / knowledge / fragile / mastered**) is the reward that justifies the extra minutes, and each quadrant **routes to its fix** (pressure → pacing/automaticity; knowledge → content/hypercorrection). Headline message: _"Untimed you're 88%, timed 71% — that 17-point gap is pacing, not knowledge, and pacing is faster to fix."_ Most motivating sentence in the app.

**F. Pacing / choke trainer** _(timed pressure, made safe)_

- **Modes:** an **always-available untimed "learn" mode**, and a **separate opt-in "train pacing" mode.** Never blur them.
- **Ramp:** tighten per-item time budgets **gently and by consent** — only as accuracy _holds_ at the current budget. Build tolerance; never shock.
- **Choke Index** (relaxed − timed accuracy): the de-shaming diagnostic. Full 35-min **section simulator** is _periodic, opt-in exposure_ (anxiety-inducing by construction), not the daily driver.
- **Automaticity companions (my Round-1 champions, kept):** **Fluency Gates** (passive Not-yet → Effortful → **Automatic** badge) and **Structure Sprints** (seconds-long, game-like classification, Light friction, genuinely fun to open). These _are_ the anti-choke mechanism (Beilock 2004).
- **Framing:** the speed signal is _"becoming automatic"_ / _"Automatic!"_ — **never** _"you're too slow."_ No speed-shaming.
- **Anxiety reset:** opt-in, default-off, measured, **unpromised** (§2.2).

**G. Self-explanation / Trap Autopsy** _(the mechanism I flipped on)_

- **Timed mode:** **one tap** from the trap menu ("which trap got you?" → out-of-scope / extreme-language / reversal / half-right / sufficient↔necessary / …), **on misses (and optionally confident-wrong) only.** Never on items answered correctly — spend the budget where the ROI is.
- **Optional bonus:** **one** free-text line, never required, never gates progress or mastery.
- **Untimed / Blind Review mode:** full written autopsy welcome (see E).
- **When friction is allowed:** the one select-tap in timed; free text only in untimed.
- **Framing:** _"which trap got you?"_ is curiosity and diagnosis, not _"explain your failure."_
- **Honesty note (owed to the Scientist):** select < full-generation on fidelity; I'm buying most of the effect at a fraction of the friction and preserving the full version untimed. **Measure it** (A/B the prompt vs no-prompt; Barbieri 2023 risk).

**Support layer I also ratify:** the **Transfer Meter** (Feather, backend, honesty instrument) — I back it, because it's the thing that stops us shipping surface-bound drills that only _feel_ like they teach transfer. And any **Structure Twins** work is welcome **in untimed learning mode only**, built by **select/drag not free-type**, adaptively faded (Kalyuga), never every-item, never under the clock, and **gated behind the Transfer Meter proving the twins are valid.**

---

## 4. My revised final set (and what changed from Round 1)

Given the constraints above, here is the set I can _enthusiastically_ support — not tolerate, support. It is one coherent low-friction loop sharing a single one-tap primitive.

1. **ZPD daily engine (~85%) + free trap capture + trap profile.** The adherence backbone at Feather friction; insight from data we already collect. _(Unchanged as my #1 — now explicitly bundled with the free `chosen`-letter capture and the non-punitive trap profile.)_

2. **One-tap confidence → calibration + hypercorrection queue.** One tap unlocks motivating self-knowledge _and_ the blended, spaced, non-punitively-framed hypercorrection queue. _(**Changed:** hypercorrection was my optional 5th in Round 1; it's now core, because it rides free on the tap and I've pinned down the framing that keeps it from feeling like punishment.)_

3. **Blind Review (scoped, opt-in) with the pressure/knowledge 2×2 + select-tap Trap Autopsy.** _(**Biggest change:** in Round 1 I called the doubled pass "adherence poison" and kept it merely conditional. Scoped to flagged items, opt-in, and carrying the select-tap autopsy, it becomes the most _de-shaming_ diagnostic we have — so it's now in my core set.)_

4. **Pacing/Choke trainer — gentle opt-in ramp + Fluency Gates + Structure Sprints + opt-in, measured anxiety reset.** The well-being spine, now merged with automaticity training (the real anti-choke lever). _(**Changed:** I now explicitly concede timed pressure is _necessary and protective_ when ramped and consented — Round 1 framed the clock more defensively.)_

5. **(Support, not lead) Transfer Meter as the honesty instrument**, gating any Structure Twins to untimed/select-only. _(**New as an explicit endorsement** — my olive branch to the transfer camp, safe because it's backend and keeps everyone honest.)_

**What I held from Round 1:** the cut of the **daily P≈0.5 mini-CAT**, of **mandatory typed articulation on every item**, and of **punitive gamification** (streak-shaming). Those stay cut.

**Net motion:** I moved from 4 guarded picks (with one optional) to **4 core + 1 supported**, and I said an enthusiastic yes to three things I was defensive about in Round 1 (Blind Review, hypercorrection, select-tap autopsy) — because in every case a UX constraint, not a veto, was the right tool.

---

## 5. Remaining disagreements for the moderator

Convergence is close. These are the open calls I'd ask the moderator to rule on:

1. **Default-on vs opt-in for timed pressure.** The Coach ranks pacing as priority #1 and may want timed practice (and the ramp) **default-on**; I want it **opt-in with an always-available untimed mode** and a consented ramp. _My ask:_ opt-in default, with a strong (but skippable) nudge. Ruling needed on the default and on ramp aggressiveness.

2. **How much insight before it demoralizes (dosage).** Trap profile + calibration + choke index are motivating _if_ framed right — but there's a real dosage question. _My position:_ surface **one headline "fixable pattern" + its route** per session; keep the fuller diagnostic on a pull-not-push dashboard. Others may want a richer default readout. Ruling needed on how many "here's what you get wrong" signals a session can carry before insight tips into discouragement.

3. **Confidence tap: every-item vs sampled.** Scientist/Engineer want every item (maximal calibration data); I want **auto-sampling under detected fatigue.** Small, but worth a ruling so the tap never becomes the thing people quit over.

4. **Blind Review cadence.** Suggested-default-after-every-timed-set (Coach's lean) vs fully opt-in (mine). Adherence vs data-density trade.

5. **Mini-CAT "level check" frequency & framing.** All four of us agree it's not the daily engine. Open: how often it runs (weekly? on-demand only?) and whether its P≈0.5 stream needs an explicit _"this is a measurement — expect it to feel hard"_ label so the difficulty doesn't read as failure.

6. **Structure Twins: phase-1 or phase-2, and the validity bar.** I (and the Engineer) say ship the **Transfer Meter first** and gate Twins on it clearing a twin-validity bar; the Scientist wants Twins in the moment the meter proves valid. Ruling needed on sequencing.

7. **Self-explanation fidelity trade.** Does the one-tap select preserve _enough_ of the g=0.55 generative benefit, or does the Scientist need at least the optional free-text to "count"? _My ask:_ let the eval settle it — A/B select-only vs select+optional-text vs no-prompt, on held-out items.

---

## 6. Summary

- **My revised set (4 core + 1 supported):** (1) **ZPD ~85% daily engine + free trap capture/profile**; (2) **one-tap confidence → calibration + (blended, spaced) hypercorrection queue**; (3) **scoped, opt-in Blind Review with the pressure/knowledge 2×2 + select-tap trap autopsy**; (4) **pacing/choke trainer — gentle opt-in ramp + Fluency Gates + Structure Sprints + opt-in/measured anxiety reset**; plus (5) the **Transfer Meter** as a supported honesty instrument gating any untimed Structure Twins.
- **Non-negotiable UX constraints:** the **timed loop gets ≤1 confidence tap + ≤1 trap-select tap on a miss, zero typing, zero forms** — all typing lives in untimed modes; **anxiety tools are opt-in, default-off, measured, and promise nothing**; the **daily engine sits at ~85% success, never the P≈0.5 measurement difficulty**; and **all insight names the fixable habit ("extreme-language owns your Strengthen misses"), never the person ("you're bad at Strengthen")** — no streak-shaming, no speed-shaming, no "wrong again."
- **Biggest concession:** I accept that **timed pressure is necessary and can be protective** — so **Blind Review and a consented pacing ramp move into my core set** (with scoping + opt-in guardrails), reversing my Round-1 stance that the doubled pass was "adherence poison." Runner-up concession: **structured self-explanation is in — as a one-tap trap-select**, not the typed homework I feared.
- **What changed:** hypercorrection promoted (optional → core), Blind Review promoted (conditional → core), select-tap autopsy endorsed; the cuts I held are the daily mini-CAT, mandatory typing, and punitive gamification.

_Sam Okafor — Round 2. I'm no longer guarding the door; I'm holding the blueprint. Give me these constraints and I'll champion the whole loop._
