// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// Loosely-typed mirrors of the JSON that lsat/dashboard_data.py::build() and the
// study endpoints return. Fields are optional because every panel abstains
// honestly until it has enough evidence, so consumers must guard on presence.

export interface OverallMemory {
    memory: number | null;
    low: number | null;
    high: number | null;
    displayed_topics?: number;
    note?: string;
}

export interface TopicRow {
    node_id: string;
    name: string;
    kind?: string;
    tag?: string;
    n_cards?: number;
    n_reviews?: number;
    n_events?: number;
    memory?: number | null;
    p?: number | null;
    low?: number | null;
    high?: number | null;
    enough_evidence?: boolean;
    note?: string;
}

export interface MemoryScore {
    overall: OverallMemory;
    topics: TopicRow[];
}

export interface PerformanceScore {
    available?: boolean;
    overall?: { p: number; low: number; high: number; displayed_topics: number } | null;
    topics?: TopicRow[];
    n_events?: number;
    note?: string;
}

export interface ReadinessScore {
    available?: boolean;
    point_estimate?: number;
    range?: [number, number];
    percent_covered?: number;
    // [level, reason] -- both strings; level is "low" | "medium" | "high"
    // (see lsat/models/readiness.py::_confidence).
    confidence?: [string, string];
    top_reasons?: string[];
    best_next_to_study?: { node_id: string; name: string } | null;
    past_projection_track_record?: { note?: string };
    reason?: string;
    missing?: string[];
    // D2: how many points each side the band grew due to measured
    // student miscalibration, and the index that drove it.
    range_widened_by_miscalibration?: number;
    student_overconfidence?: number | null;
}

// -- insight panels ---------------------------------------------------------

export interface Abstainable {
    available?: boolean;
    reason?: string;
}

export interface CalibrationPanel extends Abstainable {
    n_rated?: number;
    ece?: number;
    resolution_auc?: number;
    overconfidence_index?: number;
    reliability?: { confidence_label: string; stated_prob: number; actual_accuracy: number; n: number }[];
    sure_and_wrong?: { item_id: string; node_ids: string[]; confidence: string }[];
}

export interface TrapFamily {
    misses: number;
    weight: number;
    share: number;
}

export interface TrapPanel extends Abstainable {
    headline?: string | null;
    n_attributed_misses?: number;
    by_family?: Record<string, TrapFamily>;
    by_type_family?: Record<string, unknown>;
}

export interface GapCounts {
    mastered: number;
    fragile: number;
    pressure: number;
    knowledge: number;
}

export interface GapMapPanel extends Abstainable {
    headline?: string;
    overall?: { counts: GapCounts; shares?: Record<string, number> } | null;
    skills?: { node_id: string; name?: string; counts: GapCounts }[];
}

export interface ChokePanel extends Abstainable {
    // Paired within-item estimator (DECISION-round2 #24): the overall mean delta
    // with a bootstrap 95% CI and a confident-gap flag (CI lower bound > 0).
    method?: string;
    overall?: {
        choke_index: number;
        ci_low?: number;
        ci_high?: number;
        flag?: boolean;
        n_paired?: number;
        // Present only on the unpaired fallback below.
        timed_accuracy?: number;
        untimed_accuracy?: number;
    } | null;
    skills?: {
        node_id: string;
        name?: string;
        choke_index?: number;
        ci_low?: number;
        ci_high?: number;
        flag?: boolean;
        enough_evidence?: boolean;
    }[];
    top_choke_skills?: string[];
    headline?: string;
    note?: string;
    n_paired_items?: number;
    // The old unpaired aggregate, kept as a labelled low-confidence fallback.
    fallback?: {
        available?: boolean;
        method?: string;
        headline?: string;
        overall?: { timed_accuracy: number; untimed_accuracy: number; choke_index: number } | null;
    };
}

export interface PacingPanel extends Abstainable {
    overall?: { median_response_ms: number; slow_share: number } | null;
    skills?: unknown[];
}

export interface FluencyNode {
    available?: boolean;
    state?: "not_yet" | "effortful" | "automatic";
    accuracy?: number;
    median_ms?: number;
    n?: number;
    fast_ms?: number;
}

export interface FluencyPanel extends Abstainable {
    nodes?: Record<string, FluencyNode>;
    fast_ms?: number | null;
}

export interface MisconceptionHypothesis {
    text: string;
    source_label: string;
    label: string;
    source: string;
    item_id?: string;
}

export interface MisconceptionPanelData extends Abstainable {
    n_events?: number;
    n_classified?: number;
    states?: Record<string, number>;
    by_topic?: Record<string, Record<string, number>>;
    misconceptions?: { item_id: string; status: string; chosen?: string }[];
    resolution?: { open: number; resolved: number; relapsed: number };
    headline?: string | null;
    hypotheses?: MisconceptionHypothesis[];
}

export interface FatiguePanel extends Abstainable {
    n_timed?: number;
    n_sessions?: number;
    bins?: { label: string; n: number; accuracy: number; median_response_ms: number }[];
    accuracy_slope_per_30min?: number | null;
    note?: string;
}

// Rush-Error panel: on items answered faster than a personal speed threshold, is
// the error rate higher than at the student's normal pace? A gentle diagnostic --
// the excess is in accuracy percentage points with a bootstrap 95% CI, and the
// `framing` string states it is a nudge, never a punitive score. Abstains (via
// `note`) until there are enough timed + baseline answers.
export interface RushSkill {
    node_id: string;
    name: string;
    enough_evidence?: boolean;
    n_timed?: number;
    n_fast?: number;
    n_slow?: number;
    n_rush?: number;
    fast_error_rate?: number;
    nonfast_error_rate?: number;
    // 0-1 accuracy delta (fast_error_rate - nonfast_error_rate); null when unknown.
    rush_excess?: number | null;
    excess_ci_low?: number | null;
    excess_ci_high?: number | null;
    flag?: boolean;
    threshold_ms?: number;
    baseline_median_ms?: number;
}

export interface RushOverall {
    n_timed?: number;
    n_fast?: number;
    n_slow?: number;
    n_rush?: number;
    fast_error_rate?: number;
    nonfast_error_rate?: number;
    rush_excess?: number | null;
    excess_ci_low?: number | null;
    excess_ci_high?: number | null;
    flag?: boolean;
    threshold_ms?: number;
    baseline_median_ms?: number;
    flagged_skills?: string[];
}

export interface RushPanel extends Abstainable {
    n_timed?: number;
    n_baseline?: number;
    framing?: string;
    overall?: RushOverall | null;
    skills?: RushSkill[];
    headline?: string;
    // present only when abstaining -- a calm "answer some timed", never an error.
    note?: string;
}

// Time-Leak panel: on items answered right BOTH timed and untimed, how much clock
// time could pacing reclaim? STRICTLY descriptive -- `reclaimable_seconds` is TIME
// (rendered as minutes), never a promised score/point gain (the `framing` string
// says so). Abstains (via `reason`) until there is a blind pass to compare against.
export interface TimeLeakSkill {
    node_id: string;
    name: string;
    reclaimable_seconds?: number;
    n_unwinnable?: number;
    n_pairs?: number;
}

export interface TimeLeakOverall {
    reclaimable_seconds?: number;
    reclaimable_ci_low?: number;
    reclaimable_ci_high?: number;
    n_unwinnable?: number;
    n_winnable?: number;
    n_pairs?: number;
}

export interface TimeLeakPanel extends Abstainable {
    n_pairs?: number;
    framing?: string;
    measurable_leak?: boolean;
    overall?: TimeLeakOverall | null;
    skills?: TimeLeakSkill[];
    headline?: string;
}

export interface Insights {
    calibration?: CalibrationPanel;
    traps?: TrapPanel;
    gap_map?: GapMapPanel;
    choke?: ChokePanel;
    pacing?: PacingPanel;
    fluency?: FluencyPanel;
    fatigue?: FatiguePanel;
    misconceptions?: MisconceptionPanelData;
    rush?: RushPanel;
    time_leak?: TimeLeakPanel;
}

export interface PrimitiveFamily {
    covered: number;
    total: number;
    pct: number;
    missing: string[];
}

export interface PrimitiveCoverage extends Abstainable {
    families?: Record<string, PrimitiveFamily>;
    overall_pct?: number;
    basis?: string;
}

export interface Coverage {
    pct: number;
    covered: number;
    total: number;
    min_items: number;
    basis?: string;
    topics: { node_id: string; name: string; n_cards: number; covered: boolean }[];
    primitives?: PrimitiveCoverage;
}

export interface ExamSchedule {
    available?: boolean;
    days_until_exam?: number | null;
    desired_retention?: number | null;
    n_below_target?: number;
    n_due_after_exam?: number;
    reason?: string | null;
    note?: string | null;
}

export interface Adherence {
    available?: boolean;
    if_then?: string;
    n_cards_target?: number;
    window_days?: number;
    active_days?: number;
    completed_days?: number;
    last_active_days_ago?: number | null;
    consecutive_missed_days?: number;
    needs_replan?: boolean;
    reason?: string;
    note?: string;
}

// Mastery-Growth: a self-referential progress readout. Each skill compares the
// student's recent accuracy against their own earlier window and abstains until
// a bootstrap 95% CI clears 0 -- so a directional call ("improved"/"slipped")
// is never a rank, a percentile, or a comparison to anyone else.
export interface GrowthSkill {
    node_id: string;
    label: string;
    // true iff the readout is directional (status improved/slipped).
    available: boolean;
    status: "improved" | "slipped" | "abstain";
    // signed accuracy delta (recent - early) as a 0-1 fraction; present when
    // available (0.14 => +14 percentage points).
    delta?: number;
    ci_low?: number;
    ci_high?: number;
    n_early: number;
    n_recent: number;
    // present when abstaining -- a calm "keep going", never a failure.
    reason?: string;
    // present when available -- the concrete next action for this skill.
    next_step?: string;
}

export interface MasteryGrowth {
    // true iff at least one skill has a directional readout.
    available: boolean;
    skills: GrowthSkill[];
    n_improved: number;
    n_slipped: number;
    n_tracked: number;
    headline: string;
    // honesty framing: self-referential, not a rank/score.
    note: string;
}

// First-Instinct Ledger (DECISION-round4 #17): the learner's OWN answer-change
// tally over their captured timed sections, with a bootstrap 95% CI. It reports a
// direction only when the CI excludes 0 -- never the folk "never change" rule nor
// the population ~2:1 base rate (applying either to an individual is the ecological
// fallacy). A DIAGNOSTIC, not a prescription or a score; abstains below a
// min-changes floor. Fields optional so consumers guard on presence.
export interface AnswerChangeLedger extends Abstainable {
    direction?: "changing_helps_you" | "changing_costs_you" | "abstain";
    n_changes?: number;
    wrong_to_right?: number;
    right_to_wrong?: number;
    wrong_to_wrong?: number;
    // signed net = wrong->right minus right->wrong; present when available.
    net?: number;
    ci_low?: number;
    ci_high?: number;
    // present when available -- the plain-language directional read.
    headline?: string;
    n_sections?: number;
    floor?: number;
    // honesty framing: your own record, never a rule or base rate.
    framing?: string;
}

export interface Dashboard {
    exam: string;
    format_as_of: string;
    generated_at: number;
    give_up?: { min_reviews_per_topic?: number };
    // Exam-Day Retrievability Targeting (DECISION-round2 #7): days-to-exam +
    // consolidation count, or an abstain shape when no exam date is set.
    exam_schedule?: ExamSchedule;
    // If-Then study plan adherence (DECISION-round2 #4), or abstain when no plan.
    adherence?: Adherence;
    // Mastery-Growth panel: per-skill self-referential progress, or an abstain
    // shape when no skill has a directional readout yet.
    growth?: MasteryGrowth;
    scores: { memory: MemoryScore; performance: PerformanceScore; readiness: ReadinessScore };
    insights?: Insights;
    coverage: Coverage;
    // First-Instinct Ledger panel, or an abstain shape below the changes floor.
    answer_change?: AnswerChangeLedger;
}

// -- study flow (mobile) ----------------------------------------------------

export interface StudyChoice {
    letter: string;
    text: string;
}

export interface StudyItemData {
    item_id: string;
    stem: string;
    choices: StudyChoice[];
    skill_tags?: string[];
    done?: boolean; // true when the queue is empty
    remaining?: number;
}

export type Confidence = "sure" | "likely" | "guess" | "";

export interface AnswerContrast {
    available: boolean;
    // Why the credited answer is credited (keyed to the item's question type).
    why_credited?: string;
    // Why the picked letter is a trap (present only when it has a trap label).
    trap?: { family: string; label: string; tip: string; minimal_edit: string };
}

export interface AnswerResult {
    correct: boolean;
    correct_letter: string;
    has_traps: boolean;
    // Elaborated Contrast Card (DECISION-round2 #13): shown on a miss; null on a
    // correct answer; { available: false } when nothing is documented.
    contrast?: AnswerContrast | null;
}

export interface TrapResult {
    trap_correct: boolean;
    actual_family: string | null;
    actual_label: string | null;
}

// Conditional Translation Drill (DECISION-round2 #19).
export interface ConditionalDrillData {
    item_id: string;
    sentence: string;
    options: string[]; // the two clauses (shuffled); tap which is the sufficient condition
    done?: boolean;
}

export interface ConditionalResult {
    graded: boolean;
    correct?: boolean;
    sufficient_correct?: boolean;
    necessary_correct?: boolean;
    sufficient?: string;
    necessary?: string;
    arrow?: string;
    contrapositive?: string;
    reason?: string;
}

export interface ClassifyResult {
    classify_correct: boolean;
    actual_type: string;
    actual_label: string;
}

// Quantifier Reasoning Drill Suite. Fields on the result types are optional
// (matching ConditionalResult): the server sends only the graded payload or a
// `{ graded: false, reason }` shape, so consumers guard on `graded`.
export type QuantifierVerdict = "must_be_true" | "cannot_be_true" | "could_be_either";

export interface QuantifierValidityDrill {
    item_id: string;
    premises: string[];
    conclusion: string;
    done?: boolean;
}

export interface QuantifierValidityResult {
    graded: boolean;
    correct?: boolean;
    verdict?: QuantifierVerdict;
    note?: string;
    reason?: string;
}

export interface QuantifierNegationOption {
    quant: string;
    text: string;
}

export interface QuantifierNegationDrill {
    item_id: string;
    sentence: string;
    options: QuantifierNegationOption[];
    done?: boolean;
}

export interface QuantifierNegationResult {
    graded: boolean;
    correct?: boolean;
    answer?: string;
    reason?: string;
}

// Stem-Polarity Micro-Drill: read a question stem and tap whether it is
// direct / EXCEPT / LEAST / negated. `options` is always the four fixed
// polarity keys (no shuffle -- they are semantic labels, not positions).
export interface StemPolarityDrill {
    item_id: string;
    stem: string;
    options: string[]; // always ["direct", "except", "least", "negated"]
    done?: boolean;
}

// Conditional-Chain Drill (r4 #22): a 3+ arrow chain + a candidate inference to
// judge must-follow / does-not-follow. `options` is always the two fixed verdict
// keys (no shuffle -- they are semantic labels, not answer positions).
export interface ChainDrill {
    item_id: string;
    premises: string[];
    candidate: string;
    options: string[]; // always ["must_follow", "does_not_follow"]
    done?: boolean;
}

export interface ChainResult {
    graded: boolean;
    correct?: boolean;
    verdict?: string; // the correct option key
    note?: string; // the teaching explanation, revealed post-answer
    reason?: string;
}

// Oracle-Verified Faded Worked Example (research feature #1): the first proven
// steps of a conditional-chain derivation are shown and the final step is
// blanked. Each option is a premise applied as-is or as its contrapositive
// (`move_id` is "<index>:direct" | "<index>:contra"). The correct move + note
// are withheld until submit (no leak). `source` records whether the served
// derivation was oracle-derived deterministically or LLM-drafted-then-verified.
export interface WorkedExampleMove {
    move_id: string;
    text: string;
}
// The proof receipt: what the buyer/skeptic sees to trust the "AI can't lie"
// claim. `steps_verified` shown steps were each re-derived by a decision
// procedure; `source` records whether the derivation was oracle-authored
// (deterministic), an LLM draft the oracle blessed (ai_verified), or an LLM
// draft the oracle vetoed -> deterministic (deterministic_fallback).
export interface ProofVerification {
    method: string;
    steps_verified: number;
    claim: string;
}
export interface WorkedExampleDrill {
    item_id: string;
    premises: string[];
    goal: string;
    shown_steps: string[];
    frontier: string;
    prompt: string;
    options: WorkedExampleMove[];
    fade: number;
    source?: string;
    verification?: ProofVerification;
    done?: boolean;
}

// Oracle-Proven "Skill or Luck?" evil twin: a minimally-edited variant of a
// formal-logic item whose correct answer FLIPS. `twin_key` encodes the base item
// + the edit so grading re-derives the answer from the oracle statelessly. The
// correct verdict + `edit_note` are withheld until submit. `source` records
// whether an LLM targeted the twin (ai_targeted) or it was picked deterministically.
export interface EvilTwinDrill {
    item_id: string;
    twin_key: string;
    premises: string[];
    conclusion: string;
    options: string[];
    prompt: string;
    source?: string;
    done?: boolean;
}
export interface EvilTwinResult {
    graded: boolean;
    correct?: boolean;
    verdict?: string;
    original_verdict?: string;
    edit_note?: string;
    reason?: string;
}

// Result fields are optional (matching ConditionalResult): the server sends the
// graded payload or a `{ graded: false, reason }` shape, so consumers guard on
// `graded`. `to_text` is the literal the chosen step reaches; `note` is the
// teaching explanation revealed post-answer.
export interface WorkedStepResult {
    graded: boolean;
    correct?: boolean;
    to_text?: string;
    note?: string;
    reason?: string;
}

// Result fields are optional (matching ConditionalResult): the server sends the
// graded payload or a `{ graded: false, reason }` shape, so consumers guard on
// `graded`. `base_task` is a best-effort taxonomy hint and may be null.
export interface StemPolarityResult {
    graded: boolean;
    correct?: boolean;
    polarity?: string;
    instruction?: string;
    base_task?: string | null;
    reason?: string;
}

// Necessary/Sufficient Discrimination Drill (r4 #5): sort a candidate
// assumption for a gap argument into necessary-only / sufficient-only / both /
// neither. `options` is always the four fixed cell keys (no shuffle -- they are
// semantic labels, not positions).
export interface AssumptionDrill {
    item_id: string;
    premises: string[];
    conclusion: string;
    candidate: string;
    options: string[]; // always ["necessary_only","sufficient_only","both","neither"]
    done?: boolean;
}

// Result fields are optional (matching ConditionalResult): the server sends the
// graded payload or a `{ graded: false, reason }` shape, so consumers guard on
// `graded`. `cell` is the correct option key; `label` is its human label; `note`
// is the teaching explanation revealed post-answer.
export interface AssumptionResult {
    graded: boolean;
    correct?: boolean;
    cell?: string;
    label?: string;
    necessary?: boolean;
    sufficient?: boolean;
    note?: string;
    reason?: string;
}

// Timed Section Runner (DECISION-round4 #17). The client sends RAW first/final
// CHOICES per question -- never correctness; the server grades them so a timed
// section stays blind until submit. `reached` is true iff the question got a
// final choice; an unreached question carries empty choices.
export interface SectionQuestionAttempt {
    item_id: string;
    first_choice: string;
    final_choice: string;
    reached: boolean;
    flagged: boolean;
    dwell_ms: number;
    n_changes: number;
}

// The submit response: the refreshed First-Instinct Ledger, or a fail-closed
// `{ ok: false, reason }` for an empty / malformed trajectory.
export interface SectionAttemptResult {
    ok: boolean;
    n_questions?: number;
    ledger?: AnswerChangeLedger;
    reason?: string;
}

// A batch of distinct items for a timed section (no correct answer included).
export interface SectionItems {
    items: StudyItemData[];
    n: number;
}

export type Status = "good" | "warn" | "bad" | "neutral";

// Oracle Proof Theater (marquee AI demo): a RECORDED model draft of a
// conditional-chain derivation, checked LIVE step-by-step by the exact
// material-entailment oracle. Most moves verify; exactly one is a planted
// hallucination whose verdict flips to blocked (with the oracle's reason), after
// which the oracle substitutes the continuation it can prove. Every `verified` /
// `blocked` flag is computed server-side at request time -- nothing is baked.
export interface OracleTheaterStep {
    n: number;
    claim: string; // cumulative claim, e.g. "A ⊢ B"
    cited: string; // the rendered premise the step cites (notes if contrapositive)
    verified: boolean;
    blocked: boolean;
    reason: string | null; // the oracle's verbatim veto, present iff blocked
}

export interface OracleTheaterCorrectedStep {
    claim: string;
    cited: string;
}

export interface OracleTheaterScenario {
    id: string;
    title: string;
    premises: string[];
    goal: string;
    mode: "recorded"; // the draft is a committed recording, replayed offline
    steps: OracleTheaterStep[];
    corrected: OracleTheaterCorrectedStep[];
    receipt: { verified_steps: number; note: string };
}

export interface OracleTheater {
    scenarios: OracleTheaterScenario[];
    // "live" when a model key is present, else "recorded"; the VERDICTS are
    // computed live by the oracle either way (only the draft's provenance differs).
    mode: "live" | "recorded";
}
