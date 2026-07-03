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

_CARD_QFMT = "{{front}}"
_CARD_AFMT = (
    "{{FrontSide}}\n\n<hr id=answer>\n\n"
    "<b>{{back}}</b>\n\n"
    '<div class="lsat-explanation">{{explanation}}</div>'
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
.lsat-item { --lsat-accent:#2f6fed; --lsat-good:#1a8a3a; --lsat-bad:#c0392b;
  --lsat-line:rgba(128,128,128,.32); --lsat-soft:rgba(128,128,128,.08);
  max-width: 760px; margin: 0 auto; text-align: left; }
@media (prefers-color-scheme: dark) {
  .lsat-item { --lsat-accent:#6f9bff; --lsat-good:#37b364; --lsat-bad:#e2685d;
    --lsat-line:rgba(200,200,200,.28); --lsat-soft:rgba(255,255,255,.05); }
}
.lsat-stem { white-space: pre-wrap; font-size: 1.06em; line-height: 1.55; }
.lsat-choices { display: flex; flex-direction: column; gap: .5rem; margin-top: 1.1rem; }
.lsat-choice { display: flex; align-items: flex-start; gap: .65rem; text-align: left;
  min-height: 48px; padding: .7rem .85rem; border: 1px solid var(--lsat-line);
  border-radius: 12px; background: var(--lsat-soft); color: inherit; font: inherit;
  cursor: pointer; transition: border-color .18s ease, background .18s ease, transform .05s ease; }
.lsat-choice:hover:not(.disabled) { border-color: var(--lsat-accent); }
.lsat-choice:active:not(.disabled) { transform: translateY(1px); }
.lsat-choice.disabled { cursor: default; }
.lsat-choice.chosen { border-color: var(--lsat-accent); border-width: 2px; }
.lsat-choice.right { border-color: var(--lsat-good); background: rgba(26,138,58,.14); }
.lsat-choice.wrong { border-color: var(--lsat-bad); background: rgba(192,57,43,.14); }
.lsat-letter { display: inline-flex; align-items: center; justify-content: center;
  width: 1.7em; height: 1.7em; flex: 0 0 auto; border-radius: 50%; font-weight: 700;
  font-size: .85em; background: var(--lsat-accent); color: #fff; }
.lsat-confidence, .lsat-trap { display: flex; align-items: center; gap: .45rem;
  margin-top: .9rem; flex-wrap: wrap; }
.lsat-conf-label { opacity: .7; margin-right: .15rem; }
.lsat-conf-btn { min-height: 38px; padding: .4rem .8rem; border: 1px solid var(--lsat-line);
  border-radius: 999px; background: transparent; color: inherit; font: inherit;
  font-weight: 600; cursor: pointer; transition: border-color .18s ease; }
.lsat-conf-btn:hover:not(:disabled) { border-color: var(--lsat-accent); }
.lsat-conf-btn:disabled { opacity: .5; cursor: default; }
.lsat-conf-skip { opacity: .6; border-style: dashed; font-weight: 500; }
.lsat-trap-feedback { flex-basis: 100%; margin-top: .3rem; opacity: .9; }
.lsat-classify { margin-top: 1rem; }
.lsat-classify-chips { display: flex; gap: .4rem; flex-wrap: wrap; margin-top: .5rem; }
.lsat-classify-feedback { margin-top: .5rem; font-weight: 600; }
.lsat-classify-feedback.right { color: var(--lsat-good); }
.lsat-classify-feedback.wrong { color: var(--lsat-bad); }
.lsat-contrast { display: grid; grid-template-columns: 1fr 1fr; gap: .55rem; margin-top: .9rem; }
@media (max-width: 540px) { .lsat-contrast { grid-template-columns: 1fr; } }
.lsat-ct-col { display: flex; flex-direction: column; gap: .3rem; padding: .6rem .7rem;
  border: 1px solid var(--lsat-line); border-radius: 10px; font-size: .92em; line-height: 1.4; }
.lsat-ct-col.credited { border-color: var(--lsat-good); background: rgba(26,138,58,.10); }
.lsat-ct-col.trap { border-color: var(--lsat-bad); background: rgba(192,57,43,.10); }
.lsat-ct-hd { font-weight: 700; font-size: .72em; text-transform: uppercase;
  letter-spacing: .02em; opacity: .7; }
.lsat-ct-col p { margin: 0; }
.lsat-ct-tip { font-size: .82em; font-style: italic; opacity: .7; }
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
    "<style>.lsat-correct { max-width: 760px; margin: .6rem auto 0; padding: .55rem .8rem;"
    " border-radius: 10px; background: rgba(26,138,58,.14); color: inherit;"
    " border: 1px solid rgba(26,138,58,.5); font-weight: 600; }</style>\n"
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


# Valid values for the LSAT Card ``primitive_type`` field (SPOV 1 / A1).
PRIMITIVE_TYPES = ("diction", "logic", "qtype")


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
