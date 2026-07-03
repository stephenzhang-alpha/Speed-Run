# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""The 50-pair gold set (docs/ai-card-pipeline.md section 3).

50 ORIGINAL LSAT-style question -> known-correct-answer pairs, spread across the
taxonomy (LR question types, the flaw catalog, conditional logic, RC). All are
authored for this project -- never LSAC/PrepTest content (PRD section 16). Each
carries a ``principle`` span that supports its answer, so the gold set can both
(a) validate the checker (:func:`checker_validation_cases`) and (b) anchor the
performance eval. Keep in the held-out partition (leakage check, PRD section 12).
"""

from __future__ import annotations

import re
from typing import Any


def _overlap(a: str, b: str) -> float:
    ta = {t for t in re.findall(r"[a-z0-9]+", a.lower()) if len(t) > 2}
    tb = {t for t in re.findall(r"[a-z0-9]+", b.lower()) if len(t) > 2}
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


GOLD_SET: list[dict[str, Any]] = [
    # -- LR: flaw catalog ----------------------------------------------------
    {
        "id": "g01",
        "skill": "flaw.causal",
        "difficulty": "medium",
        "question": "Sales rose after the new logo launched, so the logo caused the increase. Name the flaw.",
        "answer": "Correlation mistaken for causation (post hoc): a later event is assumed to be caused by an earlier one.",
        "principle": "Assuming that because one event followed another the first caused the second is the post hoc, correlation-causation flaw.",
    },
    {
        "id": "g02",
        "skill": "flaw.ad_hominem",
        "difficulty": "easy",
        "question": '"Her argument for the tax is worthless because she is wealthy." Name the flaw.',
        "answer": "Ad hominem: attacking the arguer's traits instead of the argument's merits.",
        "principle": "Attacking the person advancing an argument rather than the argument itself is the ad hominem flaw.",
    },
    {
        "id": "g03",
        "skill": "flaw.sampling",
        "difficulty": "medium",
        "question": "A poll of one club's members is used to describe the whole city. Name the flaw.",
        "answer": "Unrepresentative (biased) sample: generalizing from a group that may not reflect the population.",
        "principle": "Generalizing from a sample that may not represent the larger population is the unrepresentative-sample flaw.",
    },
    {
        "id": "g04",
        "skill": "flaw.equivocation",
        "difficulty": "hard",
        "question": 'An argument uses "free" to mean both "no cost" and "at liberty." Name the flaw.',
        "answer": "Equivocation: a key term shifts meaning between premises and conclusion.",
        "principle": "Using one word in two different senses within an argument is the equivocation flaw.",
    },
    {
        "id": "g05",
        "skill": "flaw.circular",
        "difficulty": "medium",
        "question": '"The law is just because it is the law." Name the flaw.',
        "answer": "Circular reasoning: the conclusion is assumed as a premise.",
        "principle": "Assuming the truth of the conclusion among the premises is circular reasoning (begging the question).",
    },
    {
        "id": "g06",
        "skill": "flaw.false_dilemma",
        "difficulty": "medium",
        "question": '"Either we cut the budget or the city fails; we won\'t cut, so it fails." Name the flaw.',
        "answer": "False dilemma: only two options are presented when others exist.",
        "principle": "Presenting only two choices when more are available is the false-dilemma flaw.",
    },
    {
        "id": "g07",
        "skill": "flaw.appeal_authority",
        "difficulty": "easy",
        "question": "A celebrity endorses a medical claim, so the claim is treated as true. Name the flaw.",
        "answer": "Appeal to an authority with no relevant expertise.",
        "principle": "Treating an endorsement from someone lacking relevant expertise as evidence is an illegitimate appeal to authority.",
    },
    {
        "id": "g08",
        "skill": "flaw.composition",
        "difficulty": "hard",
        "question": '"Each part is light, so the whole machine is light." Name the flaw.',
        "answer": "Composition: inferring a property of the whole from properties of its parts.",
        "principle": "Inferring that the whole has a property merely because its parts do is the composition flaw.",
    },
    {
        "id": "g09",
        "skill": "flaw.straw_man",
        "difficulty": "medium",
        "question": "A rebuttal distorts an opponent's modest claim into an extreme one, then refutes that. Name the flaw.",
        "answer": "Straw man: refuting a distorted, weaker version of the opponent's position.",
        "principle": "Misrepresenting an opponent's view as a weaker claim and refuting that is the straw-man flaw.",
    },
    {
        "id": "g10",
        "skill": "flaw.necessary_sufficient",
        "difficulty": "hard",
        "question": '"Studying is needed to pass; she studied, so she passed." Name the flaw.',
        "answer": "Confusing a necessary condition with a sufficient one.",
        "principle": "Treating a necessary condition as if it were sufficient is a necessary-sufficient confusion.",
    },
    # -- LR: question-type recognition ---------------------------------------
    {
        "id": "g11",
        "skill": "lr.weaken",
        "difficulty": "easy",
        "question": 'Stem: "Which one, if true, most undermines the argument?" Classify the question type.',
        "answer": "Weaken.",
        "principle": "Stems asking what most undermines or calls into question an argument are Weaken questions.",
    },
    {
        "id": "g12",
        "skill": "lr.strengthen",
        "difficulty": "easy",
        "question": 'Stem: "Which one, if true, most supports the conclusion?" Classify the question type.',
        "answer": "Strengthen.",
        "principle": "Stems asking what most supports or bolsters the conclusion are Strengthen questions.",
    },
    {
        "id": "g13",
        "skill": "lr.assumption_necessary",
        "difficulty": "medium",
        "question": 'Stem: "The argument depends on which assumption?" Classify the question type.',
        "answer": "Necessary Assumption.",
        "principle": "Stems asking what the argument depends on or requires identify a Necessary Assumption question.",
    },
    {
        "id": "g14",
        "skill": "lr.assumption_sufficient",
        "difficulty": "medium",
        "question": 'Stem: "Which principle, if assumed, allows the conclusion to be properly drawn?" Classify.',
        "answer": "Sufficient Assumption (Justify).",
        "principle": "Stems asking what, if assumed, would justify or guarantee the conclusion identify a Sufficient Assumption question.",
    },
    {
        "id": "g15",
        "skill": "lr.inference_must_be_true",
        "difficulty": "medium",
        "question": 'Stem: "If the statements are true, which must also be true?" Classify.',
        "answer": "Inference / Must Be True.",
        "principle": "Stems asking what must be true given the statements identify an Inference (Must Be True) question.",
    },
    {
        "id": "g16",
        "skill": "lr.most_strongly_supported",
        "difficulty": "medium",
        "question": 'Stem: "The statements most strongly support which one of the following?" Classify.',
        "answer": "Most Strongly Supported.",
        "principle": "Stems asking what is most strongly supported (not strictly entailed) identify a Most Strongly Supported question.",
    },
    {
        "id": "g17",
        "skill": "lr.principle",
        "difficulty": "medium",
        "question": 'Stem: "Which principle, if valid, most helps to justify the reasoning?" Classify.',
        "answer": "Principle (Identify/Apply).",
        "principle": "Stems invoking a general principle that governs or justifies the reasoning identify a Principle question.",
    },
    {
        "id": "g18",
        "skill": "lr.paradox",
        "difficulty": "medium",
        "question": 'Stem: "Which one, if true, most helps resolve the apparent discrepancy?" Classify.',
        "answer": "Resolve / Explain the Paradox.",
        "principle": "Stems asking what resolves an apparent conflict or discrepancy identify a Paradox question.",
    },
    {
        "id": "g19",
        "skill": "lr.parallel",
        "difficulty": "hard",
        "question": 'Stem: "The reasoning is most similar to which one of the following?" Classify.',
        "answer": "Parallel Reasoning.",
        "principle": "Stems asking which answer's reasoning is most similar in structure identify a Parallel Reasoning question.",
    },
    {
        "id": "g20",
        "skill": "lr.method",
        "difficulty": "medium",
        "question": 'Stem: "The argument proceeds by..." Classify the question type.',
        "answer": "Method of Reasoning.",
        "principle": "Stems asking how an argument proceeds or what technique it uses identify a Method of Reasoning question.",
    },
    {
        "id": "g21",
        "skill": "lr.main_conclusion",
        "difficulty": "easy",
        "question": 'Stem: "Which one most accurately expresses the main conclusion?" Classify.',
        "answer": "Main Conclusion.",
        "principle": "Stems asking for the argument's main conclusion identify a Main Conclusion question.",
    },
    {
        "id": "g22",
        "skill": "lr.point_at_issue",
        "difficulty": "medium",
        "question": 'Stem: "The dialogue supports that the two disagree about whether..." Classify.',
        "answer": "Point at Issue (Disagreement).",
        "principle": "Stems asking what two speakers disagree about identify a Point at Issue question.",
    },
    # -- Conditional logic ---------------------------------------------------
    {
        "id": "g23",
        "skill": "skill.conditional_logic",
        "difficulty": "easy",
        "question": 'Give the contrapositive of "If P then Q."',
        "answer": "If not Q then not P.",
        "principle": 'The contrapositive of "if P then Q" negates and swaps the terms to "if not Q then not P," which is logically equivalent.',
    },
    {
        "id": "g24",
        "skill": "skill.conditional_logic",
        "difficulty": "medium",
        "question": '"A only if B" translates to which conditional?',
        "answer": "If A then B.",
        "principle": '"A only if B" means A cannot hold without B, i.e., if A then B.',
    },
    {
        "id": "g25",
        "skill": "skill.conditional_logic",
        "difficulty": "medium",
        "question": '"No cats are dogs" translates to which conditional?',
        "answer": "If it is a cat then it is not a dog (and contrapositive: if a dog then not a cat).",
        "principle": '"No X are Y" means if something is an X then it is not a Y.',
    },
    {
        "id": "g26",
        "skill": "skill.conditional_logic",
        "difficulty": "medium",
        "question": '"P unless Q" translates to which conditional?',
        "answer": "If not Q then P.",
        "principle": '"P unless Q" means that without Q, P holds: if not Q then P.',
    },
    {
        "id": "g27",
        "skill": "skill.conditional_logic",
        "difficulty": "hard",
        "question": "Given P->Q and Q->R, what follows about P?",
        "answer": "P->R (chaining the conditionals).",
        "principle": "Conditionals chain transitively: from P->Q and Q->R it follows that P->R.",
    },
    {
        "id": "g28",
        "skill": "skill.conditional_logic",
        "difficulty": "medium",
        "question": 'Negate "All A are B."',
        "answer": "At least one A is not B (some A are not B).",
        "principle": 'The negation of "all A are B" is "at least one A is not B."',
    },
    {
        "id": "g29",
        "skill": "skill.conditional_logic",
        "difficulty": "hard",
        "question": '"P if and only if Q" yields which two conditionals?',
        "answer": "If P then Q, and if Q then P.",
        "principle": 'A biconditional "P if and only if Q" asserts both if P then Q and if Q then P.',
    },
    {
        "id": "g30",
        "skill": "skill.conditional_logic",
        "difficulty": "hard",
        "question": 'From "if P then Q," does "not P" let you conclude "not Q"?',
        "answer": "No -- that is denying the antecedent; not P is uninformative about Q.",
        "principle": "Concluding not-Q from not-P is the fallacy of denying the antecedent and is invalid.",
    },
    {
        "id": "g31",
        "skill": "skill.conditional_logic",
        "difficulty": "medium",
        "question": 'From "if P then Q," does "Q" let you conclude "P"?',
        "answer": "No -- that is affirming the consequent and is invalid.",
        "principle": 'Concluding P from Q given "if P then Q" is the fallacy of affirming the consequent.',
    },
    {
        "id": "g32",
        "skill": "skill.conditional_logic",
        "difficulty": "easy",
        "question": '"All students who pass studied." What is guaranteed of a student who did not study?',
        "answer": "That student did not pass (contrapositive).",
        "principle": "If passing requires studying, then by contrapositive a student who did not study did not pass.",
    },
    # -- Reading comprehension ----------------------------------------------
    {
        "id": "g33",
        "skill": "rc.main_point",
        "difficulty": "medium",
        "question": 'RC stem: "Which one best states the main point of the passage?" Classify.',
        "answer": "Main Point.",
        "principle": "RC stems asking for the central thesis of the whole passage are Main Point questions.",
    },
    {
        "id": "g34",
        "skill": "rc.primary_purpose",
        "difficulty": "medium",
        "question": 'RC stem: "The author\'s primary purpose is to..." Classify.',
        "answer": "Primary Purpose.",
        "principle": "RC stems asking why the author wrote the passage identify a Primary Purpose question.",
    },
    {
        "id": "g35",
        "skill": "rc.author_attitude",
        "difficulty": "medium",
        "question": 'RC stem: "The author\'s attitude toward the theory is best described as..." Classify.',
        "answer": "Author's Attitude / Tone.",
        "principle": "RC stems asking about the author's stance or tone identify an Attitude question.",
    },
    {
        "id": "g36",
        "skill": "rc.function",
        "difficulty": "hard",
        "question": 'RC stem: "The second paragraph functions primarily to..." Classify.',
        "answer": "Function / Role of a passage part.",
        "principle": "RC stems asking what a paragraph or sentence accomplishes identify a Function question.",
    },
    {
        "id": "g37",
        "skill": "rc.inference",
        "difficulty": "medium",
        "question": 'RC stem: "The passage implies which one of the following?" Classify.',
        "answer": "Inference.",
        "principle": "RC stems asking what the passage implies or suggests identify an Inference question.",
    },
    {
        "id": "g38",
        "skill": "rc.detail",
        "difficulty": "easy",
        "question": 'RC stem: "According to the passage, X is..." Classify.',
        "answer": "Detail (explicitly stated).",
        "principle": "RC stems asking what the passage explicitly states identify a Detail question.",
    },
    {
        "id": "g39",
        "skill": "rc.comparative",
        "difficulty": "hard",
        "question": "In comparative RC, a question asks where the two passages would agree. Classify.",
        "answer": "Comparative agreement/relationship question.",
        "principle": "Comparative RC questions ask how two passages relate, such as where their authors agree or disagree.",
    },
    {
        "id": "g40",
        "skill": "rc.strengthen",
        "difficulty": "hard",
        "question": 'RC stem: "Which finding, if true, would most support the author\'s claim?" Classify.',
        "answer": "Strengthen (applied in RC).",
        "principle": "RC stems asking what new information would support the author's claim are Strengthen questions.",
    },
    # -- Trap patterns & mixed judgments -------------------------------------
    {
        "id": "g41",
        "skill": "trap.extreme_language",
        "difficulty": "medium",
        "question": 'Why is an answer using "always" often a trap on an inference question?',
        "answer": "Extreme wording overstates what the passage supports; the text rarely warrants absolute claims.",
        "principle": "Answer choices with extreme words like always or never are common traps because passages seldom support absolute claims.",
    },
    {
        "id": "g42",
        "skill": "trap.reversal",
        "difficulty": "hard",
        "question": "Name the trap in an answer that swaps the necessary and sufficient conditions.",
        "answer": "Conditional reversal (mistaken reversal).",
        "principle": "A trap answer that reverses a conditional treats a necessary condition as sufficient (a mistaken reversal).",
    },
    {
        "id": "g43",
        "skill": "trap.out_of_scope",
        "difficulty": "medium",
        "question": "Why is an answer introducing a new comparison the passage never made a trap?",
        "answer": "Out of scope: it goes beyond what the argument addresses.",
        "principle": "Answer choices that introduce considerations outside the argument's scope are out-of-scope traps.",
    },
    {
        "id": "g44",
        "skill": "trap.opposite",
        "difficulty": "medium",
        "question": "On a Weaken question, why is a supporting fact a trap?",
        "answer": "Opposite-answer trap: it strengthens rather than weakens.",
        "principle": "On a Weaken question, an answer that supports the argument is an opposite-answer trap.",
    },
    {
        "id": "g45",
        "skill": "lr.flaw",
        "difficulty": "medium",
        "question": "An argument treats absence of evidence as evidence of absence. Name the flaw.",
        "answer": "Appeal to ignorance: unproven is treated as false (or vice versa).",
        "principle": "Treating a claim as false merely because it has not been proven true is the appeal-to-ignorance flaw.",
    },
    {
        "id": "g46",
        "skill": "lr.flaw",
        "difficulty": "hard",
        "question": "An argument assumes what is true of a group is true of each member. Name the flaw.",
        "answer": "Division: inferring a property of a part from the whole.",
        "principle": "Inferring that each member has a property because the group does is the division flaw.",
    },
    {
        "id": "g47",
        "skill": "lr.weaken",
        "difficulty": "hard",
        "question": "What most weakens a causal claim that A causes B?",
        "answer": "Evidence of an alternative cause, or that B occurs without A.",
        "principle": "A causal claim that A causes B is weakened by an alternative cause or by cases where B occurs without A.",
    },
    {
        "id": "g48",
        "skill": "lr.strengthen",
        "difficulty": "hard",
        "question": "What most strengthens a causal claim that A causes B?",
        "answer": "Ruling out alternative causes, e.g., a controlled comparison where only A differs.",
        "principle": "A causal claim is strengthened by ruling out alternatives, such as a control group differing only in A.",
    },
    {
        "id": "g49",
        "skill": "lr.assumption_necessary",
        "difficulty": "hard",
        "question": "What does the negation test confirm about a necessary assumption?",
        "answer": "Negating a necessary assumption makes the argument fall apart.",
        "principle": "By the negation test, negating a necessary assumption destroys the argument's support for its conclusion.",
    },
    {
        "id": "g50",
        "skill": "lr.inference_must_be_true",
        "difficulty": "medium",
        "question": "On a Must Be True question, may a correct answer add outside information?",
        "answer": "No -- it must follow from the stated facts alone.",
        "principle": "A Must Be True answer must follow from the given statements alone, without new outside information.",
    },
]


def load_gold_set() -> list[dict[str, Any]]:
    return list(GOLD_SET)


def checker_validation_cases() -> list[tuple[Any, str, str, bool]]:
    """Build labelled ``(Card, source_span, gold_answer, is_correct)`` cases.

    For each gold item we build one CORRECT card (answer matches the gold) and
    one WRONG card (answer swapped from a different item -> unsupported by the
    span / conflicts with the gold), so :func:`validate_checker` can measure the
    false-pass and false-block rates."""
    from lsat.ai.generator import Card

    items = load_gold_set()
    cases: list[tuple[Any, str, str, bool]] = []
    for i, item in enumerate(items):
        span = item["principle"]
        # A clearly-wrong distractor: the other item's answer that shares the
        # least with this item's answer (a genuinely wrong card the checker
        # must catch). The offline checker judges by lexical support/overlap;
        # a real LLM checker would additionally catch subtler near-misses.
        wrong_answer = min(
            (items[j]["answer"] for j in range(len(items)) if j != i),
            key=lambda ans: _overlap(ans, item["answer"]),
        )

        def _card(back: str) -> Any:
            return Card(
                card_type="flaw_id",
                front=item["question"],
                back=back,
                explanation="",
                skill_tags=[item["skill"]],
                difficulty=item["difficulty"],
                source_id=item["id"],
                source_quote=span,
            )

        cases.append((_card(item["answer"]), span, item["answer"], True))
        cases.append((_card(wrong_answer), span, item["answer"], False))
    return cases
