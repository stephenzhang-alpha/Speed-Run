# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Authored content for the default LSAT decks (SPOV 1 / docs/Speedrun_AI_Features.md A1).

SPOV 1 -- "the LSAT is a knowledge test wearing a reasoning test's costume" --
defines the memorizable knowledge base as three *reasoning-primitive* families,
each a first-class deck so coverage, scheduling, and analytics slice by them:

- ``diction`` -- precise meanings of terms/connectives whose misreading costs
  working-memory capacity mid-passage (``some``, ``unless``, ``only if`` ...).
- ``logic``   -- formal-logic rules and the named-fallacy catalog (sufficient vs.
  necessary, contrapositive, causal/sampling/equivocation flaws ...).
- ``qtype``   -- the LR/RC question-type taxonomy and its prescribed attack,
  drilled identification-first (A2): show a stem cue, name the type.

Every taxonomy node in ``lsat-taxonomy.yaml`` gets at least one card here, so the
shipped deck covers ~100% of the primitive taxonomy (``lsat.primitives`` measures
this; the A3 give-up rule abstains from readiness when it is too thin).

All content is ORIGINAL -- authored for this project, never copied from LSAC
PrepTests or other copyrighted material (PRD section 16). Each card's FIRST
``skills`` entry is its family-defining node: ``seed.py`` derives the card's
``primitive_type`` and its destination deck from it, so the family a card teaches
and the deck it lands in can never drift apart.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# diction family -- precise connective/term meanings (primary skill: diction.*)
# ---------------------------------------------------------------------------
DICTION_CARDS: list[dict] = [
    {
        "front": (
            'On the LSAT, what does "some" mean, and does "Some lawyers are '
            'judges" tell you any lawyer is NOT a judge?'
        ),
        "back": "At least one (possibly all); no.",
        "explanation": (
            '"Some" = at least one, with no upper bound -- it is compatible with '
            '"all." Inferring "some are not" from "some are" is a classic '
            "quantifier error."
        ),
        "skills": ["diction.some", "skill.quantifier_logic"],
    },
    {
        "front": (
            'On the LSAT, what does "most" mean, and if most X are Y and most X '
            "are Z, must some single X be both Y and Z?"
        ),
        "back": "More than half (possibly all); yes.",
        "explanation": (
            '"Most" = strictly more than 50%, up to and including 100%. Two '
            '"most" claims about the same group must overlap: more than half plus '
            "more than half cannot fit without a shared member."
        ),
        "skills": ["diction.most", "skill.quantifier_logic"],
    },
    {
        "front": '"The picnic will be held unless it rains." Translate into if-then form.',
        "back": "If it does not rain, the picnic will be held.",
        "explanation": (
            '"A unless B" means "if not B, then A." The sentence does NOT claim '
            "rain guarantees cancellation -- only that no-rain guarantees the "
            "picnic."
        ),
        "skills": ["diction.unless", "skill.conditional_logic"],
    },
    {
        "front": '"You may enter only if you have a ticket." Which condition is the ticket?',
        "back": "Necessary (enter -> ticket).",
        "explanation": (
            '"Only if" introduces a necessary condition: entering guarantees you '
            "have a ticket, but a ticket does not guarantee entry. Reading it as "
            "sufficient is the reversal trap."
        ),
        "skills": ["diction.only_if", "skill.conditional_logic"],
    },
    {
        "front": (
            '"You pass if and only if you score at least 60." What TWO conditionals '
            'does "if and only if" assert?'
        ),
        "back": "pass -> scored >= 60 AND scored >= 60 -> pass (both directions).",
        "explanation": (
            '"If and only if" combines "if" (the condition is sufficient) with '
            '"only if" (it is also necessary), so the two terms are logically '
            "equivalent -- each guarantees the other (a biconditional)."
        ),
        "skills": ["diction.if_and_only_if", "skill.conditional_logic"],
    },
    {
        "front": (
            '"Each of the following, if true, supports the claim EXCEPT:" What is '
            "the credited answer's relationship to the claim?"
        ),
        "back": "It is the one choice that does NOT support the claim.",
        "explanation": (
            '"EXCEPT" inverts the call of the question: four choices share the '
            "stated property and the credited answer is the lone one that lacks "
            "it. Skimming past EXCEPT flips right and wrong."
        ),
        "skills": ["diction.except"],
    },
    {
        "front": (
            '"Few of the council members supported the plan." Roughly how many '
            "supported it, and what does this imply about the rest?"
        ),
        "back": "Very few did; MOST members did not support it.",
        "explanation": (
            'Unlike "a few" (which merely asserts some), "few" is quasi-negative: '
            "it stresses the small count and carries the implication that most "
            "did not. The two are not interchangeable."
        ),
        "skills": ["diction.few", "skill.quantifier_logic"],
    },
    {
        "front": (
            '"Aggressive drivers tend to cause more accidents." Does this rule out '
            "a careful driver who causes many accidents?"
        ),
        "back": "No -- it is a qualified/statistical claim, not a universal rule.",
        "explanation": (
            'Hedged language ("tends to," "typically," "generally") describes a '
            "trend with exceptions. Treating it as an absolute is the overreading "
            "that many strengthen/weaken traps exploit."
        ),
        "skills": ["diction.tends_to"],
    },
    {
        "front": (
            "Sort into SUFFICIENT-condition vs NECESSARY-condition markers: "
            '"if", "requires", "depends on", "guarantees", "only if", "ensures".'
        ),
        "back": (
            "Sufficient: if, guarantees, ensures. Necessary: requires, depends "
            "on, only if."
        ),
        "explanation": (
            'Sufficient markers ("if", "when", "guarantees", "ensures") name what '
            'triggers the result; necessary markers ("requires", "depends on", '
            '"only", "unless") name what the result cannot occur without. Mapping '
            "the word to the arrow direction is the core translation skill."
        ),
        "skills": [
            "diction.necessary_vs_sufficient_markers",
            "skill.conditional_logic",
        ],
    },
]

# ---------------------------------------------------------------------------
# logic family -- formal rules + named fallacies
# (primary skill: flaw.* or skill.conditional_logic / skill.quantifier_logic)
# ---------------------------------------------------------------------------
LOGIC_CARDS: list[dict] = [
    {
        "front": (
            "A town council notes that ever since it installed brighter "
            "streetlights, reported nighttime crime fell, and concludes the "
            "lights reduced crime. Identify the primary reasoning flaw."
        ),
        "back": "Correlation mistaken for causation (post hoc).",
        "explanation": (
            "A temporal association (crime fell after the lights went up) is "
            "treated as proof the lights caused the drop, without ruling out "
            "other causes such as extra patrols or fewer reports."
        ),
        "skills": ["flaw.causal", "lr.flaw"],
    },
    {
        "front": (
            '"Most employees we surveyed prefer remote work; therefore most '
            'employees in the country prefer remote work." Name the flaw.'
        ),
        "back": "Unrepresentative (biased) sample.",
        "explanation": (
            "The argument generalizes from a possibly non-representative "
            "subgroup to a much larger population."
        ),
        "skills": ["flaw.sampling", "lr.flaw"],
    },
    {
        "front": (
            "\"We should reject Dr. Lee's study on air quality -- she once worked "
            'for an oil company." Name the reasoning flaw.'
        ),
        "back": "Ad hominem (attacking the source, not the argument).",
        "explanation": (
            "The claim is rejected by impugning the person or her motives rather "
            "than the evidence. A source's bias is a reason to scrutinize, not by "
            "itself a reason the conclusion is false."
        ),
        "skills": ["flaw.ad_hominem", "lr.flaw"],
    },
    {
        "front": (
            '"A famous actor says this supplement cures colds, so it must work." '
            "Name the flaw."
        ),
        "back": "Inappropriate appeal to authority.",
        "explanation": (
            "The cited source has no relevant expertise (fame is not medical "
            "evidence). Appeals to authority fail when the authority is "
            "irrelevant, biased, or the field lacks consensus."
        ),
        "skills": ["flaw.appeal_to_authority", "lr.flaw"],
    },
    {
        "front": (
            '"Only man is rational, and no woman is a man, so no woman is '
            'rational." Name the flaw.'
        ),
        "back": "Equivocation (a key term shifts meaning).",
        "explanation": (
            '"Man" is used first as "human being" then as "male," so the premises '
            "are not about the same category. A term that changes sense mid-"
            "argument breaks the logical link."
        ),
        "skills": ["flaw.equivocation", "lr.flaw"],
    },
    {
        "front": (
            '"The senator is trustworthy because she says so, and a trustworthy '
            'person would not lie." Name the flaw.'
        ),
        "back": "Circular reasoning (begging the question).",
        "explanation": (
            "The conclusion (she is trustworthy) is assumed within the premises, "
            "so the argument offers no independent support -- it only restates "
            "what it set out to prove."
        ),
        "skills": ["flaw.circular", "lr.flaw"],
    },
    {
        "front": (
            '"Every player on the team is excellent, so the team is excellent." '
            "Name the flaw."
        ),
        "back": "Fallacy of composition (part -> whole).",
        "explanation": (
            "A property of the individual parts is assumed to transfer to the "
            "whole. Excellent players can still form a poor team (bad chemistry), "
            "so the inference is not guaranteed."
        ),
        "skills": ["flaw.composition", "lr.flaw"],
    },
    {
        "front": (
            '"This corporation is enormously wealthy, so its newest employee must '
            'be wealthy." Name the flaw.'
        ),
        "back": "Fallacy of division (whole -> part).",
        "explanation": (
            "A property of the whole is assumed to hold of each part -- the "
            "reverse of composition. The aggregate's wealth says nothing about "
            "any single member."
        ),
        "skills": ["flaw.division", "lr.flaw"],
    },
    {
        "front": (
            '"We either cut the budget or the company fails. We will not cut the '
            'budget, so the company will fail." Name the flaw.'
        ),
        "back": "False dichotomy (false dilemma).",
        "explanation": (
            "Only two options are presented as if exhaustive, ignoring "
            "alternatives (raise revenue, restructure). If a third path exists, "
            "the forced choice collapses."
        ),
        "skills": ["flaw.false_dichotomy", "lr.flaw"],
    },
    {
        "front": (
            '"If a contract is valid, it is signed. This contract is signed, so '
            'it is valid." Name the conditional-logic error.'
        ),
        "back": "Affirming the consequent.",
        "explanation": (
            "Being signed is necessary, not sufficient, for validity; affirming "
            "the necessary condition does not establish the sufficient one."
        ),
        "skills": [
            "flaw.affirming_consequent",
            "flaw.necessary_sufficient_confusion",
            "skill.conditional_logic",
        ],
    },
    {
        "front": (
            '"If it rains, the game is canceled. It did not rain, so the game was '
            'not canceled." Name the conditional-logic error.'
        ),
        "back": "Denying the antecedent.",
        "explanation": (
            "Rain is sufficient, not necessary, for cancellation -- the game "
            "could be canceled for other reasons. Negating the sufficient "
            "condition tells you nothing about the necessary one."
        ),
        "skills": ["flaw.denying_antecedent", "skill.conditional_logic", "lr.flaw"],
    },
    {
        "front": (
            '"Clinic A cured 90% of its patients and Clinic B only 60%, so Clinic '
            'A cured more people." Name the flaw.'
        ),
        "back": "Confusing a percentage with an absolute number.",
        "explanation": (
            "Without the patient counts the percentages do not fix the totals: "
            "if B treated ten times as many people, B cured far more. Rates and "
            "counts are different quantities."
        ),
        "skills": ["flaw.percentage_vs_number", "lr.flaw"],
    },
    {
        "front": (
            '"To win the scholarship you must volunteer. Maria volunteers, so she '
            'will win it." Name the flaw.'
        ),
        "back": "Confusing a necessary condition for a sufficient one.",
        "explanation": (
            "Volunteering is required (necessary) but not enough (sufficient) to "
            'win. Treating "you must have X" as "X guarantees it" is the '
            "necessary/sufficient confusion."
        ),
        "skills": [
            "flaw.necessary_sufficient_confusion",
            "skill.conditional_logic",
            "lr.flaw",
        ],
    },
    {
        "front": (
            '"My opponent wants to trim the military budget slightly. Clearly he '
            'wants to leave us defenseless." Name the flaw.'
        ),
        "back": "Straw man (misrepresenting the opposing view).",
        "explanation": (
            "The arguer distorts a modest position into an extreme one that is "
            "easier to attack, then refutes the distortion instead of the actual "
            "claim."
        ),
        "skills": ["flaw.straw_man", "lr.flaw"],
    },
    {
        "front": (
            '"No one has proven that the treatment is unsafe, so it must be safe." '
            "Name the flaw."
        ),
        "back": "Appeal to ignorance (absence of evidence as evidence).",
        "explanation": (
            "A lack of proof against a claim is not proof for it. Not-yet-"
            "disproven and demonstrated-true are different states; the burden of "
            "evidence is unmet."
        ),
        "skills": ["flaw.appeal_to_ignorance", "lr.flaw"],
    },
    {
        "front": 'Give the contrapositive of: "If a student passes, then they studied."',
        "back": "If a student did not study, then they did not pass.",
        "explanation": (
            "The contrapositive negates and swaps the terms: P -> S becomes "
            "not-S -> not-P, which is logically equivalent to the original."
        ),
        "skills": ["skill.conditional_logic"],
    },
    {
        "front": (
            "All poems are texts. Most poems are difficult. What, if anything, "
            "must be true about texts?"
        ),
        "back": "At least some texts are difficult.",
        "explanation": (
            '"Most poems are difficult" guarantees at least one difficult poem; '
            "since every poem is a text, that item is a difficult text. A "
            '"most" statement plus an "all" statement yields a valid "some" '
            "conclusion."
        ),
        "skills": ["skill.quantifier_logic"],
    },
]

# ---------------------------------------------------------------------------
# qtype family -- question-type identification, drilled identification-first
# (A2): show a characteristic stem cue, name the type. (primary: lr.* / rc.*)
# ---------------------------------------------------------------------------
QTYPE_CARDS: list[dict] = [
    # --- Logical Reasoning -------------------------------------------------
    {
        "front": (
            'A stem reads: "Which one of the following, if true, most undermines '
            'the argument?" Classify the question type.'
        ),
        "back": "Weaken.",
        "explanation": (
            '"Most undermines" / "casts the most doubt" / "calls into question" '
            "are characteristic Weaken cues."
        ),
        "skills": ["lr.weaken"],
    },
    {
        "front": (
            "A stem reads: \"The argument's conclusion depends on which one of "
            'the following assumptions?" Classify the question type.'
        ),
        "back": "Necessary Assumption.",
        "explanation": (
            '"Depends on" / "requires assuming" cue a Necessary Assumption '
            "question; the negation test confirms a candidate is required."
        ),
        "skills": ["lr.assumption_necessary", "skill.argument_parts"],
    },
    {
        "front": (
            'A stem reads: "The reasoning is most vulnerable to criticism on the '
            'grounds that it..." Classify the question type.'
        ),
        "back": "Flaw in the Reasoning.",
        "explanation": (
            '"Vulnerable to criticism," "questionable because," and "error in '
            'reasoning" are Flaw cues; the task is to name what the argument does '
            "wrong."
        ),
        "skills": ["lr.flaw"],
    },
    {
        "front": (
            'A stem reads: "If the statements above are true, which one of the '
            'following must also be true?" Classify the question type.'
        ),
        "back": "Inference / Must Be True.",
        "explanation": (
            '"Must also be true," "can be properly inferred," and "follows '
            'logically" signal Inference -- the answer must be fully proven by '
            "the stimulus."
        ),
        "skills": ["lr.inference_must_be_true"],
    },
    {
        "front": (
            'A stem reads: "Which one of the following, if true, most strengthens '
            'the argument?" Classify the question type.'
        ),
        "back": "Strengthen.",
        "explanation": (
            '"Most strengthens," "most supports," and "if true, most justifies" '
            "cue Strengthen -- add a fact that makes the conclusion more likely."
        ),
        "skills": ["lr.strengthen"],
    },
    {
        "front": (
            'A stem reads: "Which one of the following principles, if valid, most '
            'helps to justify the reasoning above?" Classify the question type.'
        ),
        "back": "Principle (Identify & Apply).",
        "explanation": (
            '"Principle," "conforms to which," and "proposition most helps to '
            'justify" mark Principle questions -- match a general rule to the '
            "specific case."
        ),
        "skills": ["lr.principle"],
    },
    {
        "front": (
            'A stem reads: "The conclusion follows logically if which one of the '
            'following is assumed?" Classify the question type.'
        ),
        "back": "Sufficient Assumption / Justify.",
        "explanation": (
            '"The conclusion follows if ... is assumed" / "justifies the '
            'reasoning" cue Sufficient Assumption -- find the premise that makes '
            "the argument valid, not merely one it needs."
        ),
        "skills": ["lr.assumption_sufficient", "skill.conditional_logic"],
    },
    {
        "front": (
            'A stem reads: "Which one of the following, if true, most helps to '
            'resolve the apparent discrepancy?" Classify the question type.'
        ),
        "back": "Resolve / Explain the Paradox.",
        "explanation": (
            '"Resolve," "explain the discrepancy," and "reconcile" cue Paradox -- '
            "find the fact that lets two seemingly conflicting statements both be "
            "true."
        ),
        "skills": ["lr.paradox"],
    },
    {
        "front": (
            'A stem reads: "The statements above, if true, most strongly support '
            'which one of the following?" Classify the question type.'
        ),
        "back": "Most Strongly Supported.",
        "explanation": (
            '"Most strongly supported by" runs from stimulus down to answer (like '
            "Inference), but the answer need only be well-supported, not airtight "
            "-- that is what separates it from Must Be True."
        ),
        "skills": ["lr.most_strongly_supported"],
    },
    {
        "front": (
            'A stem reads: "Which one of the following arguments is most similar '
            'in its pattern of reasoning to the argument above?" Classify the '
            "question type."
        ),
        "back": "Parallel Reasoning.",
        "explanation": (
            '"Most similar in its reasoning" / "pattern of reasoning most '
            'parallel" cue Parallel Reasoning -- match the abstract logical '
            "structure, not the topic."
        ),
        "skills": ["lr.parallel_reasoning"],
    },
    {
        "front": 'A stem reads: "The argument proceeds by..." Classify the question type.',
        "back": "Method of Reasoning / Argument.",
        "explanation": (
            '"Argument proceeds by," "technique of reasoning," and "responds by" '
            "cue Method -- describe HOW the argument is made, in the abstract, "
            "not whether it is any good."
        ),
        "skills": ["lr.method_of_reasoning", "skill.argument_parts"],
    },
    {
        "front": (
            'A stem reads: "Which one of the following most accurately expresses '
            'the main conclusion of the argument?" Classify the question type.'
        ),
        "back": "Main Conclusion.",
        "explanation": (
            '"Main conclusion" / "overall conclusion drawn" cue this '
            "identification task -- find the claim every other statement supports "
            "(watch for a sub-conclusion that is itself a premise for a further "
            "point)."
        ),
        "skills": ["lr.main_conclusion", "skill.argument_parts"],
    },
    {
        "front": (
            'A stem reads: "The claim that recycling saves money plays which one '
            'of the following roles in the argument?" Classify the question type.'
        ),
        "back": "Role in Argument.",
        "explanation": (
            '"Plays which role," "figures in the argument," and "serves to" cue '
            "Role -- state how one specific statement functions (premise, sub-"
            "conclusion, main conclusion, or counter-point)."
        ),
        "skills": ["lr.role_in_argument", "skill.argument_parts"],
    },
    {
        "front": (
            'A stem reads: "Which one of the following exhibits a flawed pattern '
            'of reasoning most similar to that in the argument above?" Classify '
            "the question type."
        ),
        "back": "Parallel Flaw.",
        "explanation": (
            "Like Parallel Reasoning, but the stimulus is flawed -- match the "
            'SAME error\'s structure. "Flawed pattern of reasoning most similar" '
            "is the cue."
        ),
        "skills": ["lr.parallel_flaw"],
    },
    {
        "front": (
            'A stem reads: "Marco and Lena are committed to disagreeing about '
            'which one of the following?" Classify the question type.'
        ),
        "back": "Point at Issue / Agreement.",
        "explanation": (
            '"Disagree about whether," "committed to disagreeing," and "point at '
            'issue" cue this two-speaker type -- find the claim one endorses and '
            "the other denies."
        ),
        "skills": ["lr.point_at_issue"],
    },
    {
        "front": (
            'A stem reads: "The answer to which one of the following would be most '
            'useful to know in evaluating the argument?" Classify the question '
            "type."
        ),
        "back": "Evaluate the Argument.",
        "explanation": (
            '"Most useful to know in evaluating" / "most relevant to evaluating" '
            "cue Evaluate -- pick the question whose answer would strengthen or "
            "weaken the argument depending on how it comes out."
        ),
        "skills": ["lr.evaluate"],
    },
    {
        "front": (
            'A stem reads: "If the statements above are true, which one of the '
            'following CANNOT be true?" Classify the question type.'
        ),
        "back": "Cannot Be True.",
        "explanation": (
            '"Cannot be true" inverts Must Be True -- the credited answer is '
            "impossible given the stimulus, while every wrong answer could be "
            "true."
        ),
        "skills": ["lr.cannot_be_true"],
    },
    # --- Reading Comprehension --------------------------------------------
    {
        "front": (
            'An RC stem reads: "The passage suggests that the author would be '
            'most likely to agree with which one of the following?" Classify the '
            "RC question type."
        ),
        "back": "Inference.",
        "explanation": (
            '"The passage suggests," "most likely to agree," and "can be '
            'inferred" cue RC Inference -- support the answer from what the '
            "passage implies, not only what it states outright."
        ),
        "skills": ["rc.inference"],
    },
    {
        "front": (
            'An RC stem reads: "According to the passage, the researchers '
            'observed which one of the following?" Classify the RC question type.'
        ),
        "back": "Specific Detail / Lookup.",
        "explanation": (
            '"According to the passage," "the passage states," and "the author '
            'mentions" cue a Detail question -- the answer is stated directly; go '
            "find it."
        ),
        "skills": ["rc.specific_detail"],
    },
    {
        "front": (
            'An RC stem reads: "Which one of the following most accurately states '
            'the main point of the passage?" Classify the RC question type.'
        ),
        "back": "Main Point / Primary Purpose.",
        "explanation": (
            '"Main point," "primary purpose," and "central idea" cue this whole-'
            "passage question -- capture the thesis, not one paragraph's detail."
        ),
        "skills": ["rc.main_point_purpose", "skill.rc_structural_reading"],
    },
    {
        "front": (
            'An RC stem reads: "The author mentions the 1918 census most likely '
            'in order to..." Classify the RC question type.'
        ),
        "back": "Function / Role of a Statement.",
        "explanation": (
            '"In order to," "the function of the reference to," and "why the '
            'author mentions" cue Function -- explain WHY a detail is included, '
            "i.e., its role in the passage."
        ),
        "skills": ["rc.function_role", "skill.rc_structural_reading"],
    },
    {
        "front": (
            "An RC stem reads: \"The author's attitude toward the new policy is "
            'best described as..." Classify the RC question type.'
        ),
        "back": "Author's Attitude / Tone.",
        "explanation": (
            '"Attitude toward," "the author\'s tone," and "would most likely '
            "regard\" cue Attitude -- gauge the author's stance and its intensity "
            "from word choice."
        ),
        "skills": ["rc.attitude_tone", "skill.rc_structural_reading"],
    },
    {
        "front": (
            'An RC stem reads: "Which one of the following, if true, would most '
            "weaken the author's argument in the second paragraph?\" Classify the "
            "RC question type."
        ),
        "back": "Strengthen / Weaken (RC).",
        "explanation": (
            'RC borrows the LR skill: "would most strengthen/weaken" and "if '
            "true, would most support the author.\" Apply the passage's argument "
            "to a new fact from outside the text."
        ),
        "skills": ["rc.strengthen_weaken_rc"],
    },
    {
        "front": (
            'An RC stem reads: "Which one of the following most accurately '
            'describes the organization of the passage?" Classify the RC '
            "question type."
        ),
        "back": "Structure / Organization.",
        "explanation": (
            '"Organized in which," "how the passage proceeds," and "the structure '
            'of the passage" cue Structure -- map the sequence of moves (e.g., '
            "claim, objection, rebuttal)."
        ),
        "skills": ["rc.structure_organization", "skill.rc_structural_reading"],
    },
    {
        "front": (
            'An RC stem reads: "Which one of the following is most analogous to '
            'the method described in the passage?" Classify the RC question type.'
        ),
        "back": "Application / Analogy.",
        "explanation": (
            '"Most analogous," "situation most similar," and "to which would the '
            "author's reasoning apply\" cue Application -- transfer the passage's "
            "idea to a new scenario."
        ),
        "skills": ["rc.application_analogy"],
    },
    {
        "front": (
            'An RC stem reads: "The author of Passage B would most likely respond '
            'to the argument in Passage A by..." Classify the RC question type.'
        ),
        "back": "Comparative (Dual-Passage Relationship).",
        "explanation": (
            '"Both passages," "Passage A and Passage B," and "the author of B '
            'would respond" cue the Comparative set -- track where the two '
            "authors agree, differ, and address each other."
        ),
        "skills": ["rc.comparative_dual_passage"],
    },
]

# The three families concatenated: the full default drill deck. Order is
# diction -> logic -> qtype; ``seed.py`` routes each card to its family deck by
# its first skill, so this stays a flat, easily-scanned list.
SEED_CARDS: list[dict] = [*DICTION_CARDS, *LOGIC_CARDS, *QTYPE_CARDS]

# ---------------------------------------------------------------------------
# Graded practice items (LSAT Item) -- the performance signal (SPOV 1:
# necessary != sufficient). ``distractor_traps`` labels each wrong choice with a
# skill.trap.* family so the Distractor-Reasoning Engine can attribute a miss and
# grade the "which trap got you?" tap (lsat/notetypes.py, lsat/error_patterns.py).
# ---------------------------------------------------------------------------
PRACTICE_ITEMS: list[dict] = [
    {
        "stem": (
            "Nutritionist: People who eat breakfast weigh less on average than "
            "those who skip it. So eating breakfast must help control weight.\n\n"
            "Which one of the following, if true, most weakens the argument?"
        ),
        "choices": (
            "(A) Some people who skip breakfast exercise regularly.\n"
            "(B) People who skip breakfast tend to snack much more later in the "
            "day, consuming more total calories for reasons unrelated to "
            "breakfast itself.\n"
            "(C) Breakfast foods vary widely in calorie content.\n"
            "(D) The study measured each participant's weight only once.\n"
            "(E) Many people say they enjoy eating breakfast."
        ),
        "correct": "B",
        "difficulty": "medium",
        "skills": ["lr.weaken", "flaw.causal"],
        "distractor_traps": "A=out_of_scope C=out_of_scope D=half_right E=out_of_scope",
    },
    {
        "stem": (
            "Editorial: If a city raises transit fares, ridership declines. "
            "Riverton did not raise fares last year. So Riverton's ridership "
            "did not decline.\n\nThe argument is most vulnerable to criticism "
            "on the grounds that it"
        ),
        "choices": (
            "(A) treats a fare increase as the only possible cause of declining "
            "ridership, confusing a sufficient condition for a necessary one.\n"
            "(B) relies on an unrepresentative sample of cities.\n"
            "(C) draws a conclusion about every city from a single case.\n"
            "(D) assumes the very point it is trying to establish.\n"
            "(E) appeals to an authority with no relevant expertise."
        ),
        "correct": "A",
        "difficulty": "medium",
        "skills": [
            "lr.flaw",
            "flaw.necessary_sufficient_confusion",
            "skill.conditional_logic",
        ],
        "distractor_traps": "B=out_of_scope C=out_of_scope D=out_of_scope E=out_of_scope",
    },
    {
        "stem": (
            "Critic: This novel cannot be great literature, because its author "
            "wrote it merely to make money.\n\nThe reasoning is most vulnerable "
            "to criticism because it"
        ),
        "choices": (
            "(A) generalizes from an unrepresentative sample.\n"
            "(B) attacks the author's motive instead of addressing the merits "
            "of the work.\n"
            "(C) mistakes a correlation for a cause.\n"
            "(D) relies on a term used in two different senses.\n"
            "(E) presents only two options when others are available."
        ),
        "correct": "B",
        "difficulty": "easy",
        "skills": ["lr.flaw", "flaw.ad_hominem"],
        "distractor_traps": "A=out_of_scope C=out_of_scope D=out_of_scope E=out_of_scope",
    },
    {
        "stem": (
            "Researcher: Every plant in our greenhouse that received the new "
            "fertilizer grew taller than average, so the fertilizer causes "
            "taller growth.\n\nWhich one of the following, if true, most "
            "strengthens the argument?"
        ),
        "choices": (
            "(A) The greenhouse was warmer than usual that season.\n"
            "(B) An otherwise-identical control group of plants that did not "
            "receive the fertilizer grew only to average height under the same "
            "conditions.\n"
            "(C) The fertilizer is inexpensive to produce.\n"
            "(D) Some treated plants grew much taller than other treated plants.\n"
            "(E) The researcher has studied plant growth for many years."
        ),
        "correct": "B",
        "difficulty": "medium",
        "skills": ["lr.strengthen", "flaw.causal"],
        "distractor_traps": "A=out_of_scope C=out_of_scope D=irrelevant_comparison E=out_of_scope",
    },
    {
        "stem": (
            "Columnist: Since the city installed protected bike lanes downtown, "
            "downtown traffic accidents have fallen sharply. To make the suburbs "
            "safer, the city should install the same lanes there.\n\nThe argument "
            "depends on assuming which one of the following?"
        ),
        "choices": (
            "(A) The bike lanes, rather than some other change, were responsible "
            "for the decline in downtown accidents.\n"
            "(B) Suburban residents bicycle as often as downtown residents do.\n"
            "(C) Protected bike lanes are the most cost-effective safety measure "
            "available.\n"
            "(D) Downtown traffic accidents have fallen to zero.\n"
            "(E) The suburbs currently have more traffic accidents than downtown "
            "does."
        ),
        "correct": "A",
        "difficulty": "medium",
        "skills": ["lr.assumption_necessary", "flaw.causal", "skill.argument_parts"],
        "distractor_traps": "B=out_of_scope C=extreme_language D=extreme_language E=irrelevant_comparison",
    },
    {
        "stem": (
            "Every student in the seminar has read either Kant or Hume. No "
            "student who has read Hume has read Kant. Rosa is a student in the "
            "seminar who has read Kant.\n\nIf the statements above are true, "
            "which one of the following must be true?"
        ),
        "choices": (
            "(A) Rosa has not read Hume.\n"
            "(B) Rosa has read both Kant and Hume.\n"
            "(C) Some students in the seminar have read neither Kant nor Hume.\n"
            "(D) Most students in the seminar have read Hume.\n"
            "(E) No student in the seminar other than Rosa has read Kant."
        ),
        "correct": "A",
        "difficulty": "medium",
        "skills": ["lr.inference_must_be_true", "skill.conditional_logic"],
        "distractor_traps": "B=reversal C=out_of_scope D=out_of_scope E=extreme_language",
    },
    {
        "stem": (
            "A new medication reliably lowers blood pressure in laboratory "
            "tests. Yet patients who were prescribed it showed no average "
            "decrease in blood pressure over the following year.\n\nWhich one of "
            "the following, if true, most helps to explain the discrepancy?"
        ),
        "choices": (
            "(A) The medication is more expensive than existing treatments.\n"
            "(B) Many patients prescribed the medication stopped taking it "
            "within weeks because of unpleasant side effects.\n"
            "(C) The laboratory tests were conducted by the medication's "
            "manufacturer.\n"
            "(D) Blood pressure is also influenced by diet and exercise.\n"
            "(E) A few patients' blood pressure rose slightly during the year."
        ),
        "correct": "B",
        "difficulty": "medium",
        "skills": ["lr.paradox"],
        "distractor_traps": "A=out_of_scope C=out_of_scope D=out_of_scope E=half_right",
    },
    {
        "stem": (
            "Principle: A person should not be blamed for a harmful outcome that "
            "they could not reasonably have foreseen.\n\nWhich one of the "
            "following judgments conforms most closely to the principle above?"
        ),
        "choices": (
            "(A) A pharmacist who knowingly dispensed an expired drug is not at "
            "fault when a patient is harmed.\n"
            "(B) A driver obeying every traffic law is not to blame when a child "
            "suddenly darts out from behind a parked truck and is injured.\n"
            "(C) A chef is blameless for a diner's allergic reaction even though "
            "the menu failed to list a well-known allergen.\n"
            "(D) A contractor who ignored the building code is not responsible "
            "for the structure's later collapse.\n"
            "(E) A babysitter who left a toddler alone by a pool is not at fault "
            "for the resulting accident."
        ),
        "correct": "B",
        "difficulty": "medium",
        "skills": ["lr.principle"],
        "distractor_traps": "A=reversal C=half_right D=reversal E=reversal",
    },
    {
        "stem": (
            "Historians once treated the diaries of ordinary soldiers as "
            "unreliable footnotes to official military records. Recent "
            "scholarship reverses this hierarchy: because official reports were "
            "written to justify decisions to superiors, they systematically omit "
            "confusion, fear, and error, whereas private diaries, written for no "
            "audience, preserve exactly those features. The diaries are not free "
            "of distortion -- memory and self-regard shape them too -- but their "
            "distortions run in different directions from those of the official "
            "record, and it is the comparison of the two, not the triumph of "
            "either, that yields the fullest account.\n\nWhich one of the "
            "following most accurately expresses the main point of the passage?"
        ),
        "choices": (
            "(A) Official military records are worthless as historical "
            "evidence.\n"
            "(B) Soldiers' diaries are free of the distortions that mar official "
            "records.\n"
            "(C) The fullest historical account comes from comparing soldiers' "
            "diaries against official records, because each distorts in "
            "different ways.\n"
            "(D) Historians should abandon official records in favor of private "
            "diaries.\n"
            "(E) Memory and self-regard make all first-person accounts equally "
            "unreliable."
        ),
        "correct": "C",
        "difficulty": "medium",
        "skills": ["rc.main_point_purpose", "skill.rc_structural_reading"],
        "distractor_traps": "A=extreme_language B=extreme_language D=extreme_language E=half_right",
    },
    {
        "stem": (
            "Wildlife biologist: In the years since the county reintroduced "
            "beavers to Elm Creek, the number of songbird species nesting along "
            "the creek has more than doubled. Clearly, the beavers' dams are "
            "responsible for attracting the additional songbirds.\n\nWhich one of "
            "the following, if true, most weakens the argument?"
        ),
        "choices": (
            "(A) Beaver dams create ponds that support the insects and shrubs on "
            "which many songbird species depend.\n"
            "(B) During the same period, the county banned a pesticide that had "
            "been killing the insects the songbirds feed on, and insect "
            "populations along the creek surged.\n"
            "(C) The beaver population along Elm Creek is expected to keep "
            "growing for several more years.\n"
            "(D) Some of the songbird species now nesting along Elm Creek can "
            "also be found along nearby creeks that have no beavers.\n"
            "(E) The county spent more on the beaver reintroduction than on any "
            "other conservation project that year."
        ),
        "correct": "B",
        "difficulty": "medium",
        "skills": ["lr.weaken", "flaw.causal"],
        "distractor_traps": "A=reversal C=out_of_scope D=irrelevant_comparison E=out_of_scope",
    },
    {
        "stem": (
            "Talent-agency director: To learn whether our new online audition "
            "portal is easier to use than the old in-person process, we emailed "
            "a survey to every actor who submitted an audition through the portal "
            "last month. Ninety percent rated the portal easy to use. The portal "
            "is therefore easier for actors to use than the in-person process "
            "was.\n\nWhich one of the following, if true, most weakens the "
            "argument?"
        ),
        "choices": (
            "(A) The old in-person process required actors to travel to the "
            "agency's downtown office during weekday business hours.\n"
            "(B) Many actors who tried the portal found it so confusing that they "
            "gave up without submitting an audition, and so were never sent the "
            "survey.\n"
            "(C) A few of the actors who rated the portal easy to use had "
            "previously used similar portals at other agencies.\n"
            "(D) The agency received more total auditions last month than in any "
            "previous month.\n"
            "(E) The survey let actors rate the portal as easy, moderate, or "
            "difficult to use."
        ),
        "correct": "B",
        "difficulty": "hard",
        "skills": ["lr.weaken", "flaw.sampling"],
        "distractor_traps": "A=reversal C=out_of_scope D=out_of_scope E=out_of_scope",
    },
    {
        "stem": (
            "Gardener: I planted marigolds around my vegetable beds this spring, "
            "and for the first time in years aphids did not infest my tomatoes. "
            "The marigolds must have kept the aphids away.\n\nWhich one of the "
            "following, if true, most strengthens the gardener's argument?"
        ),
        "choices": (
            "(A) Marigolds produce bright flowers that many gardeners find "
            "attractive.\n"
            "(B) Aphids are repelled by a chemical that marigolds release into "
            "the surrounding soil and air.\n"
            "(C) This spring the gardener also switched to a tomato variety "
            "specially bred to resist aphids.\n"
            "(D) Marigolds can be grown either from seed or from nursery "
            "seedlings.\n"
            "(E) Aphid populations throughout the region were much lower this "
            "spring than in previous years."
        ),
        "correct": "B",
        "difficulty": "easy",
        "skills": ["lr.strengthen", "flaw.causal"],
        "distractor_traps": "A=out_of_scope C=reversal D=out_of_scope E=reversal",
    },
    {
        "stem": (
            "Agricultural economist: Farms that adopted the new drip-irrigation "
            "system last year used 30 percent less water than comparable farms "
            "that kept their old sprinkler systems. So farms that switch to drip "
            "irrigation can expect to cut their water use substantially.\n\nWhich "
            "one of the following, if true, most strengthens the economist's "
            "argument?"
        ),
        "choices": (
            "(A) In the year before the switch, the farms that later adopted "
            "drip irrigation had used about the same amount of water per acre as "
            "the comparison farms.\n"
            "(B) Drip-irrigation systems are more expensive to install than "
            "sprinkler systems are.\n"
            "(C) The farms that adopted drip irrigation grew crops that naturally "
            "require less water than the crops grown on the comparison farms.\n"
            "(D) Water prices in the region are expected to rise sharply over the "
            "next decade.\n"
            "(E) Drip-irrigation systems must be inspected regularly to keep "
            "their emitters from clogging."
        ),
        "correct": "A",
        "difficulty": "medium",
        "skills": ["lr.strengthen", "skill.argument_parts", "flaw.causal"],
        "distractor_traps": "B=out_of_scope C=reversal D=out_of_scope E=out_of_scope",
    },
    {
        "stem": (
            "Cafe owner: Ever since we began playing classical music in the "
            "dining room, customers have lingered longer over their meals. "
            "Lingering customers order more coffee and dessert, so switching to "
            "classical music will increase our revenue.\n\nThe argument depends "
            "on assuming which one of the following?"
        ),
        "choices": (
            "(A) The additional coffee and dessert orders from lingering "
            "customers will not be outweighed by revenue lost because fewer new "
            "customers can be seated.\n"
            "(B) Classical music is more popular with the cafe's customers than "
            "any other kind of music is.\n"
            "(C) Playing classical music is the only way to get customers to "
            "linger longer over their meals.\n"
            "(D) Most other cafes in the area do not play classical music in "
            "their dining rooms.\n"
            "(E) The cafe's coffee and desserts are more profitable than its "
            "main dishes."
        ),
        "correct": "A",
        "difficulty": "medium",
        "skills": ["lr.assumption_necessary", "skill.argument_parts"],
        "distractor_traps": "B=extreme_language C=extreme_language D=out_of_scope E=out_of_scope",
    },
    {
        "stem": (
            "Archaeologist: The pottery fragments we unearthed at the Highfield "
            "site bear a glaze that was produced only by the Vantar civilization. "
            "The Vantar are known to have traded their pottery widely. "
            "Nonetheless, we can conclude that the Highfield site was once a "
            "Vantar settlement.\n\nThe argument depends on assuming which one of "
            "the following?"
        ),
        "choices": (
            "(A) The Highfield site contains no artifacts made by any "
            "civilization other than the Vantar.\n"
            "(B) The people who left the pottery at the Highfield site did not "
            "obtain it through trade with the Vantar.\n"
            "(C) The Vantar produced more pottery than any other civilization of "
            "their era.\n"
            "(D) Pottery is the most durable kind of artifact that the Vantar "
            "left behind.\n"
            "(E) Every known Vantar settlement contains pottery bearing the "
            "distinctive glaze."
        ),
        "correct": "B",
        "difficulty": "hard",
        "skills": ["lr.assumption_necessary", "skill.argument_parts"],
        "distractor_traps": "A=extreme_language C=out_of_scope D=out_of_scope E=reversal",
    },
    {
        "stem": (
            "Loan officer: Any applicant who has both a steady income and a "
            "strong credit history should have their loan approved. Ms. Alvarez "
            "has a steady income. Therefore, her loan should be approved.\n\nThe "
            "conclusion follows logically if which one of the following is "
            "assumed?"
        ),
        "choices": (
            "(A) Ms. Alvarez has a strong credit history.\n"
            "(B) Any applicant who has a strong credit history has a steady "
            "income.\n"
            "(C) Most applicants who have a steady income also have a strong "
            "credit history.\n"
            "(D) Ms. Alvarez has never missed a payment on any previous loan.\n"
            "(E) No applicant who lacks a steady income should have their loan "
            "approved."
        ),
        "correct": "A",
        "difficulty": "medium",
        "skills": ["lr.assumption_sufficient", "skill.conditional_logic"],
        "distractor_traps": "B=reversal C=half_right D=out_of_scope E=out_of_scope",
    },
    {
        "stem": (
            "A feather is light. Nothing that is light is dark. So no feather is "
            "dark.\n\nThe reasoning above is most vulnerable to criticism on the "
            "grounds that it"
        ),
        "choices": (
            '(A) depends on using the word "light" in two distinct senses.\n'
            "(B) takes a property of a whole to be a property of each of its "
            "parts.\n"
            "(C) treats a claim that is only sometimes true as though it were "
            "always true.\n"
            "(D) infers from the fact that most feathers are pale that all "
            "feathers are pale.\n"
            "(E) assumes without warrant that an object can have only one color."
        ),
        "correct": "A",
        "difficulty": "easy",
        "skills": ["lr.flaw", "flaw.equivocation"],
        "distractor_traps": "B=out_of_scope C=out_of_scope D=out_of_scope E=out_of_scope",
    },
    {
        "stem": (
            "Ensemble manager: Each of the five musicians we are recruiting is "
            "the best in the world at his or her instrument. So the ensemble we "
            "form from them will be the best ensemble in the world.\n\nThe "
            "reasoning above is flawed because it"
        ),
        "choices": (
            "(A) assumes that a group must have a given property merely because "
            "each of its members has that property.\n"
            "(B) relies on the testimony of a person who has an interest in the "
            "outcome.\n"
            "(C) takes for granted that no other ensemble is trying to recruit "
            "the same musicians.\n"
            "(D) confuses being the best at an instrument with being the most "
            "famous player of it.\n"
            "(E) draws a conclusion about all ensembles from the example of a "
            "single ensemble."
        ),
        "correct": "A",
        "difficulty": "medium",
        "skills": ["lr.flaw", "flaw.composition"],
        "distractor_traps": "B=out_of_scope C=out_of_scope D=out_of_scope E=out_of_scope",
    },
    {
        "stem": (
            "At the Fairmont Conservatory, every student who studies composition "
            "also studies music theory. No student who studies jazz studies "
            "music theory. Dev is a student at the conservatory who studies "
            "composition.\n\nIf the statements above are true, which one of the "
            "following must be true?"
        ),
        "choices": (
            "(A) Dev studies music theory but does not study jazz.\n"
            "(B) Dev studies jazz in addition to composition.\n"
            "(C) Every student who studies music theory also studies "
            "composition.\n"
            "(D) Some students at the conservatory study neither composition nor "
            "music theory.\n"
            "(E) Most students at the conservatory study music theory."
        ),
        "correct": "A",
        "difficulty": "medium",
        "skills": ["lr.inference_must_be_true", "skill.conditional_logic"],
        "distractor_traps": "B=reversal C=reversal D=out_of_scope E=out_of_scope",
    },
    {
        "stem": (
            "Every member of the Drayton hiking club has climbed Mount Corliss. "
            "Most members of the club have also climbed Mount Baird. Some members "
            "of the club are professional guides.\n\nIf the statements above are "
            "true, which one of the following must be true?"
        ),
        "choices": (
            "(A) Most members of the club have climbed both Mount Corliss and "
            "Mount Baird.\n"
            "(B) Everyone who has climbed Mount Baird is a professional guide.\n"
            "(C) Some professional guides have climbed Mount Baird.\n"
            "(D) Most professional guides have climbed Mount Corliss.\n"
            "(E) Every member who has climbed Mount Corliss has also climbed "
            "Mount Baird."
        ),
        "correct": "A",
        "difficulty": "hard",
        "skills": ["lr.inference_must_be_true", "skill.quantifier_logic"],
        "distractor_traps": "B=out_of_scope C=half_right D=out_of_scope E=extreme_language",
    },
    {
        "stem": (
            "Principle: A public official may accept a gift only if doing so "
            "would not lead a reasonable citizen to doubt the official's "
            "impartiality.\n\nWhich one of the following judgments conforms most "
            "closely to the principle above?"
        ),
        "choices": (
            "(A) Mayor Chen declined a luxury vacation offered by a developer "
            "whose rezoning application was awaiting her vote, reasoning that "
            "accepting it would lead reasonable citizens to doubt her "
            "impartiality.\n"
            "(B) Council member Ortiz accepted an expensive watch from a "
            "lobbyist who was seeking his vote on a pending bill, because the two "
            "had been close friends for years.\n"
            "(C) Judge Ramos refused a modest thank-you card from a school group "
            "that had no case before her court, on the ground that a judge should "
            "never accept anything from members of the public.\n"
            "(D) Governor Pike accepted a large campaign donation from an "
            "industry group and later voted for the very regulations the group "
            "had opposed.\n"
            "(E) Auditor Vance accepted free concert tickets from a company she "
            "was in the middle of auditing, judging that the tickets were too "
            "inexpensive to matter."
        ),
        "correct": "A",
        "difficulty": "medium",
        "skills": ["lr.principle", "skill.conditional_logic"],
        "distractor_traps": "B=reversal C=extreme_language D=out_of_scope E=half_right",
    },
    {
        "stem": (
            "Coach: If a swimmer trains every morning, she will qualify for the "
            "regional meet. Nadia did not qualify for the regional meet. So Nadia "
            "did not train every morning.\n\nWhich one of the following arguments "
            "is most similar in its reasoning to the argument above?"
        ),
        "choices": (
            "(A) If a student reads all the assigned chapters, he will pass the "
            "quiz. Tomas passed the quiz. So Tomas read all the assigned "
            "chapters.\n"
            "(B) If a bridge is well maintained, it will not corrode. The old "
            "trestle was not well maintained. So the old trestle will corrode.\n"
            "(C) If a bakery uses fresh yeast, its bread will rise properly. This "
            "morning's loaves did not rise properly. So the bakery did not use "
            "fresh yeast.\n"
            "(D) If a car passes inspection, it is roadworthy. This car passed "
            "inspection. So this car is roadworthy.\n"
            "(E) Most of the houses on Elm Street have brick facades. The Corwin "
            "house is on Elm Street. So the Corwin house probably has a brick "
            "facade."
        ),
        "correct": "C",
        "difficulty": "medium",
        "skills": ["lr.parallel_reasoning", "skill.conditional_logic"],
        "distractor_traps": "A=reversal B=reversal D=out_of_scope E=out_of_scope",
    },
    {
        "stem": (
            "Critic: No film shot in under three weeks can be a masterpiece; "
            "great films require time.\n\nDirector: That is false. The film "
            "Autumn Light was shot in just eleven days, yet it is widely regarded "
            "as one of the greatest films ever made.\n\nThe director responds to "
            "the critic's claim by"
        ),
        "choices": (
            "(A) presenting a counterexample to the critic's general claim.\n"
            "(B) attacking the critic's motives rather than the critic's claim.\n"
            "(C) redefining a key term that the critic had used.\n"
            "(D) appealing to the opinion of a recognized authority.\n"
            "(E) showing that the critic's claim leads to a contradiction."
        ),
        "correct": "A",
        "difficulty": "easy",
        "skills": ["lr.method_of_reasoning", "skill.argument_parts"],
        "distractor_traps": "B=out_of_scope C=out_of_scope D=half_right E=out_of_scope",
    },
    {
        "stem": (
            "For decades, museums treated the conservation of old paintings as a "
            "race to restore each work to its original appearance, stripping "
            "away later varnish and overpaint until the earliest surface "
            "reemerged. A newer school of conservators rejects this goal as "
            "naive. Every act of restoration, they argue, is itself an "
            "interpretation: deciding what counts as the original requires "
            "choosing among the many states a painting has passed through, and "
            "the tools and tastes of the restorer inevitably leave their own "
            "mark. These conservators do not conclude that restoration should "
            "stop; rather, they hold that it should be fully documented and, "
            "wherever possible, reversible -- treated as one more chapter in a "
            "work's history rather than as a return to some fixed origin. The "
            "aim, on this view, is not to erase time but to manage it "
            "honestly.\n\nWhich one of the following most accurately expresses "
            "the main point of the passage?"
        ),
        "choices": (
            "(A) Museums should stop restoring old paintings, since every "
            "restoration distorts the original work.\n"
            "(B) A newer school of conservators regards restoration not as a "
            "return to a painting's fixed original state but as a documented, "
            "reversible act of interpretation within the work's continuing "
            "history.\n"
            "(C) Older conservators could never agree among themselves about "
            "which state of a painting counted as its original.\n"
            "(D) The tools and tastes of a restorer always end up damaging the "
            "paintings they are used on.\n"
            "(E) Restoring a painting to its original appearance is the surest "
            "way to preserve the work's history."
        ),
        "correct": "B",
        "difficulty": "medium",
        "skills": ["rc.main_point_purpose", "skill.rc_structural_reading"],
        "distractor_traps": "A=extreme_language C=out_of_scope D=extreme_language E=reversal",
    },
    {
        "stem": (
            "Economists have long held that when the price of a good rises, "
            "people buy less of it. A handful of goods appear to defy this rule: "
            "as their prices climbed, the quantity demanded rose as well. Early "
            "commentators seized on such cases as refutations of the basic law "
            "of demand. Closer analysis, however, dissolves the paradox. In each "
            "case the rising price signaled something buyers valued -- scarcity, "
            "status, or higher quality -- so that the increase changed not merely "
            "the cost of the good but what buyers believed they were purchasing. "
            "The law of demand, properly stated, holds the buyer's perception of "
            "the good constant; once that perception shifts, no genuine exception "
            "has occurred.\n\nThe passage proceeds by"
        ),
        "choices": (
            "(A) stating a general principle, describing apparent exceptions to "
            "it, and then arguing that the exceptions are not genuine once the "
            "principle is properly understood.\n"
            "(B) tracing the historical development of a principle from its "
            "earliest origins to its modern form.\n"
            "(C) contrasting two competing principles and defending one of them "
            "against the other.\n"
            "(D) using a series of examples to demonstrate that a widely "
            "accepted principle is false.\n"
            "(E) proposing a new principle to replace one that earlier analysis "
            "had discredited."
        ),
        "correct": "A",
        "difficulty": "medium",
        "skills": ["rc.structure_organization", "skill.rc_structural_reading"],
        "distractor_traps": "B=out_of_scope C=half_right D=reversal E=reversal",
    },
]

# Alias kept for the historical name used by ``seed.py`` / callers.
SEED_ITEMS: list[dict] = PRACTICE_ITEMS
