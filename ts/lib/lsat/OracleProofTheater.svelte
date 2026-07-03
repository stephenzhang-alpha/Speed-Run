<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

ORACLE PROOF THEATER — the marquee, offline-demoable AI feature.

A *recorded* model draft of a conditional-chain derivation is replayed and checked
LIVE, step by step, by the exact material-entailment oracle our tests run
(lsat.conditional_chain.entails via lsat.worked_example). Most steps verify and
resolve to a ✓ "entails" pill; the one planted hallucination flips to
"✗ does not follow — blocked" with the oracle's verbatim reason, and then the
oracle substitutes the continuation it can prove. The AI's WORDS are a committed
recording; every VERDICT is computed at request time server-side — nothing baked.

Tagline: "Watch the AI get overruled." Self-fetches via client.oracleTheater();
no props, no page mount here (the coordinator mounts <OracleProofTheater/>).
Motion is transform/opacity only; prefers-reduced-motion disables auto-play and
offers a "Step through ▸" control, with an aria-live region mirroring each beat.
-->
<script lang="ts">
    import { onDestroy, onMount, tick } from "svelte";

    import * as client from "./client";
    import ProvenanceBadge from "./ProvenanceBadge.svelte";
    import type {
        OracleTheater,
        OracleTheaterCorrectedStep,
        OracleTheaterScenario,
        OracleTheaterStep,
    } from "./types";

    type State =
        | "loading"
        | "poster"
        | "drafting"
        | "checking"
        | "vetoed"
        | "corrected"
        | "receipt"
        | "error";

    // One renderable beat of the replay: a recorded draft step, or a step the
    // oracle substituted after the veto.
    type Beat =
        | { type: "draft"; step: OracleTheaterStep }
        | { type: "fix"; corrected: OracleTheaterCorrectedStep };

    let data: OracleTheater | null = null;
    let state: State = "loading";
    let error = "";

    let idx = 0; // selected scenario
    let started = false; // has the current run begun?
    let revealed = 0; // how many beats are shown
    let reduceMotion = false;
    let liveMsg = ""; // mirrored into the aria-live region
    let timer: ReturnType<typeof setTimeout> | null = null;

    const radios: HTMLButtonElement[] = [];
    let mql: MediaQueryList | null = null;

    $: current = data && data.scenarios.length ? data.scenarios[idx] : null;
    $: chipLabel =
        data?.mode === "live" ? "live model draft" : "recorded · replayed offline";
    $: beats = buildBeats(current);
    $: blockedBeatIndex = current
        ? current.steps.findIndex((s) => s.blocked)
        : -1;
    $: running = started && state !== "receipt";
    function labelFor(hasStarted: boolean, st: string): string {
        if (!hasStarted) {
            return "Run the verifier ▶";
        }
        return st === "receipt" ? "Run again ▶" : "Running…";
    }
    $: runLabel = labelFor(started, state);

    function buildBeats(sc: OracleTheaterScenario | null): Beat[] {
        if (!sc) {
            return [];
        }
        return [
            ...sc.steps.map((step): Beat => ({ type: "draft", step })),
            ...sc.corrected.map(
                (corrected): Beat => ({ type: "fix", corrected }),
            ),
        ];
    }

    function clearTimer(): void {
        if (timer) {
            clearTimeout(timer);
            timer = null;
        }
    }

    // Derive the fine-grained state from how far the replay has progressed. The
    // sequence is drafting → checking → vetoed → corrected → receipt.
    function syncState(): void {
        if (!started) {
            state = "poster";
            return;
        }
        if (revealed >= beats.length) {
            state = "receipt";
            return;
        }
        if (revealed === 0) {
            state = "drafting";
        } else if (revealed <= blockedBeatIndex) {
            state = "checking";
        } else if (revealed === blockedBeatIndex + 1) {
            state = "vetoed";
        } else {
            state = "corrected";
        }
    }

    function announce(): void {
        if (!started || !current) {
            liveMsg = "";
            return;
        }
        if (revealed === 0) {
            liveMsg = `${chipLabel}. Checking ${current.steps.length} proposed steps against the oracle.`;
            return;
        }
        if (revealed >= beats.length) {
            liveMsg = `Proof complete. ${current.receipt.note}`;
            return;
        }
        const b = beats[revealed - 1];
        if (b.type === "draft") {
            liveMsg = b.step.blocked
                ? `Step ${b.step.n} blocked. ${b.step.reason ?? ""}`
                : `Step ${b.step.n} verified: ${b.step.claim}. Entails.`;
        } else {
            liveMsg = `Oracle substitutes ${b.corrected.claim}, from ${b.corrected.cited}.`;
        }
    }

    function scheduleNext(): void {
        if (revealed >= beats.length) {
            clearTimer();
            return;
        }
        // Linger a beat longer right before the veto lands, and before the receipt.
        const nextIsBlocked = revealed === blockedBeatIndex;
        const delay = nextIsBlocked ? 950 : 680;
        timer = setTimeout(() => {
            revealed += 1;
            syncState();
            announce();
            scheduleNext();
        }, delay);
    }

    function run(): void {
        clearTimer();
        started = true;
        revealed = 0;
        syncState();
        announce();
        // prefers-reduced-motion: no auto-play — the learner drives it manually.
        if (!reduceMotion) {
            scheduleNext();
        }
    }

    function step(): void {
        if (revealed >= beats.length) {
            return;
        }
        revealed += 1;
        syncState();
        announce();
    }

    function resetCascade(): void {
        clearTimer();
        started = false;
        revealed = 0;
        liveMsg = "";
        state = "poster";
    }

    async function select(i: number, focusEl = false): Promise<void> {
        idx = i;
        resetCascade();
        if (focusEl) {
            await tick();
            radios[i]?.focus();
        }
    }

    function onRadioKey(e: KeyboardEvent): void {
        if (!data) {
            return;
        }
        const n = data.scenarios.length;
        if (e.key === "ArrowRight" || e.key === "ArrowDown") {
            e.preventDefault();
            void select((idx + 1) % n, true);
        } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
            e.preventDefault();
            void select((idx - 1 + n) % n, true);
        }
    }

    async function load(): Promise<void> {
        state = "loading";
        error = "";
        try {
            const d = await client.oracleTheater();
            if (!d.scenarios.length) {
                data = d;
                error = "No scenarios available.";
                state = "error";
                return;
            }
            data = d;
            idx = 0;
            resetCascade();
        } catch (e) {
            error = String(e);
            state = "error";
        }
    }

    onMount(() => {
        if (typeof window !== "undefined" && window.matchMedia) {
            mql = window.matchMedia("(prefers-reduced-motion: reduce)");
            reduceMotion = mql.matches;
            mql.addEventListener("change", onMotionChange);
        }
        void load();
    });

    function onMotionChange(e: MediaQueryListEvent): void {
        reduceMotion = e.matches;
    }

    onDestroy(() => {
        clearTimer();
        mql?.removeEventListener("change", onMotionChange);
    });
</script>

<section class="theater" aria-labelledby="opt-title">
    <div class="poster">
        <span class="eyebrow">VERIFIED AI</span>
        <h2 id="opt-title">Watch the AI get overruled</h2>
        <p class="dek">
            A recorded model draft, checked <strong>live</strong> — one step at a time —
            by the same decision procedure our tests run. The words are a recording;
            the verdicts are computed right now. No API key.
        </p>

        {#if data && data.scenarios.length}
            <div class="switch" role="radiogroup" aria-label="Choose a scenario">
                {#each data.scenarios as sc, i (sc.id)}
                    <button
                        type="button"
                        role="radio"
                        aria-checked={i === idx}
                        tabindex={i === idx ? 0 : -1}
                        class="tab"
                        class:on={i === idx}
                        bind:this={radios[i]}
                        on:click={() => select(i)}
                        on:keydown={onRadioKey}
                    >
                        {sc.title}
                    </button>
                {/each}
            </div>

            <button class="run" type="button" on:click={run} disabled={running}>
                {runLabel}
            </button>
        {/if}
    </div>

    {#if state === "loading"}
        <p class="muted">Loading&hellip;</p>
    {:else if state === "error"}
        <div class="stage">
            <p class="muted">{error}</p>
            <button class="run" type="button" on:click={load}>Try again</button>
        </div>
    {:else if current}
        <div class="stage" class:vetoed={state === "vetoed"}>
            <div class="frame">
                <div class="block">
                    <span class="lbl">Premises</span>
                    <ul class="premises">
                        {#each current.premises as p (p)}
                            <li class="mono">{p}</li>
                        {/each}
                    </ul>
                </div>
                <div class="goalrow">
                    <span class="lbl">Prove</span>
                    <span class="mono goal">{current.goal}</span>
                </div>
            </div>

            {#if started}
                <div class="draftbar">
                    <span class="aichip">AI draft</span>
                    <span class="prov">{chipLabel}</span>
                </div>

                <ol class="steps">
                    {#each beats as b, i (i)}
                        {#if i < revealed}
                            {#if b.type === "draft"}
                                <li
                                    class="step"
                                    class:blocked={b.step.blocked}
                                >
                                    <div class="row">
                                        <span class="claim mono">{b.step.claim}</span>
                                        {#if b.step.blocked}
                                            <span class="pill bad">✗ does not follow — blocked</span>
                                        {:else}
                                            <span class="pill ok">✓ entails</span>
                                        {/if}
                                    </div>
                                    <span class="cite mono">{b.step.cited}</span>
                                    {#if b.step.blocked && b.step.reason}
                                        <p class="reason">{b.step.reason}</p>
                                    {/if}
                                </li>
                            {:else}
                                <li class="step fix">
                                    <div class="row">
                                        <span class="oraclechip">oracle</span>
                                        <span class="claim mono">{b.corrected.claim}</span>
                                        <span class="pill ok">✓ proven</span>
                                    </div>
                                    <span class="cite mono">{b.corrected.cited}</span>
                                </li>
                            {/if}
                        {/if}
                    {/each}
                </ol>

                {#if reduceMotion && revealed < beats.length}
                    <button class="stepper" type="button" on:click={step}>
                        Step through ▸
                    </button>
                {/if}

                {#if state === "receipt"}
                    <div class="receipt">
                        <ProvenanceBadge tier="proven" label="Proven live" />
                        <p class="rnote">{current.receipt.note}</p>
                    </div>
                {/if}
            {/if}
        </div>
    {/if}

    <!-- Screen-reader mirror of every beat + the veto reason, verbatim. -->
    <p class="sr-only" aria-live="polite">{liveMsg}</p>
</section>

<style lang="scss">
    .theater {
        display: flex;
        flex-direction: column;
        gap: var(--lsat-gap);
        padding: var(--lsat-pad);
        border-radius: var(--lsat-radius);
        background: var(--lsat-surface);
        box-shadow: var(--lsat-elev-evidence);
        color: var(--lsat-fg);
    }

    .poster {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .eyebrow {
        align-self: flex-start;
        padding: 0.15rem 0.55rem;
        font-family: var(--lsat-mono);
        font-size: 0.66rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        color: color-mix(in srgb, var(--lsat-accent) 74%, var(--lsat-fg));
        background: var(--lsat-accent-soft);
        border-radius: var(--lsat-radius-pill);
    }
    h2 {
        margin: 0;
        font-size: clamp(1.35rem, 1.1rem + 1.4vw, 1.8rem);
        font-weight: 750;
        line-height: 1.15;
        letter-spacing: -0.01em;
    }
    .dek {
        margin: 0;
        max-width: 60ch;
        font-size: 0.9rem;
        line-height: 1.5;
        color: var(--lsat-fg-subtle);
    }
    .dek strong {
        color: var(--lsat-fg);
        font-weight: 700;
    }

    .switch {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-top: 0.3rem;
    }
    .tab {
        padding: 0.4rem 0.8rem;
        font: inherit;
        font-size: 0.82rem;
        font-weight: 600;
        color: var(--lsat-fg-subtle);
        background: var(--lsat-inset);
        border: 1px solid var(--lsat-border-subtle);
        border-radius: var(--lsat-radius-pill);
        cursor: pointer;
        transition:
            color var(--lsat-transition) var(--lsat-ease),
            border-color var(--lsat-transition) var(--lsat-ease);
    }
    .tab:hover {
        border-color: var(--lsat-accent);
    }
    .tab.on {
        color: color-mix(in srgb, var(--lsat-accent) 78%, var(--lsat-fg));
        background: var(--lsat-accent-soft);
        border-color: color-mix(in srgb, var(--lsat-accent) 45%, transparent);
    }
    .tab:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }

    .run {
        align-self: flex-start;
        min-height: 44px;
        margin-top: 0.4rem;
        padding: 0.55rem 1.15rem;
        border: none;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-proven);
        color: #fff;
        font: inherit;
        font-weight: 700;
        letter-spacing: 0.01em;
        cursor: pointer;
        box-shadow: var(--lsat-glow);
        transition: transform var(--lsat-transition) var(--lsat-ease);
    }
    .run:hover:not(:disabled) {
        transform: translateY(-1px);
    }
    .run:disabled {
        cursor: default;
        opacity: 0.7;
        box-shadow: none;
    }
    .run:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }

    .muted {
        margin: 0;
        color: var(--lsat-fg-subtle);
    }

    .stage {
        display: flex;
        flex-direction: column;
        gap: 0.7rem;
    }

    .frame {
        display: flex;
        flex-direction: column;
        gap: 0.55rem;
        padding: 0.75rem 0.85rem;
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-inset);
        background-image: var(--lsat-graph);
    }
    .lbl {
        display: block;
        font-size: 0.66rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--lsat-fg-subtle);
    }
    .premises {
        margin: 0.3rem 0 0;
        padding: 0;
        list-style: none;
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
    }
    .mono {
        font-family: var(--lsat-mono);
    }
    .premises li {
        font-size: 0.88rem;
        line-height: 1.4;
    }
    .goalrow {
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
        padding-top: 0.5rem;
        border-top: 1px dashed var(--lsat-border-subtle);
    }
    .goal {
        font-size: 0.98rem;
        font-weight: 700;
    }

    .draftbar {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .aichip {
        padding: 0.2rem 0.6rem;
        font-family: var(--lsat-mono);
        font-size: 0.72rem;
        font-weight: 700;
        color: color-mix(in srgb, var(--lsat-accent-2) 68%, var(--lsat-fg));
        background: color-mix(in srgb, var(--lsat-accent-2) 14%, transparent);
        border: 1px solid color-mix(in srgb, var(--lsat-accent-2) 42%, transparent);
        border-radius: var(--lsat-radius-pill);
    }
    .prov {
        font-family: var(--lsat-mono);
        font-size: 0.72rem;
        color: var(--lsat-fg-faint);
    }

    .steps {
        margin: 0;
        padding: 0;
        list-style: none;
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
    }
    .step {
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
        padding: 0.55rem 0.7rem;
        border: 1px solid var(--lsat-border-subtle);
        border-left: var(--lsat-rail-w) solid var(--lsat-good);
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-surface);
        animation: riseIn 240ms var(--lsat-ease) both;
    }
    .step.blocked {
        border-left-color: var(--lsat-bad);
        background: var(--lsat-bad-soft);
    }
    .step.fix {
        border-left-color: var(--lsat-accent);
        border-left-style: dashed;
    }
    .row {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .claim {
        font-size: 0.98rem;
        font-weight: 700;
        letter-spacing: 0.01em;
    }
    .step.blocked .claim {
        text-decoration: line-through;
        text-decoration-thickness: 2px;
        color: color-mix(in srgb, var(--lsat-bad) 60%, var(--lsat-fg));
    }
    .cite {
        font-size: 0.8rem;
        color: var(--lsat-fg-subtle);
    }
    .oraclechip {
        padding: 0.1rem 0.45rem;
        font-family: var(--lsat-mono);
        font-size: 0.66rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        color: color-mix(in srgb, var(--lsat-accent) 74%, var(--lsat-fg));
        background: var(--lsat-accent-soft);
        border-radius: var(--lsat-radius-pill);
    }

    .pill {
        margin-left: auto;
        padding: 0.18rem 0.55rem;
        font-family: var(--lsat-mono);
        font-size: 0.72rem;
        font-weight: 700;
        white-space: nowrap;
        border: 1px solid;
        border-radius: var(--lsat-radius-pill);
    }
    .pill.ok {
        color: color-mix(in srgb, var(--lsat-good) 72%, var(--lsat-fg));
        background: var(--lsat-good-soft);
        border-color: color-mix(in srgb, var(--lsat-good) 40%, transparent);
    }
    .pill.bad {
        color: color-mix(in srgb, var(--lsat-bad) 68%, var(--lsat-fg));
        background: color-mix(in srgb, var(--lsat-bad) 20%, transparent);
        border-color: color-mix(in srgb, var(--lsat-bad) 46%, transparent);
        animation: flipIn 320ms var(--lsat-ease) both;
    }
    .reason {
        margin: 0.1rem 0 0;
        font-size: 0.84rem;
        line-height: 1.45;
        color: color-mix(in srgb, var(--lsat-bad) 55%, var(--lsat-fg));
    }

    .stepper {
        align-self: flex-start;
        min-height: 40px;
        padding: 0.45rem 0.95rem;
        font: inherit;
        font-weight: 650;
        color: var(--lsat-fg);
        background: var(--lsat-inset);
        border: 1px solid var(--lsat-border);
        border-radius: var(--lsat-radius-pill);
        cursor: pointer;
    }
    .stepper:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }

    .receipt {
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
        padding: 0.7rem 0.8rem;
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-good-soft);
        animation: riseIn 260ms var(--lsat-ease) both;
    }
    .rnote {
        margin: 0;
        font-size: 0.84rem;
        line-height: 1.45;
        color: color-mix(in srgb, var(--lsat-good) 40%, var(--lsat-fg));
    }

    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }

    @keyframes riseIn {
        from {
            opacity: 0;
            transform: translateY(6px);
        }
        to {
            opacity: 1;
            transform: none;
        }
    }
    @keyframes flipIn {
        from {
            opacity: 0;
            transform: rotateX(80deg);
        }
        to {
            opacity: 1;
            transform: rotateX(0);
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .run:hover:not(:disabled) {
            transform: none;
        }
        .step,
        .pill.bad,
        .receipt {
            animation: none;
        }
    }
</style>
