# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""The LSAT notetypes, created through Anki's models API.

Three notetypes back the LSAT layer:

- ``LSAT Card`` -- a spaced-repetition drill of a *reusable judgment* (name the
  flaw, classify the stem, execute a conditional transform).
- ``LSAT Item`` -- a graded, multiple-choice practice question; answering these
  is the performance signal the score models read.
- ``LSAT PerformanceEvent`` -- an append-only log row (one note per graded
  answer). These ride Anki's note sync so the event log merges cleanly across
  devices; their cards are not meant for study and are suspended when events are
  recorded.

``ensure_notetypes`` is idempotent: it only creates a notetype that is missing,
so it is safe to call on every startup / before seeding.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anki.collection import Collection
    from anki.models import NotetypeDict

LSAT_CARD = "LSAT Card"
LSAT_ITEM = "LSAT Item"
LSAT_PERFORMANCE_EVENT = "LSAT PerformanceEvent"
# Append-only per-section trajectory (DECISION-round4 #17: the Timed Section
# Runner / First-Instinct Ledger). Like PerformanceEvent, its cards are suspended
# (attempts are logged, never studied) and it syncs as ordinary notes so the
# HLC-merge rules apply. The full per-question trajectory lives in a JSON field.
LSAT_SECTION_ATTEMPT = "LSAT SectionAttempt"

# Field order matters: the first field is the sort field in the browser.
CARD_FIELDS = [
    "front",
    "back",
    "explanation",
    "skill_tags",
    "source_id",
    "source_quote",
    # SPOV 1 (docs/Speedrun_AI_Features.md A1): the reasoning-primitive family this
    # card drills -- "diction" (precise connective/term meanings), "logic"
    # (formal rules + named fallacies) or "qtype" (question-type taxonomy and
    # its prescribed attack). Coverage, scheduling and analytics slice by it.
    "primitive_type",
    # The exam weight of the primitive (taxonomy exam_weight/study_weight at
    # seed time), so queue/coverage code can read it off the note directly.
    "topic_weight",
]
ITEM_FIELDS = [
    "stem",
    "choices",
    "correct",
    "skill_tags",
    "difficulty",
    "source_id",
    "source_quote",
    # Per-distractor trap labels, e.g. "B=extreme_language A=out_of_scope"
    # (families are the skill.trap.* leaves in lsat-taxonomy.yaml). Powers the
    # Distractor-Reasoning Engine: attributes the trap a student fell for and
    # grades the "which trap is (C)?" tap. Optional/blank on legacy items.
    "distractor_traps",
]
EVENT_FIELDS = [
    "item_id",
    "skill_tags",
    "correct",
    "response_ms",
    "answered_at_hlc",
    "device_id",
    # Per-answer annotation store (the debate's keystone). These let the score
    # models read *how* an answer was reached, not just whether it was right:
    #   chosen     -- the multiple-choice letter actually selected (A-E); the
    #                 trap you picked is the diagnosis (Distractor-Reasoning).
    #   confidence -- one-tap self-rating "sure"/"likely"/"guess" ("" = unrated);
    #                 drives calibration + the hypercorrection queue.
    #   phase      -- "timed"/"blind"/"relaxed"; separates a lucky timed guess
    #                 from real mastery (Blind-Review Gap Map + phase-aware fold).
    #   identified -- identification-first stage grade (SPOV 1 / A2): "1" the
    #                 student named the question type correctly before solving,
    #                 "0" misidentified, "" no classify stage (legacy/RC items).
    "chosen",
    "confidence",
    "phase",
    "identified",
]

# LSAT SectionAttempt fields. The trajectory is a JSON array of per-question
# records (index, first/final answer, first/final correctness, changed, reached,
# flagged, dwell_ms); the diagnostic reads it in lsat/answer_change.py.
SECTION_FIELDS = [
    "trajectory",
    "n_questions",
    "started_at_hlc",
    "device_id",
]

# The LSAT Card (reusable-judgment drill) shares the LSAT Prep visual identity
# with the Item card. The shared CSS lives on the question side so ``{{FrontSide}}``
# carries it to the answer; the answer wrapper (``.lsat-card-back``) reuses the
# same tokens but omits the brand mark so it appears once per card.
_CARD_QFMT = r"""<div class="lsat-card">
<div class="lsat-card-front">{{front}}</div>
</div>
<style>
.lsat-card, .lsat-card-back {
  --lsat-accent:#4f46e5; --lsat-accent-2:#7c3aed; --lsat-ink-on-accent:#f5f6ff;
  --lsat-hero:linear-gradient(135deg,#4f46e5,#7c3aed);
  --lsat-surface:#ffffff; --lsat-inset:#eef1f7;
  --lsat-fg:#101526; --lsat-fg-subtle:#4a5468;
  --lsat-border:rgba(16,24,48,.10); --lsat-border-subtle:rgba(16,24,48,.06);
  --lsat-radius:18px; --lsat-radius-sm:11px;
  --lsat-shadow:0 1px 2px rgba(16,24,48,.04), 0 6px 18px -6px rgba(16,24,48,.10);
  --lsat-font:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,"Helvetica Neue",sans-serif;
  --lsat-mono:ui-monospace,"SF Mono","SFMono-Regular",Menlo,Consolas,"Liberation Mono",monospace;
  max-width: 720px; margin: 0 auto; text-align: left; line-height: 1.55;
  font-family: var(--lsat-font); color: var(--lsat-fg); -webkit-font-smoothing: antialiased;
}
@media (prefers-color-scheme: dark) {
  .lsat-card, .lsat-card-back {
    --lsat-accent:#7c86ff; --lsat-accent-2:#a78bfa; --lsat-ink-on-accent:#0d1017;
    --lsat-hero:linear-gradient(135deg,#7c86ff,#a78bfa);
    --lsat-surface:#161b26; --lsat-inset:#1c2331; --lsat-fg:#e8ebf2; --lsat-fg-subtle:#aab2c2;
    --lsat-border:rgba(255,255,255,.12); --lsat-border-subtle:rgba(255,255,255,.07);
    --lsat-shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -8px rgba(0,0,0,.6);
  }
}
.night-mode .lsat-card, .night-mode .lsat-card-back,
.nightMode .lsat-card, .nightMode .lsat-card-back,
.night_mode .lsat-card, .night_mode .lsat-card-back {
  --lsat-accent:#7c86ff; --lsat-accent-2:#a78bfa; --lsat-ink-on-accent:#0d1017;
  --lsat-hero:linear-gradient(135deg,#7c86ff,#a78bfa);
  --lsat-surface:#161b26; --lsat-inset:#1c2331; --lsat-fg:#e8ebf2; --lsat-fg-subtle:#aab2c2;
  --lsat-border:rgba(255,255,255,.12); --lsat-border-subtle:rgba(255,255,255,.07);
  --lsat-shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -8px rgba(0,0,0,.6);
}
.lsat-card::before {
  content:"\22A2"; display: flex; align-items: center; justify-content: center;
  width: 2.1em; height: 2.1em; margin: 0 0 .85rem; border-radius: var(--lsat-radius-sm);
  background: var(--lsat-hero); color: var(--lsat-ink-on-accent);
  font-family: var(--lsat-mono); font-weight: 700; line-height: 1; box-shadow: var(--lsat-shadow);
}
.lsat-card-front { font-size: 1.12em; line-height: 1.6; background: var(--lsat-surface);
  border: 1px solid var(--lsat-border); border-radius: var(--lsat-radius);
  box-shadow: var(--lsat-shadow); padding: 1.1rem 1.2rem; }
.lsat-card-back { margin-top: 1.1rem; }
.lsat-card-answer { font-size: 1.1em; font-weight: 700; background: var(--lsat-surface);
  border: 1px solid var(--lsat-border); border-left: 3px solid var(--lsat-accent);
  border-radius: var(--lsat-radius-sm); box-shadow: var(--lsat-shadow); padding: .9rem 1.05rem; }
.lsat-explanation { margin-top: .75rem; font-size: .96em; line-height: 1.55;
  color: var(--lsat-fg-subtle); background: var(--lsat-inset);
  border: 1px solid var(--lsat-border-subtle); border-radius: var(--lsat-radius-sm);
  padding: .85rem 1rem; }
@media (prefers-reduced-motion: reduce) { .lsat-card *, .lsat-card ::before { transition: none !important; } }
</style>"""
_CARD_AFMT = (
    "{{FrontSide}}\n\n<hr id=answer>\n\n"
    '<div class="lsat-card-back">\n'
    '<div class="lsat-card-answer">{{back}}</div>\n'
    '{{#explanation}}<div class="lsat-explanation">{{explanation}}</div>{{/explanation}}\n'
    "</div>"
)

# The Item question is identification-first (SPOV 1 / A2): for LR items the
# student must first NAME the question type (classify stage; graded via
# pycmd("lsatClassify:<node_id>")) before the choices unlock. Clicking a choice
# then reveals a one-tap confidence rating (sure/likely/guess, skippable); the
# rating tap posts pycmd("lsatAnswer:<LETTER>:conf=<label>:ident=<1|0>") --
# grading is deferred to that tap so confidence AND the classify-stage grade
# ride the SAME graded event (the log stays append-only). Python grades it (the
# correct answer is NOT in the question template, so it stays hidden) and
# returns {correct, correct_letter}.
_ITEM_QFMT_TEMPLATE = r"""<div class="lsat-item">
<div class="lsat-stem">{{stem}}</div>
<div id="lsat-raw" hidden>{{choices}}</div>
<div id="lsat-skills" hidden>{{skill_tags}}</div>
<div class="lsat-classify" id="lsat-classify" hidden>
  <span class="lsat-conf-label">First: what type of question is this?</span>
  <div class="lsat-classify-chips" id="lsat-classify-chips"></div>
  <div class="lsat-classify-feedback" id="lsat-classify-feedback" hidden></div>
</div>
<div class="lsat-choices" id="lsat-choices" hidden></div>
<div class="lsat-confidence" id="lsat-confidence" hidden>
  <span class="lsat-conf-label">How sure?</span>
  <button type="button" class="lsat-conf-btn" data-conf="sure">Sure</button>
  <button type="button" class="lsat-conf-btn" data-conf="likely">Likely</button>
  <button type="button" class="lsat-conf-btn" data-conf="guess">Guess</button>
  <button type="button" class="lsat-conf-btn lsat-conf-skip" data-conf="">skip</button>
</div>
<div class="lsat-contrast" id="lsat-contrast" hidden></div>
<div class="lsat-trap" id="lsat-trap" hidden></div>
</div>
<style>
/* LSAT Prep desktop reviewer card. Tokens mirror ts/lib/lsat/theme.scss so the
   in-app flashcard reads as the same premium product as the web UI. */
.lsat-item {
  --lsat-accent:#4f46e5; --lsat-accent-strong:#4338ca; --lsat-accent-2:#7c3aed;
  --lsat-ink-on-accent:#f5f6ff;
  --lsat-hero:linear-gradient(135deg,#4f46e5,#7c3aed);
  --lsat-surface:#ffffff; --lsat-inset:#eef1f7;
  --lsat-fg:#101526; --lsat-fg-subtle:#4a5468; --lsat-fg-faint:#667085;
  --lsat-border:rgba(16,24,48,.10); --lsat-border-subtle:rgba(16,24,48,.06);
  --lsat-good:#0f9d6a; --lsat-bad:#e0483d;
  --lsat-good-soft:rgba(15,157,106,.12); --lsat-good-line:rgba(15,157,106,.45);
  --lsat-bad-soft:rgba(224,72,61,.12); --lsat-bad-line:rgba(224,72,61,.42);
  --lsat-radius:18px; --lsat-radius-sm:11px;
  --lsat-shadow:0 1px 2px rgba(16,24,48,.04), 0 6px 18px -6px rgba(16,24,48,.10);
  --lsat-ring:0 0 0 3px rgba(79,70,229,.28);
  --lsat-t:180ms; --lsat-ease:cubic-bezier(.22,1,.36,1);
  --lsat-font:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,"Helvetica Neue",sans-serif;
  --lsat-mono:ui-monospace,"SF Mono","SFMono-Regular",Menlo,Consolas,"Liberation Mono",monospace;
  max-width: 760px; margin: 0 auto; text-align: left; line-height: 1.55;
  font-family: var(--lsat-font); color: var(--lsat-fg);
  -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;
}
/* Anki desktop toggles a class for night mode (prefers-color-scheme follows the
   OS, not the app theme), so drive dark via the class AND keep a media fallback
   for standalone/mobile contexts. Palette mirrors theme.scss's dark ramp. */
@media (prefers-color-scheme: dark) {
  .lsat-item {
    --lsat-accent:#7c86ff; --lsat-accent-strong:#949bff; --lsat-accent-2:#a78bfa;
    --lsat-ink-on-accent:#0d1017;
    --lsat-hero:linear-gradient(135deg,#7c86ff,#a78bfa);
    --lsat-surface:#161b26; --lsat-inset:#1c2331;
    --lsat-fg:#e8ebf2; --lsat-fg-subtle:#aab2c2; --lsat-fg-faint:#8b93a5;
    --lsat-border:rgba(255,255,255,.12); --lsat-border-subtle:rgba(255,255,255,.07);
    --lsat-good:#34d399; --lsat-bad:#f87171;
    --lsat-good-soft:rgba(52,211,153,.15); --lsat-good-line:rgba(52,211,153,.5);
    --lsat-bad-soft:rgba(248,113,113,.15); --lsat-bad-line:rgba(248,113,113,.5);
    --lsat-shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -8px rgba(0,0,0,.6);
    --lsat-ring:0 0 0 3px rgba(124,134,255,.35);
  }
}
.night-mode .lsat-item, .nightMode .lsat-item, .night_mode .lsat-item {
  --lsat-accent:#7c86ff; --lsat-accent-strong:#949bff; --lsat-accent-2:#a78bfa;
  --lsat-ink-on-accent:#0d1017;
  --lsat-hero:linear-gradient(135deg,#7c86ff,#a78bfa);
  --lsat-surface:#161b26; --lsat-inset:#1c2331;
  --lsat-fg:#e8ebf2; --lsat-fg-subtle:#aab2c2; --lsat-fg-faint:#8b93a5;
  --lsat-border:rgba(255,255,255,.12); --lsat-border-subtle:rgba(255,255,255,.07);
  --lsat-good:#34d399; --lsat-bad:#f87171;
  --lsat-good-soft:rgba(52,211,153,.15); --lsat-good-line:rgba(52,211,153,.5);
  --lsat-bad-soft:rgba(248,113,113,.15); --lsat-bad-line:rgba(248,113,113,.5);
  --lsat-shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -8px rgba(0,0,0,.6);
  --lsat-ring:0 0 0 3px rgba(124,134,255,.35);
}
/* brand mark — the turnstile, the one signature-gradient "proven" moment */
.lsat-item::before {
  content:"\22A2"; display: flex; align-items: center; justify-content: center;
  width: 2.1em; height: 2.1em; margin: 0 0 .85rem; border-radius: var(--lsat-radius-sm);
  background: var(--lsat-hero); color: var(--lsat-ink-on-accent);
  font-family: var(--lsat-mono); font-weight: 700; font-size: 1em; line-height: 1;
  box-shadow: var(--lsat-shadow);
}
/* question stem — a clean reading surface */
.lsat-stem {
  white-space: pre-wrap; font-size: 1.08em; line-height: 1.6; color: var(--lsat-fg);
  background: var(--lsat-surface); border: 1px solid var(--lsat-border);
  border-radius: var(--lsat-radius); box-shadow: var(--lsat-shadow);
  padding: 1.1rem 1.2rem;
}
/* answer choices — well-spaced tappable rows with a circled (mono) letter */
.lsat-choices { display: flex; flex-direction: column; gap: .55rem; margin-top: 1.15rem; }
.lsat-choice { display: flex; align-items: flex-start; gap: .7rem; text-align: left;
  width: 100%; min-height: 52px; padding: .8rem .95rem; border: 1px solid var(--lsat-border);
  border-radius: var(--lsat-radius-sm); background: var(--lsat-surface); color: var(--lsat-fg);
  font: inherit; font-size: 1em; line-height: 1.5; cursor: pointer; box-shadow: var(--lsat-shadow);
  transition: border-color var(--lsat-t) var(--lsat-ease),
    box-shadow var(--lsat-t) var(--lsat-ease),
    background var(--lsat-t) var(--lsat-ease), transform .06s ease; }
.lsat-choice:hover:not(.disabled) { border-color: var(--lsat-accent); }
.lsat-choice:active:not(.disabled) { transform: translateY(1px); }
.lsat-choice:focus-visible { outline: none; border-color: var(--lsat-accent); box-shadow: var(--lsat-ring); }
.lsat-choice.disabled { cursor: default; box-shadow: none; }
.lsat-choice.chosen { border-color: var(--lsat-accent); box-shadow: 0 0 0 1px var(--lsat-accent); }
.lsat-choice.right { border-color: var(--lsat-good-line); background: var(--lsat-good-soft); box-shadow: none; }
.lsat-choice.wrong { border-color: var(--lsat-bad-line); background: var(--lsat-bad-soft); box-shadow: none; }
/* credited answer gets a calm turnstile mark — never a punishing X on a miss */
.lsat-choice.right::after { content:"\22A2"; margin-left: auto; align-self: center;
  padding-left: .6rem; font-family: var(--lsat-mono); font-weight: 700; color: var(--lsat-good); }
.lsat-letter { display: inline-flex; align-items: center; justify-content: center;
  width: 1.85em; height: 1.85em; flex: 0 0 auto; margin-top: .02em; border-radius: 50%;
  font-family: var(--lsat-mono); font-weight: 700; font-size: .82em;
  background: var(--lsat-inset); color: var(--lsat-accent); border: 1px solid var(--lsat-border-subtle);
  transition: background var(--lsat-t) var(--lsat-ease), color var(--lsat-t) var(--lsat-ease); }
.lsat-choice.chosen .lsat-letter { background: var(--lsat-accent); color: var(--lsat-ink-on-accent); border-color: transparent; }
.lsat-choice.right .lsat-letter { background: var(--lsat-good); color: #fff; border-color: transparent; }
.lsat-choice.wrong .lsat-letter { background: var(--lsat-bad); color: #fff; border-color: transparent; }
/* confidence + trap taps — pills */
.lsat-confidence, .lsat-trap { display: flex; align-items: center; gap: .45rem;
  margin-top: 1.05rem; flex-wrap: wrap; }
.lsat-conf-label { color: var(--lsat-fg-faint); font-size: .92em; margin-right: .2rem; }
.lsat-conf-btn { min-height: 40px; padding: .45rem .9rem; border: 1px solid var(--lsat-border);
  border-radius: 999px; background: var(--lsat-surface); color: var(--lsat-fg); font: inherit;
  font-weight: 600; font-size: .95em; cursor: pointer; box-shadow: var(--lsat-shadow);
  transition: border-color var(--lsat-t) var(--lsat-ease), color var(--lsat-t) var(--lsat-ease),
    background var(--lsat-t) var(--lsat-ease); }
.lsat-conf-btn:hover:not(:disabled) { border-color: var(--lsat-accent); color: var(--lsat-accent); }
.lsat-conf-btn:focus-visible { outline: none; border-color: var(--lsat-accent); box-shadow: var(--lsat-ring); }
.lsat-conf-btn:disabled { opacity: .5; cursor: default; box-shadow: none; }
.lsat-conf-skip { opacity: .7; border-style: dashed; font-weight: 500; background: transparent; box-shadow: none; }
.lsat-trap-feedback { flex-basis: 100%; margin-top: .4rem; color: var(--lsat-fg-subtle); font-size: .95em; }
/* identification-first classify stage */
.lsat-classify { margin-top: 1.15rem; }
.lsat-classify-chips { display: flex; gap: .45rem; flex-wrap: wrap; margin-top: .55rem; }
.lsat-classify-feedback { margin-top: .6rem; font-weight: 600; font-size: .95em; }
.lsat-classify-feedback.right { color: var(--lsat-good); }
.lsat-classify-feedback.wrong { color: var(--lsat-bad); }
/* elaborated contrast card (shown on a miss) */
.lsat-contrast { display: grid; grid-template-columns: 1fr 1fr; gap: .6rem; margin-top: 1.05rem; }
@media (max-width: 540px) { .lsat-contrast { grid-template-columns: 1fr; } }
.lsat-ct-col { display: flex; flex-direction: column; gap: .35rem; padding: .75rem .85rem;
  border: 1px solid var(--lsat-border); border-radius: var(--lsat-radius-sm);
  background: var(--lsat-surface); box-shadow: var(--lsat-shadow); font-size: .93em; line-height: 1.45; }
.lsat-ct-col.credited { border-color: var(--lsat-good-line); background: var(--lsat-good-soft); }
.lsat-ct-col.trap { border-color: var(--lsat-bad-line); background: var(--lsat-bad-soft); }
.lsat-ct-hd { font-weight: 700; font-size: .7em; text-transform: uppercase;
  letter-spacing: .04em; color: var(--lsat-fg-faint); }
.lsat-ct-col.credited .lsat-ct-hd { color: var(--lsat-good); }
.lsat-ct-col.trap .lsat-ct-hd { color: var(--lsat-bad); }
.lsat-ct-col p { margin: 0; color: var(--lsat-fg); }
.lsat-ct-tip { font-size: .85em; font-style: italic; color: var(--lsat-fg-subtle); }
@media (prefers-reduced-motion: reduce) {
  .lsat-item *, .lsat-item ::before, .lsat-item ::after { transition: none !important; }
}
</style>
<script>
(function () {
  var raw = document.getElementById("lsat-raw");
  var container = document.getElementById("lsat-choices");
  var confRow = document.getElementById("lsat-confidence");
  if (!raw || !container) return;
  container.innerHTML = "";
  var text = raw.textContent || "";
  var re = /(?:^|\n)[ \t]*\(([A-E])\)\s*([\s\S]*?)(?=\n[ \t]*\([A-E]\)|$)/g;
  var answered = false, graded = false, chosenLetter = null, identState = "", m;

  function highlight(res) {
    if (!res) return;
    // An item with no gradeable answer key is abstained server-side (graded:false,
    // nothing logged); don't mark a choice a false "wrong" -- leave it neutral and
    // let the normal reviewer controls advance.
    if (res.graded === false) return;
    var self = container.querySelector('.lsat-choice[data-letter="' + chosenLetter + '"]');
    if (self) self.classList.add(res.correct ? "right" : "wrong");
    if (!res.correct && res.correct_letter) {
      var ok = container.querySelector('.lsat-choice[data-letter="' + res.correct_letter + '"]');
      if (ok) ok.classList.add("right");
    }
    // Elaborated Contrast Card (DECISION-round2 #13): on a miss, why the credited
    // answer wins + why the picked letter is a trap (deterministic; AI-off).
    if (!res.correct && res.contrast && res.contrast.available) showContrast(res.contrast);
    // On a miss for an item with trap labels, ask which trap you fell for
    // (competitive retrieval + self-explanation; graded server-side).
    if (!res.correct && res.has_traps) showTrapTap();
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function showContrast(c) {
    var el = document.getElementById("lsat-contrast");
    if (!el) return;
    var html = "";
    if (c.why_credited) {
      html += '<div class="lsat-ct-col credited"><span class="lsat-ct-hd">Why the credited answer wins</span><p>' +
        esc(c.why_credited) + "</p></div>";
    }
    if (c.trap) {
      html += '<div class="lsat-ct-col trap"><span class="lsat-ct-hd">Why (' + esc(chosenLetter) +
        ") is a trap — " + esc(c.trap.label) + '</span><p>' + esc(c.trap.minimal_edit) +
        '</p><span class="lsat-ct-tip">Fixable habit: ' + esc(c.trap.tip) + "</span></div>";
    }
    if (!html) return;
    el.innerHTML = html;
    el.hidden = false;
  }
  function grade(conf) {
    if (graded) return;
    graded = true;
    if (confRow) confRow.hidden = true;
    pycmd("lsatAnswer:" + chosenLetter + (conf ? ":conf=" + conf : "") +
      (identState ? ":ident=" + identState : ""), highlight);
  }

  // Identification-first stage (SPOV 1 / A2): LR items must be classified
  // before the choices unlock; the grade rides the answer event as `ident`.
  // The chip list (node_id + label) is injected from the taxonomy at
  // notetype-creation time (see _item_qfmt) so EVERY scored LR question type is
  // offered -- a shipped item of any LR type can be identified correctly and
  // the ids match what lsat.grading.grade_classify compares against.
  var QTYPES = __LSAT_QTYPES_JSON__;
  var skillsEl = document.getElementById("lsat-skills");
  var classifyEl = document.getElementById("lsat-classify");
  var chipsEl = document.getElementById("lsat-classify-chips");
  var classifyFb = document.getElementById("lsat-classify-feedback");
  var isLR = /(^|\s)lr\./.test(skillsEl ? skillsEl.textContent || "" : "");

  function unlockChoices() {
    container.hidden = false;
  }
  function startClassify() {
    if (!classifyEl || !chipsEl || !isLR) { unlockChoices(); return; }
    var done = false;
    for (var q = 0; q < QTYPES.length; q++) {
      (function (id, label) {
        var cb = document.createElement("button");
        cb.type = "button"; cb.className = "lsat-conf-btn"; cb.textContent = label;
        cb.addEventListener("click", function () {
          if (done) return; done = true;
          var all = chipsEl.querySelectorAll(".lsat-conf-btn");
          for (var k = 0; k < all.length; k++) all[k].disabled = true;
          pycmd("lsatClassify:" + id, function (r) {
            if (r && r.actual_type) {
              identState = r.classify_correct ? "1" : "0";
              if (classifyFb) {
                classifyFb.textContent = r.classify_correct
                  ? "Yes \u2014 " + r.actual_label + "."
                  : "Actually this is a " + r.actual_label + " question.";
                classifyFb.className = "lsat-classify-feedback " +
                  (r.classify_correct ? "right" : "wrong");
                classifyFb.hidden = false;
              }
            }
            unlockChoices();
          });
        });
        chipsEl.appendChild(cb);
      })(QTYPES[q][0], QTYPES[q][1]);
    }
    classifyEl.hidden = false;
  }
  var TRAPS = [["out_of_scope", "Out of scope"], ["extreme_language", "Extreme language"],
    ["reversal", "Reversal"], ["half_right", "Half-right"],
    ["irrelevant_comparison", "Irrelevant comparison"]];
  var trapEl = document.getElementById("lsat-trap");
  function showTrapTap() {
    if (!trapEl) return;
    trapEl.innerHTML = '<span class="lsat-conf-label">Why is (' + chosenLetter + ') wrong?</span>';
    var done = false;
    for (var t = 0; t < TRAPS.length; t++) {
      (function (fam, label) {
        var tb = document.createElement("button");
        tb.type = "button"; tb.className = "lsat-conf-btn"; tb.textContent = label;
        tb.addEventListener("click", function () {
          if (done) return; done = true;
          var tbtns = trapEl.querySelectorAll(".lsat-conf-btn");
          for (var k = 0; k < tbtns.length; k++) tbtns[k].disabled = true;
          pycmd("lsatTrap:" + chosenLetter + ":" + fam, function (r) {
            var fb = document.createElement("div");
            fb.className = "lsat-trap-feedback";
            if (r && r.actual_label) {
              fb.textContent = (r.trap_correct ? "Yes \u2014 (" : "Actually (") +
                chosenLetter + ") is " + r.actual_label + ".";
            }
            trapEl.appendChild(fb);
          });
        });
        trapEl.appendChild(tb);
      })(TRAPS[t][0], TRAPS[t][1]);
    }
    trapEl.hidden = false;
  }

  while ((m = re.exec(text)) !== null) {
    if (!m[2].trim()) continue;
    var btn = document.createElement("button");
    btn.className = "lsat-choice";
    btn.type = "button";
    btn.setAttribute("data-letter", m[1]);
    btn.innerHTML = '<span class="lsat-letter">' + m[1] + "</span>" + m[2].trim();
    btn.addEventListener("click", function () {
      if (answered) return;
      answered = true;
      chosenLetter = this.getAttribute("data-letter");
      var all = container.querySelectorAll(".lsat-choice");
      for (var i = 0; i < all.length; i++) {
        all[i].classList.add("disabled");
        all[i].disabled = true;
      }
      this.classList.add("chosen");
      // Reveal the one-tap confidence rating; grading happens on that tap.
      if (confRow) { confRow.hidden = false; } else { grade(""); }
    });
    container.appendChild(btn);
  }

  if (confRow) {
    var cbtns = confRow.querySelectorAll(".lsat-conf-btn");
    for (var j = 0; j < cbtns.length; j++) {
      cbtns[j].addEventListener("click", function () {
        grade(this.getAttribute("data-conf") || "");
      });
    }
  }

  startClassify();
})();
</script>"""
# The answer side reveals the correct letter and disables the choice buttons
# (FrontSide re-runs the question script, so without this a click on the answer
# side would log a second event).
_ITEM_AFMT = (
    "{{FrontSide}}\n\n<hr id=answer>\n\n"
    '<div class="lsat-correct">Correct answer: <b>{{correct}}</b></div>\n'
    "<style>\n"
    ".lsat-correct { --c-good:#0f9d6a; --c-good-soft:rgba(15,157,106,.12);"
    " --c-good-line:rgba(15,157,106,.45); --c-fg:#101526;"
    ' --c-mono:ui-monospace,"SF Mono","SFMono-Regular",Menlo,Consolas,"Liberation Mono",monospace;'
    " display: block; max-width: 760px; margin: .7rem auto 0; padding: .65rem .9rem;"
    " border-radius: 11px; background: var(--c-good-soft); border: 1px solid var(--c-good-line);"
    " color: var(--c-fg); font-weight: 600;"
    ' font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif; }\n'
    '.lsat-correct::before { content:"\\22A2"; margin-right: .45rem;'
    " font-family: var(--c-mono); font-weight: 700; color: var(--c-good); }\n"
    ".lsat-correct b { font-family: var(--c-mono); color: var(--c-good); }\n"
    "@media (prefers-color-scheme: dark) { .lsat-correct { --c-good:#34d399;"
    " --c-good-soft:rgba(52,211,153,.15); --c-good-line:rgba(52,211,153,.5); --c-fg:#e8ebf2; } }\n"
    ".night-mode .lsat-correct, .nightMode .lsat-correct, .night_mode .lsat-correct {"
    " --c-good:#34d399; --c-good-soft:rgba(52,211,153,.15); --c-good-line:rgba(52,211,153,.5);"
    " --c-fg:#e8ebf2; }\n"
    "</style>\n"
    "<script>(function () {\n"
    "  // Answer side: skip the classify gate (reveal choices, hide the stage)\n"
    "  // and disable every control so nothing logs a second event.\n"
    '  var ch = document.getElementById("lsat-choices");\n'
    "  if (ch) ch.hidden = false;\n"
    '  var cl = document.getElementById("lsat-classify");\n'
    "  if (cl) cl.hidden = true;\n"
    '  var b = document.querySelectorAll(".lsat-choice, .lsat-conf-btn");\n'
    "  for (var i = 0; i < b.length; i++) {\n"
    '    b[i].disabled = true; b[i].classList.add("disabled");\n'
    "  }\n"
    "})();</script>"
)

# PerformanceEvent cards are never studied (suspended on creation); this template
# exists only because Anki requires at least one card template per notetype.
_EVENT_QFMT = "Event for item {{item_id}}"
_EVENT_AFMT = (
    "{{FrontSide}}\n<hr>\n"
    "skills: {{skill_tags}} | correct: {{correct}} | {{response_ms}} ms"
)

_SECTION_QFMT = "Timed section attempt ({{n_questions}} questions)"
_SECTION_AFMT = "{{FrontSide}}\n<hr>\nstarted: {{started_at_hlc}} | {{device_id}}"


def _classify_qtypes() -> list[tuple[str, str]]:
    """The LR question types offered as classify chips: ``(node_id, label)``.

    Sourced from the taxonomy (defect #9) rather than a hardcoded subset, so
    every scored LR question type is offered -- an item of any LR type can be
    identified correctly -- and the node ids match exactly what
    :func:`lsat.grading.grade_classify` compares the tapped chip against.
    """
    from lsat.taxonomy import load_taxonomy

    return [(t.id, t.name) for t in load_taxonomy().question_types_for("lr")]


def _item_qfmt() -> str:
    """The ``LSAT Item`` question template with the classify chips injected.

    The taxonomy's LR question types are serialized into the template's
    ``QTYPES`` JS array (``json.dumps`` -> a valid JS array literal, safely
    escaped) at notetype-creation time.
    """
    qtypes_js = json.dumps([[node_id, label] for node_id, label in _classify_qtypes()])
    return _ITEM_QFMT_TEMPLATE.replace("__LSAT_QTYPES_JSON__", qtypes_js)


# name -> (fields, [(template_name, qfmt, afmt)]). Built fresh (not a module
# constant) so the Item classify chips always reflect the current taxonomy.
def _specs() -> dict[str, tuple[list[str], list[tuple[str, str, str]]]]:
    return {
        LSAT_CARD: (CARD_FIELDS, [("Recall", _CARD_QFMT, _CARD_AFMT)]),
        LSAT_ITEM: (ITEM_FIELDS, [("Practice", _item_qfmt(), _ITEM_AFMT)]),
        LSAT_PERFORMANCE_EVENT: (EVENT_FIELDS, [("Log", _EVENT_QFMT, _EVENT_AFMT)]),
        LSAT_SECTION_ATTEMPT: (
            SECTION_FIELDS,
            [("Log", _SECTION_QFMT, _SECTION_AFMT)],
        ),
    }


def _build(
    col: Collection,
    name: str,
    fields: list[str],
    templates: list[tuple[str, str, str]],
) -> None:
    mm = col.models
    notetype = mm.new(name)
    for field_name in fields:
        mm.add_field(notetype, mm.new_field(field_name))
    for template_name, qfmt, afmt in templates:
        template = mm.new_template(template_name)
        template["qfmt"] = qfmt
        template["afmt"] = afmt
        mm.add_template(notetype, template)
    mm.add(notetype)


def _sync_templates(
    col: Collection,
    notetype: NotetypeDict,
    templates: list[tuple[str, str, str]],
) -> None:
    """Refresh an existing notetype's template HTML in place when it changed.

    Only the qfmt/afmt text is touched (a safe, non-schema change), so template
    improvements -- e.g. the Item answer-capture UI -- reach collections that
    were seeded before the change. No-op when the HTML already matches.
    """
    by_name = {t["name"]: t for t in notetype["tmpls"]}
    changed = False
    for template_name, qfmt, afmt in templates:
        tmpl = by_name.get(template_name)
        if tmpl is None:
            continue
        if tmpl["qfmt"] != qfmt or tmpl["afmt"] != afmt:
            tmpl["qfmt"] = qfmt
            tmpl["afmt"] = afmt
            changed = True
    if changed:
        col.models.update_dict(notetype)


def migrate_missing_fields(col: Collection, name: str, fields: list[str]) -> list[str]:
    """Add any of ``fields`` missing from notetype ``name``; return those added.

    ``ensure_notetypes`` never alters an existing notetype's field list (a
    schema change forces one full sync), so field additions go through here.
    Idempotent: a no-op once the fields exist. Batch related fields into one
    call so the full-sync cost is paid once.
    """
    notetype = col.models.by_name(name)
    if notetype is None:
        return []
    have = {f["name"] for f in notetype["flds"]}
    missing = [f for f in fields if f not in have]
    if not missing:
        return []
    for field_name in missing:
        col.models.add_field(notetype, col.models.new_field(field_name))
    col.models.update_dict(notetype)
    return missing


def migrate_item_fields(col: Collection) -> bool:
    """Ensure ``LSAT Item`` carries ``distractor_traps`` (idempotent)."""
    ensure_notetypes(col)
    return bool(migrate_missing_fields(col, LSAT_ITEM, ["distractor_traps"]))


def migrate_card_fields(col: Collection) -> bool:
    """Ensure ``LSAT Card`` carries ``primitive_type`` + ``topic_weight``
    (idempotent; batched into one schema change = one full sync)."""
    ensure_notetypes(col)
    return bool(
        migrate_missing_fields(col, LSAT_CARD, ["primitive_type", "topic_weight"])
    )


def ensure_notetypes(col: Collection) -> dict[str, int]:
    """Create any missing LSAT notetypes; return ``{name: notetype_id}``.

    Idempotent. A missing notetype is created; an existing one is left
    structurally untouched (adding/removing a field or template is a schema
    change), but its template HTML is refreshed to match the code.
    """
    ids: dict[str, int] = {}
    for name, (fields, templates) in _specs().items():
        existing = col.models.by_name(name)
        if existing is None:
            _build(col, name, fields, templates)
            existing = col.models.by_name(name)
        else:
            _sync_templates(col, existing, templates)
        assert existing is not None
        ids[name] = existing["id"]
    return ids
