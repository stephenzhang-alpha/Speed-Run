<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Mobile study flow: fetch an item over HTTP; for LR items first NAME the question
type (identification-first, SPOV 1/A2); then pick a choice, tap confidence, get
graded feedback, and (on a miss with trap labels) identify the trap. Mirrors the
desktop reviewer template but uses the HTTP client instead of the Qt pycmd bridge.
-->
<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte";

    import AnswerFeedback from "./AnswerFeedback.svelte";
    import Card from "./Card.svelte";
    import * as client from "./client";
    import ConfidenceTap from "./ConfidenceTap.svelte";
    import ContrastCard from "./ContrastCard.svelte";
    import TrapTap from "./TrapTap.svelte";
    import type {
        AnswerResult,
        ClassifyResult,
        StudyItemData,
        TrapResult,
    } from "./types";

    export let phase = "timed";

    // Lets the parent open the EvilTwin ("Skill or luck?") drill from the
    // lucky-guess CTA (which used to be a dead link back to this same route).
    const dispatch = createEventDispatcher<{ practicetwin: void }>();

    type State =
        | "loading"
        | "classify"
        | "answering"
        | "confidence"
        | "grading"
        | "answered"
        | "queued"
        | "done"
        | "error";

    // All 17 LR question types (mirrors the taxonomy's lr.* question_types and the
    // desktop notetype's classify chips) so every shipped LR item's type is
    // actually selectable in the identification-first stage.
    const QTYPES: [string, string][] = [
        ["lr.flaw", "Flaw in the Reasoning"],
        ["lr.assumption_necessary", "Necessary Assumption"],
        ["lr.inference_must_be_true", "Inference / Must Be True"],
        ["lr.strengthen", "Strengthen"],
        ["lr.weaken", "Weaken"],
        ["lr.principle", "Principle (Identify & Apply)"],
        ["lr.assumption_sufficient", "Sufficient Assumption / Justify"],
        ["lr.paradox", "Resolve / Explain the Paradox"],
        ["lr.most_strongly_supported", "Most Strongly Supported"],
        ["lr.parallel_reasoning", "Parallel Reasoning"],
        ["lr.method_of_reasoning", "Method of Reasoning / Argument"],
        ["lr.main_conclusion", "Main Conclusion"],
        ["lr.role_in_argument", "Role in Argument"],
        ["lr.parallel_flaw", "Parallel Flaw"],
        ["lr.point_at_issue", "Point at Issue / Agreement"],
        ["lr.evaluate", "Evaluate the Argument"],
        ["lr.cannot_be_true", "Cannot Be True"],
    ];

    let item: StudyItemData | null = null;
    let state: State = "loading";
    let chosen = "";
    let confidence = ""; // the pre-reveal confidence ("sure" | "likely" | "guess")
    let answer: AnswerResult | null = null;
    let trapResult: TrapResult | null = null;
    let classifyResult: ClassifyResult | null = null;
    let identified = "";
    let error = "";
    let shownAt = 0;
    let classifying = false; // in-flight guard for the classify POST
    let trapPending = false; // in-flight guard for the trap POST
    let advancing = false; // in-flight guard for load(): a double-tap on "Next" would
    // otherwise call nextItem() twice and, offline, shift() two items from the
    // prefetch cache -- silently losing the second.
    // The study phase (timed/blind/relaxed) latched WHEN THE ITEM IS SHOWN, so a
    // mid-item toggle of the session control can't mislabel this answer's event.
    let capturedPhase = phase;

    async function load(): Promise<void> {
        if (advancing) {
            return; // guard: a double-tap must not consume two prefetched items
        }
        advancing = true;
        state = "loading";
        chosen = "";
        confidence = "";
        answer = null;
        trapResult = null;
        classifyResult = null;
        identified = "";
        error = "";
        try {
            const it = await client.nextItem();
            if (it.done || !it.item_id) {
                item = null;
                state = "done";
                return;
            }
            item = it;
            shownAt = Date.now();
            capturedPhase = phase; // latch at display time (see capturedPhase decl)
            // Identification-first: LR items must be classified before solving.
            const isLR = (it.skill_tags ?? []).some((t) => t.startsWith("lr."));
            state = isLR ? "classify" : "answering";
        } catch (e) {
            error = String(e);
            state = "error";
        } finally {
            advancing = false;
        }
    }

    async function classify(named: string): Promise<void> {
        // In-flight guard: without `classifying`, a fast double-tap (or a second
        // chip) passes the unchanged guard twice and double-logs the identification,
        // overwriting `identified` before it rides the graded answer.
        if (!item || state !== "classify" || classifyResult || classifying) {
            return;
        }
        classifying = true;
        try {
            classifyResult = await client.submitClassify(item.item_id, named);
            identified = classifyResult.classify_correct ? "1" : "0";
        } catch {
            /* classify feedback is best-effort; never block solving */
        } finally {
            classifying = false;
        }
        state = "answering";
    }

    function pick(letter: string): void {
        if (state !== "answering") {
            return;
        }
        chosen = letter;
        state = "confidence";
    }

    async function grade(conf: string): Promise<void> {
        // Re-entrancy guard (#16): only grade from the confidence step, and move
        // to a transient "grading" state BEFORE the await so the ConfidenceTap
        // unmounts and a second tap during the network round-trip cannot log the
        // same answer twice.
        if (!item || state !== "confidence") {
            return;
        }
        confidence = conf;
        state = "grading";
        try {
            const res = await client.submitAnswer(
                item.item_id,
                chosen,
                confidence,
                Date.now() - shownAt,
                capturedPhase,
                identified,
            );
            // Offline: the answer was saved to the local queue and will sync (and be
            // graded) on reconnect. There is no grade to show yet — acknowledge + advance.
            if (res.queued) {
                state = "queued";
                return;
            }
            // An item with no answer key is abstained server-side (graded:false, no
            // event logged); don't render a misleading "wrong" — skip to the next.
            if (res.graded === false) {
                error = "This question can't be graded (missing answer key). Skipping.";
                state = "error";
                return;
            }
            answer = res;
            state = "answered";
        } catch (e) {
            error = String(e);
            state = "error";
        }
    }

    async function chooseTrap(family: string): Promise<void> {
        // In-flight guard: TrapTap only disables its chips once trapResult is set
        // (after the await), so without trapPending a double-tap double-logs the trap.
        if (!item || trapResult || trapPending) {
            return;
        }
        trapPending = true;
        try {
            trapResult = await client.submitTrap(item.item_id, chosen, family);
        } catch {
            /* trap feedback is best-effort */
        } finally {
            trapPending = false;
        }
    }

    // Keyboard access (a11y + power users): 1-5 / A-E pick a choice while answering;
    // 1/2/3 rate confidence; Enter/Space advances. Ignored while typing anywhere.
    function handleKey(e: KeyboardEvent): void {
        const t = e.target as HTMLElement | null;
        if (
            t &&
            (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)
        ) {
            return;
        }
        if (state === "answering" && item) {
            const n = /^[1-9]$/.test(e.key) ? parseInt(e.key, 10) - 1 : -1;
            const byLetter = item.choices.findIndex(
                (c) => c.letter.toUpperCase() === e.key.toUpperCase(),
            );
            const idx = n >= 0 && n < item.choices.length ? n : byLetter;
            if (idx >= 0) {
                e.preventDefault();
                pick(item.choices[idx].letter);
            }
        } else if (state === "confidence") {
            const conf = { "1": "sure", "2": "likely", "3": "guess" }[e.key];
            if (conf) {
                e.preventDefault();
                grade(conf);
            }
        } else if (state === "answered" && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            load();
        }
    }

    // The confidence × correctness 2×2 (durable-learning framing, frontend-only):
    // a SURE miss is the highest-value fix (hypercorrection; Butterfield & Metcalfe
    // 2001); a GUESS that landed is not skill yet — nudge a proof. Never punish a
    // miss, never celebrate luck.
    $: hypercorrection =
        state === "answered" && confidence === "sure" && !!answer && !answer.correct;
    $: luckyGuess =
        state === "answered" && confidence === "guess" && !!answer && !!answer.correct;

    onMount(load);
</script>

<svelte:window on:keydown={handleKey} />

{#if state === "loading"}
    <Card><p class="muted">Loading&hellip;</p></Card>
{:else if state === "done"}
    <Card title="All caught up">
        <p class="muted">
            No questions due right now. Great work &mdash; check back later.
        </p>
    </Card>
{:else if state === "error"}
    <Card title="Couldn't load a question">
        <p class="muted">{error}</p>
        <button class="next" on:click={load} disabled={advancing}>Try again</button>
    </Card>
{:else if state === "queued"}
    <Card title="Saved offline">
        <p class="muted" aria-live="polite">
            You're offline &mdash; this answer is saved on your device and will sync
            (and be graded) automatically when you reconnect.
        </p>
        <button class="next" on:click={load} disabled={advancing}>
            Next question
            <span class="arrow" aria-hidden="true">&rarr;</span>
        </button>
    </Card>
{:else if item}
    <Card>
        <div class="stem">{item.stem}</div>

        {#if state === "classify"}
            <div class="classify">
                <span class="classify-q">First: what type of question is this?</span>
                <div class="classify-chips">
                    {#each QTYPES as [id, label] (id)}
                        <button
                            type="button"
                            class="chip"
                            disabled={classifying || !!classifyResult}
                            on:click={() => classify(id)}
                        >
                            {label}
                        </button>
                    {/each}
                </div>
            </div>
        {:else}
            {#if classifyResult && classifyResult.actual_label}
                <p class="classify-fb" class:right={classifyResult.classify_correct}>
                    {classifyResult.classify_correct
                        ? `Yes \u2014 ${classifyResult.actual_label}.`
                        : `Actually this is a ${classifyResult.actual_label} question.`}
                </p>
            {/if}
            <div class="choices">
                {#each item.choices as c (c.letter)}
                    <button
                        type="button"
                        class="choice"
                        class:chosen={chosen === c.letter}
                        class:right={answer && c.letter === answer.correct_letter}
                        class:wrong={answer && !answer.correct && c.letter === chosen}
                        disabled={state !== "answering"}
                        on:click={() => pick(c.letter)}
                    >
                        <span class="letter">{c.letter}</span>
                        <span class="text">{c.text}</span>
                    </button>
                {/each}
            </div>
        {/if}

        {#if state === "confidence"}
            <ConfidenceTap on:select={(e) => grade(e.detail)} />
        {/if}

        {#if state === "grading"}
            <p class="muted checking" aria-live="polite">Checking&hellip;</p>
        {/if}

        {#if state === "answered" && answer}
            <AnswerFeedback
                correct={answer.correct}
                correctLetter={answer.correct_letter}
            />
            {#if luckyGuess}
                <button
                    type="button"
                    class="prove-it"
                    on:click={() => dispatch("practicetwin")}
                >
                    <span>
                        Right &mdash; but was that <em>skill or luck?</em>
                        A guess that lands isn't mastery yet.
                    </span>
                    <b>Prove it with a Skill-or-luck twin &rarr;</b>
                </button>
            {/if}
            {#if !answer.correct && answer.contrast}
                <div class="contrast-wrap" class:hyper={hypercorrection}>
                    {#if hypercorrection}
                        <p class="hyper-eyebrow">
                            <span class="he-mk" aria-hidden="true">◆</span>
                            High-confidence miss &mdash; the highest-value fix
                        </p>
                    {/if}
                    <ContrastCard {chosen} contrast={answer.contrast} />
                </div>
            {/if}
            {#if !answer.correct && answer.has_traps}
                <TrapTap
                    {chosen}
                    result={trapResult}
                    on:select={(e) => chooseTrap(e.detail)}
                />
            {/if}
            <button class="next" on:click={load} disabled={advancing}>
                Next question
                <span class="arrow" aria-hidden="true">&rarr;</span>
            </button>
        {/if}
    </Card>
{/if}

<style lang="scss">
    .muted {
        color: var(--lsat-fg-subtle);
        margin: 0;
    }
    .stem {
        white-space: pre-wrap;
        font-size: 1.02rem;
        line-height: 1.58;
        color: var(--lsat-fg);
        /* A slim signature gradient rule anchors the prompt. */
        padding-left: 0.85rem;
        background: var(--lsat-hero) left top / 3px 100% no-repeat;
        border-radius: 2px;
    }
    .classify {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        margin-top: 0.5rem;
    }
    .classify-q {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--lsat-fg-faint);
    }
    .classify-chips {
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
    }
    .chip {
        min-height: 40px;
        padding: 0.4rem 0.8rem;
        border-radius: var(--lsat-radius-pill);
        border: 1px solid var(--lsat-border);
        background: var(--lsat-surface);
        color: var(--lsat-fg);
        font: inherit;
        font-size: 0.85rem;
        font-weight: 550;
        cursor: pointer;
        transition:
            border-color var(--lsat-transition) var(--lsat-ease),
            background var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease);
    }
    .chip:hover {
        border-color: var(--lsat-accent);
        background: var(--lsat-accent-soft);
    }
    .chip:active {
        transform: scale(0.96);
    }
    .chip:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }
    /* Verdict on the identification step, as a soft status pill with a glyph. */
    .classify-fb {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        align-self: flex-start;
        margin: 0.35rem 0 0;
        padding: 0.32rem 0.7rem;
        border-radius: var(--lsat-radius-pill);
        font-size: 0.82rem;
        font-weight: 600;
        color: var(--lsat-bad);
        background: var(--lsat-bad-soft);
    }
    .classify-fb::before {
        content: "\2715";
        font-weight: 800;
    }
    .classify-fb.right {
        color: var(--lsat-good);
        background: var(--lsat-good-soft);
    }
    .classify-fb.right::before {
        content: "\2713";
    }
    .choices {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        margin-top: 0.4rem;
    }
    .choice {
        display: flex;
        align-items: flex-start;
        gap: 0.65rem;
        text-align: left;
        min-height: 48px;
        padding: 0.72rem 0.85rem;
        border: 1.5px solid var(--lsat-border);
        border-radius: var(--lsat-radius);
        background: var(--lsat-surface);
        color: var(--lsat-fg);
        font: inherit;
        cursor: pointer;
        transition:
            border-color var(--lsat-transition) var(--lsat-ease),
            background var(--lsat-transition) var(--lsat-ease),
            box-shadow var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease);
    }
    .choice:hover:not(:disabled) {
        border-color: var(--lsat-accent);
        box-shadow: var(--lsat-shadow);
    }
    .choice:active:not(:disabled) {
        transform: scale(0.99);
    }
    .choice:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }
    .choice:disabled {
        cursor: default;
    }
    /* While judging confidence and once answered, let the chosen + credited rows
     * carry the story; recede the rest. The chosen row stays prominent pre-reveal
     * so we protect the commitment without ever leaking correctness. */
    .choice:disabled:not(.right):not(.wrong):not(.chosen) {
        opacity: 0.45;
    }
    .choice.chosen {
        border-color: var(--lsat-accent);
        box-shadow: var(--lsat-glow);
    }
    .choice.right {
        border-color: var(--lsat-good);
        background: var(--lsat-good-soft);
        box-shadow: none;
    }
    .choice.wrong {
        border-color: var(--lsat-bad);
        background: var(--lsat-bad-soft);
        box-shadow: none;
    }
    /* The letter as a circular badge that flips to a filled status chip. */
    .letter {
        flex: 0 0 auto;
        display: grid;
        place-items: center;
        width: 30px;
        height: 30px;
        border-radius: var(--lsat-radius-pill);
        border: 1.5px solid var(--lsat-border);
        background: var(--lsat-surface);
        color: var(--lsat-accent);
        font-weight: 750;
        font-variant-numeric: tabular-nums;
        transition:
            background var(--lsat-transition) var(--lsat-ease),
            border-color var(--lsat-transition) var(--lsat-ease),
            color var(--lsat-transition) var(--lsat-ease);
    }
    .choice:hover:not(:disabled) .letter {
        border-color: var(--lsat-accent);
        background: var(--lsat-accent-soft);
    }
    .choice.chosen .letter {
        background: var(--lsat-accent);
        border-color: var(--lsat-accent);
        color: var(--lsat-ink-on-accent);
    }
    .choice.right .letter {
        background: var(--lsat-good-soft);
        border-color: var(--lsat-good);
        color: var(--lsat-good);
    }
    .choice.wrong .letter {
        background: var(--lsat-bad-soft);
        border-color: var(--lsat-bad);
        color: var(--lsat-bad);
    }
    .text {
        margin-top: 0.15rem;
        line-height: 1.45;
    }
    .next {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        align-self: flex-start;
        min-height: 44px;
        margin-top: 0.3rem;
        padding: 0.55rem 1.2rem;
        border: none;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-hero);
        color: var(--lsat-ink-on-accent);
        font: inherit;
        font-weight: 650;
        cursor: pointer;
        box-shadow: var(--lsat-shadow);
        transition:
            box-shadow var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease);
    }
    .next:hover {
        box-shadow: var(--lsat-glow);
    }
    .next:active {
        transform: scale(0.97);
    }
    .next:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }
    .next .arrow {
        transition: transform var(--lsat-transition) var(--lsat-ease);
    }
    .next:hover .arrow {
        transform: translateX(3px);
    }

    /* Guess + correct: don't celebrate luck — nudge a proof (Skill-or-luck twin). */
    .prove-it {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
        margin-top: 0.3rem;
        padding: 0.6rem 0.8rem;
        border: 1px dashed color-mix(in srgb, var(--lsat-warn) 55%, var(--lsat-border));
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-warn-soft);
        color: var(--lsat-fg);
        font-size: 0.86rem;
        line-height: 1.4;
        text-decoration: none;
        /* it's a <button> now (was a dead <a> to this same route): reset native
         * button chrome so it keeps the card look, and make it full-width + tappable. */
        width: 100%;
        font-family: inherit;
        text-align: left;
        cursor: pointer;
        appearance: none;
    }
    .prove-it:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }
    .prove-it em {
        font-style: italic;
        font-weight: 650;
    }
    .prove-it b {
        color: color-mix(in srgb, var(--lsat-warn) 72%, var(--lsat-fg));
        font-weight: 700;
    }
    /* Sure + wrong: the hypercorrection moment — the strongest, kindest fix gets
     * an accent frame + eyebrow (not a shake). */
    .contrast-wrap.hyper {
        margin-top: 0.3rem;
        padding: 0.55rem;
        border: 1.5px solid color-mix(in srgb, var(--lsat-accent) 45%, transparent);
        border-radius: var(--lsat-radius);
        background: var(--lsat-accent-soft);
    }
    .hyper-eyebrow {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        margin: 0 0 0.5rem;
        font-family: var(--lsat-mono);
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: color-mix(in srgb, var(--lsat-accent) 72%, var(--lsat-fg));
    }
    .hyper-eyebrow .he-mk {
        color: var(--lsat-accent);
    }

    @media (prefers-reduced-motion: reduce) {
        .chip,
        .choice,
        .letter,
        .next,
        .next .arrow {
            transition: none;
        }
        .chip:active,
        .choice:active:not(:disabled),
        .next:active {
            transform: none;
        }
        .next:hover .arrow {
            transform: none;
        }
    }
</style>
