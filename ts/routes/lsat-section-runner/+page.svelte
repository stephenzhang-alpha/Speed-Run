<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Timed Section Runner (DECISION-round4 #17): a self-contained mini-section under
an LSAT-pace clock. It fetches up to SECTION_SIZE items on mount, lets the learner
answer / flag / jump between them, and on submit (or when the clock hits 0) POSTs
the RAW per-question trajectory. Correctness is NEVER revealed during the section
-- the server grades the choices and returns only the aggregate First-Instinct
Ledger, which the results view renders. No per-question right/wrong ever surfaces.
-->
<script lang="ts">
    import "$lib/lsat/theme.scss";

    import { onDestroy, onMount } from "svelte";

    import Card from "$lib/lsat/Card.svelte";
    import * as client from "$lib/lsat/client";
    import type {
        SectionAttemptResult,
        SectionQuestionAttempt,
        StudyItemData,
    } from "$lib/lsat/types";

    const SECTION_SIZE = 10;
    const SECTION_SECONDS = 10 * 84; // 1:24 per question -- LSAT timed pace.

    type State =
        | "loading"
        | "notenough"
        | "running"
        | "submitting"
        | "results"
        | "queued"
        | "error";

    // Per-question state. We hold RAW choices only; correctness is the server's
    // job and never lives on the client during the section (no-leak).
    interface Question {
        item: StudyItemData;
        firstChoice: string;
        finalChoice: string;
        flagged: boolean;
        nChanges: number;
        dwellMs: number;
    }

    let state: State = "loading";
    let questions: Question[] = [];
    let current = 0;
    let remaining = SECTION_SECONDS;
    let result: SectionAttemptResult | null = null;
    let error = "";

    // A single interval drives the countdown; `viewStart` timestamps when the
    // current question became visible so dwell can accumulate across visits.
    let ticker: ReturnType<typeof setInterval> | undefined;
    let viewStart = 0;

    $: cur = questions[current];
    $: mmss = `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")}`;
    $: urgent = state === "running" && remaining <= 60;
    $: answeredCount = questions.filter((q) => q.finalChoice).length;
    $: ledger = result?.ledger;

    async function loadItems(): Promise<void> {
        state = "loading";
        const loaded: Question[] = [];
        const seen = new Set<string>();
        try {
            // A section needs DISTINCT items without submitting answers, so we use
            // the batch endpoint (next_item returns only the single top card and
            // does not advance until an answer is logged -- unusable here).
            const batch = await client.sectionItems(SECTION_SIZE);
            for (const it of batch.items ?? []) {
                if (!it.item_id || seen.has(it.item_id)) {
                    continue;
                }
                seen.add(it.item_id);
                loaded.push({
                    item: it,
                    firstChoice: "",
                    finalChoice: "",
                    flagged: false,
                    nChanges: 0,
                    dwellMs: 0,
                });
            }
        } catch (e) {
            console.error("Failed to load timed section items:", e);
            error =
                "We couldn't load a timed section just now. Please check your connection and try again.";
            state = "error";
            return;
        }
        questions = loaded;
        if (questions.length < 2) {
            state = "notenough";
            return;
        }
        current = 0;
        remaining = SECTION_SECONDS;
        viewStart = Date.now();
        state = "running";
        startTimer();
    }

    function startTimer(): void {
        stopTimer();
        ticker = setInterval(() => {
            remaining -= 1;
            if (remaining <= 0) {
                remaining = 0;
                void submit();
            }
        }, 1000);
    }

    function stopTimer(): void {
        if (ticker !== undefined) {
            clearInterval(ticker);
            ticker = undefined;
        }
    }

    // Bank the time spent on the current question, then re-arm the stopwatch.
    function flushDwell(): void {
        const now = Date.now();
        if (cur) {
            cur.dwellMs += now - viewStart;
        }
        viewStart = now;
    }

    function goto(i: number): void {
        if (state !== "running" || i < 0 || i >= questions.length || i === current) {
            return;
        }
        flushDwell();
        current = i;
    }

    function pick(letter: string): void {
        if (state !== "running" || !cur) {
            return;
        }
        const prev = cur.finalChoice;
        // n_changes counts each switch away from a previous non-empty choice.
        if (prev && prev !== letter) {
            cur.nChanges += 1;
        }
        // The first selection also stamps first_choice.
        if (!cur.firstChoice) {
            cur.firstChoice = letter;
        }
        cur.finalChoice = letter;
        questions = questions;
    }

    function toggleFlag(): void {
        if (state !== "running" || !cur) {
            return;
        }
        cur.flagged = !cur.flagged;
        questions = questions;
    }

    // The built trajectory is held so a transient submit failure can RE-POST the same
    // section (rather than discarding minutes of work and fetching a fresh one).
    let pendingTrajectory: SectionQuestionAttempt[] | null = null;

    async function submit(): Promise<void> {
        // Guard so a manual submit and the timeout can't both fire.
        if (state !== "running") {
            return;
        }
        stopTimer();
        flushDwell();
        pendingTrajectory = questions.map((q) => {
            const reached = !!q.finalChoice;
            return {
                item_id: q.item.item_id,
                // Never answered => reached false, empty choices.
                first_choice: reached ? q.firstChoice : "",
                final_choice: reached ? q.finalChoice : "",
                reached,
                flagged: q.flagged,
                dwell_ms: Math.max(0, Math.round(q.dwellMs)),
                n_changes: q.nChanges,
            };
        });
        await sendTrajectory();
    }

    // Send (or re-send) the built trajectory. Kept separate from submit() so the
    // error card's "Try again" re-POSTs the SAME answers instead of loadItems()
    // discarding them for a new section.
    async function sendTrajectory(): Promise<void> {
        if (!pendingTrajectory) {
            return;
        }
        state = "submitting";
        try {
            result = await client.submitSectionAttempt(pendingTrajectory);
            // Offline: the section was saved to the local queue and will sync + be
            // graded on reconnect (the ledger refreshes then, not now).
            state = result.queued ? "queued" : "results";
            pendingTrajectory = null;
        } catch (e) {
            console.error("Failed to submit timed section:", e);
            error =
                "We couldn't submit your section just now — your answers are kept. Try again.";
            state = "error";
        }
    }

    onMount(loadItems);
    onDestroy(stopTimer);
</script>

<svelte:head>
    <title>Timed section</title>
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1, viewport-fit=cover"
    />
</svelte:head>

<div class="runner">
    <header class="bar">
        <div class="bar-inner">
            <a class="back" href="/lsat-mobile" aria-label="Back to study">
                <span class="arrow" aria-hidden="true">&larr;</span>
                <span class="brand">Timed section</span>
            </a>
            {#if state === "running" || state === "submitting"}
                <div class="controls">
                    <!-- no aria-live: a per-second re-announcement floods the SR queue;
                         the static label conveys the purpose, sighted users see the count. -->
                    <span class="clock" class:urgent aria-label="time remaining {mmss}">
                        {mmss}
                    </span>
                    <button
                        class="submit"
                        type="button"
                        disabled={state === "submitting"}
                        on:click={submit}
                    >
                        {state === "submitting" ? "Submitting…" : "Submit section"}
                    </button>
                </div>
            {/if}
        </div>
    </header>

    <main>
        {#if state === "loading"}
            <Card><p class="muted">Loading a timed section&hellip;</p></Card>
        {:else if state === "submitting"}
            <Card><p class="muted">Grading your section&hellip;</p></Card>
        {:else if state === "notenough"}
            <Card title="Not enough items to run a section">
                <p class="muted">
                    A timed section needs at least two distinct questions, and the queue
                    couldn't hand back enough right now. Study a few more items, then
                    try again.
                </p>
                <a class="link" href="/lsat-mobile">&larr; Back to study</a>
            </Card>
        {:else if state === "error"}
            <Card title="Couldn't run the section">
                <p class="muted">{error}</p>
                <!-- Re-POST the SAME answers if a section was in flight; only fetch a
                     fresh section when the failure was during load (no trajectory). -->
                <button
                    class="link-btn"
                    type="button"
                    on:click={() =>
                        pendingTrajectory ? sendTrajectory() : loadItems()}
                >
                    Try again
                </button>
            </Card>
        {:else if state === "queued"}
            <Card title="Section saved offline">
                <p class="muted" aria-live="polite">
                    You're offline &mdash; your section is saved on this device and will
                    sync and be graded automatically when you reconnect. Your
                    first-instinct ledger updates then.
                </p>
                <a class="link-btn" href="/lsat-mobile">Back to study</a>
            </Card>
        {:else if state === "results"}
            {#if result?.ok && ledger}
                <Card title="Section complete" subtitle="Your first-instinct ledger">
                    <p class="lead">
                        {ledger.direction === "abstain"
                            ? (ledger.reason ?? "")
                            : (ledger.headline ?? "")}
                    </p>
                    <div class="split">
                        <div class="count s-good">
                            <span class="n">{ledger.wrong_to_right ?? 0}</span>
                            <span class="clab">wrong &rarr; right</span>
                        </div>
                        <div class="count s-warn">
                            <span class="n">{ledger.right_to_wrong ?? 0}</span>
                            <span class="clab">right &rarr; wrong</span>
                        </div>
                    </div>
                    {#if ledger.framing}<p class="framing">{ledger.framing}</p>{/if}
                    <a class="link" href="/lsat-mobile">&larr; Back to study</a>
                </Card>
            {:else}
                <Card title="Couldn't submit the section">
                    <p class="muted">{result?.reason ?? error}</p>
                    <a class="link" href="/lsat-mobile">&larr; Back to study</a>
                </Card>
            {/if}
        {:else if state === "running" && cur}
            <div class="palette" role="group" aria-label="Question navigator">
                {#each questions as q, i (q.item.item_id)}
                    <button
                        type="button"
                        class="dot"
                        class:answered={!!q.finalChoice}
                        class:flagged={q.flagged}
                        class:current={i === current}
                        aria-label={`Question ${i + 1}${q.finalChoice ? ", answered" : ""}${
                            q.flagged ? ", flagged" : ""
                        }`}
                        aria-current={i === current ? "true" : undefined}
                        on:click={() => goto(i)}
                    >
                        {i + 1}
                        {#if q.flagged}<span class="pin" aria-hidden="true">
                                &#9873;
                            </span>{/if}
                    </button>
                {/each}
            </div>

            <Card>
                <div class="qhead">
                    <span class="qnum">
                        Question {current + 1} of {questions.length}
                    </span>
                    <button
                        type="button"
                        class="flag"
                        class:on={cur.flagged}
                        aria-pressed={cur.flagged}
                        on:click={toggleFlag}
                    >
                        <span class="pin" aria-hidden="true">&#9873;</span>
                        {cur.flagged ? "Flagged" : "Flag"}
                    </button>
                </div>

                <div class="stem">{cur.item.stem}</div>

                <div class="choices">
                    {#each cur.item.choices as c (c.letter)}
                        <button
                            type="button"
                            class="choice"
                            class:chosen={cur.finalChoice === c.letter}
                            aria-pressed={cur.finalChoice === c.letter}
                            on:click={() => pick(c.letter)}
                        >
                            <span class="letter">{c.letter}</span>
                            <span class="text">{c.text}</span>
                        </button>
                    {/each}
                </div>

                <div class="nav">
                    <button
                        type="button"
                        class="step"
                        class:atbound={current === 0}
                        aria-disabled={current === 0}
                        on:click={() => goto(current - 1)}
                    >
                        <span aria-hidden="true">&larr;</span>
                        Prev
                    </button>
                    <span class="progress">
                        {answeredCount}/{questions.length} answered
                    </span>
                    <button
                        type="button"
                        class="step"
                        class:atbound={current === questions.length - 1}
                        aria-disabled={current === questions.length - 1}
                        on:click={() => goto(current + 1)}
                    >
                        Next <span aria-hidden="true">&rarr;</span>
                    </button>
                </div>
            </Card>
        {/if}
    </main>
</div>

<style lang="scss">
    :global(html),
    :global(body) {
        margin: 0;
        background: var(--lsat-canvas);
    }
    .runner {
        display: flex;
        flex-direction: column;
        min-height: 100dvh;
        background: var(--lsat-bg);
        color: var(--lsat-fg);
        font-size: 15px;
    }
    .bar {
        position: sticky;
        top: 0;
        z-index: 5;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.6rem;
        padding: calc(env(safe-area-inset-top, 0px) + 0.7rem) 1rem 0.7rem;
        background: var(--lsat-surface);
        border-bottom: 1px solid var(--lsat-border-subtle);
        box-shadow: var(--lsat-shadow);
    }
    .bar-inner {
        width: 100%;
        max-width: 960px;
        margin: 0 auto;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.6rem;
    }
    .back {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        min-width: 0;
        color: var(--lsat-fg);
        text-decoration: none;
        font-weight: 700;
        letter-spacing: -0.015em;
    }
    .back .arrow {
        color: var(--lsat-fg-subtle);
        transition: transform var(--lsat-transition) var(--lsat-ease);
    }
    .back:hover .arrow {
        transform: translateX(-3px);
    }
    .brand {
        font-size: 1.02rem;
    }
    .controls {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        flex: 0 0 auto;
    }
    /* Monospaced-numeral countdown; turns to the warn colour in the last minute. */
    .clock {
        padding: 0.22rem 0.62rem;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-inset);
        border: 1px solid var(--lsat-border-subtle);
        font-size: 0.95rem;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
        color: var(--lsat-fg);
    }
    .clock.urgent {
        color: var(--lsat-bad);
        background: var(--lsat-bad-soft);
        border-color: transparent;
    }
    .submit {
        min-height: 40px;
        padding: 0.45rem 1rem;
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
    .submit:hover:not(:disabled) {
        box-shadow: var(--lsat-glow);
    }
    .submit:active:not(:disabled) {
        transform: scale(0.97);
    }
    .submit:disabled {
        opacity: 0.65;
        cursor: default;
    }
    .submit:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }
    main {
        flex: 1 1 auto;
        width: 100%;
        max-width: 960px;
        margin: 0 auto;
        padding: 0.9rem 0.9rem 1.6rem;
    }
    .muted {
        color: var(--lsat-fg-subtle);
        margin: 0;
    }

    /* Question palette: one tappable dot per question, showing answered / flagged
     * / current state so the learner can jump anywhere in the section. */
    .palette {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-bottom: 0.7rem;
    }
    .dot {
        position: relative;
        min-width: 40px;
        min-height: 40px;
        padding: 0 0.4rem;
        border: 1.5px solid var(--lsat-border);
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-surface);
        color: var(--lsat-fg);
        font: inherit;
        font-weight: 650;
        font-variant-numeric: tabular-nums;
        cursor: pointer;
        transition:
            border-color var(--lsat-transition) var(--lsat-ease),
            background var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease);
    }
    .dot:hover {
        border-color: var(--lsat-accent);
    }
    .dot:active {
        transform: scale(0.94);
    }
    .dot:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }
    /* Answered dots read as "done" (accent wash) -- NOT correctness (no-leak). */
    .dot.answered {
        border-color: var(--lsat-accent);
        background: var(--lsat-accent-soft);
        color: var(--lsat-accent);
    }
    .dot.current {
        border-color: var(--lsat-accent);
        box-shadow: var(--lsat-ring);
    }
    .dot.flagged {
        border-color: var(--lsat-warn);
    }
    .dot .pin {
        position: absolute;
        top: -6px;
        right: -4px;
        font-size: 0.7rem;
        color: var(--lsat-warn);
    }

    .qhead {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.6rem;
    }
    .qnum {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--lsat-fg-faint);
    }
    .flag {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        min-height: 34px;
        padding: 0.28rem 0.7rem;
        border-radius: var(--lsat-radius-pill);
        border: 1px solid var(--lsat-border);
        background: var(--lsat-surface);
        color: var(--lsat-fg-subtle);
        font: inherit;
        font-size: 0.78rem;
        font-weight: 600;
        cursor: pointer;
        transition:
            border-color var(--lsat-transition) var(--lsat-ease),
            background var(--lsat-transition) var(--lsat-ease),
            color var(--lsat-transition) var(--lsat-ease);
    }
    .flag:hover {
        border-color: var(--lsat-warn);
    }
    .flag.on {
        border-color: var(--lsat-warn);
        background: var(--lsat-warn-soft);
        color: var(--lsat-warn);
    }
    .flag:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }

    .stem {
        white-space: pre-wrap;
        font-size: 1.02rem;
        line-height: 1.58;
        color: var(--lsat-fg);
        padding-left: 0.85rem;
        background: var(--lsat-hero) left top / 3px 100% no-repeat;
        border-radius: 2px;
    }

    .choices {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        margin-top: 0.4rem;
    }
    /* Choices carry ONLY a "chosen" state -- never right/wrong -- during a section. */
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
    .choice:hover {
        border-color: var(--lsat-accent);
        box-shadow: var(--lsat-shadow);
    }
    .choice:active {
        transform: scale(0.99);
    }
    .choice.chosen {
        border-color: var(--lsat-accent);
        box-shadow: var(--lsat-glow);
    }
    .choice:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }
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
    .choice:hover .letter {
        border-color: var(--lsat-accent);
        background: var(--lsat-accent-soft);
    }
    .choice.chosen .letter {
        background: var(--lsat-accent);
        border-color: var(--lsat-accent);
        color: #fff;
    }
    .text {
        margin-top: 0.15rem;
        line-height: 1.45;
    }

    .nav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.6rem;
        margin-top: 0.3rem;
    }
    .step {
        min-height: 40px;
        padding: 0.45rem 0.9rem;
        border: 1px solid var(--lsat-border);
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-surface);
        color: var(--lsat-fg);
        font: inherit;
        font-weight: 600;
        font-size: 0.85rem;
        cursor: pointer;
        transition:
            border-color var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease);
    }
    .step:hover:not(.atbound) {
        border-color: var(--lsat-accent);
    }
    .step:active:not(.atbound) {
        transform: scale(0.97);
    }
    .step.atbound {
        opacity: 0.4;
        cursor: default;
    }
    .step:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }
    .progress {
        font-size: 0.78rem;
        color: var(--lsat-fg-subtle);
        font-variant-numeric: tabular-nums;
    }

    /* Results: the aggregate ledger only -- no per-question correctness ever. */
    .lead {
        margin: 0;
        font-size: 0.95rem;
        line-height: 1.5;
        color: var(--lsat-fg);
    }
    .split {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.5rem;
        margin-top: 0.2rem;
    }
    .count {
        display: flex;
        flex-direction: column;
        gap: 0.1rem;
        padding: 0.6rem 0.75rem;
        border-radius: var(--lsat-radius-sm);
        border: 1px solid var(--lsat-border-subtle);
        background: var(--lsat-inset);
    }
    .count.s-good {
        background: var(--lsat-good-soft);
    }
    .count.s-warn {
        background: var(--lsat-warn-soft);
    }
    .n {
        font-size: 1.6rem;
        font-weight: 750;
        line-height: 1;
        font-variant-numeric: tabular-nums;
    }
    .count.s-good .n {
        color: var(--lsat-good);
    }
    .count.s-warn .n {
        color: var(--lsat-warn);
    }
    .clab {
        font-size: 0.74rem;
        color: var(--lsat-fg-subtle);
    }
    .framing {
        margin: 0.1rem 0 0;
        font-size: 0.72rem;
        line-height: 1.4;
        color: var(--lsat-fg-faint);
    }
    .link {
        align-self: flex-start;
        margin-top: 0.2rem;
        color: var(--lsat-accent);
        text-decoration: none;
        font-weight: 650;
        font-size: 0.88rem;
    }
    .link:hover {
        text-decoration: underline;
    }
    .link-btn {
        align-self: flex-start;
        min-height: 40px;
        padding: 0.5rem 1.1rem;
        border: none;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-hero);
        color: var(--lsat-ink-on-accent);
        font: inherit;
        font-weight: 650;
        cursor: pointer;
        box-shadow: var(--lsat-shadow);
    }
    .link-btn:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }

    @media (prefers-reduced-motion: reduce) {
        .back .arrow,
        .submit,
        .dot,
        .flag,
        .choice,
        .letter,
        .step {
            transition: none;
        }
        .submit:active:not(:disabled),
        .dot:active,
        .choice:active,
        .step:active:not(.atbound) {
            transform: none;
        }
        .back:hover .arrow {
            transform: none;
        }
    }
</style>
