<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

ORACLE PROOF THEATER — the marquee, offline-demoable AI feature, now interactive.

Three modes over the same conditional-chain scenarios, all judged by the exact
material-entailment oracle our tests run (lsat.conditional_chain.entails via
lsat.worked_example — the LLM/user only ever PROPOSE; the oracle DISPOSES):

  • Watch — a *recorded* model draft is replayed and checked LIVE, step by step.
    The one planted hallucination flips to "✗ blocked" with the oracle's reason
    (and, when the claim genuinely fails, a concrete counterexample world), then
    the oracle substitutes the continuation it can prove. "Watch the AI get overruled."
  • Your turn — the learner assembles the proof from the scenario's closed set of
    premise edges; every pick is oracle-checked instantly. Try to sneak a bad step
    past the checker — you can't.
  • Draft it live — when a model key is present, the REAL model drafts the moves and
    the oracle checks them live (degrades to the recorded draft when AI is off).

The AI's words are a recording (Watch) or a live proposal (Draft it live); every
VERDICT is computed at request time server-side — nothing baked. Self-fetches via
client.oracleTheater(); no props. Motion is transform/opacity only;
prefers-reduced-motion disables auto-play and offers a "Step through ▸" control,
with an aria-live region mirroring each beat.
-->
<script lang="ts">
    import { onDestroy, onMount, tick } from "svelte";

    import * as client from "./client";
    import ProvenanceBadge from "./ProvenanceBadge.svelte";
    import type {
        OracleTheater,
        OracleTheaterCorrectedStep,
        OracleTheaterMove,
        OracleTheaterScenario,
        OracleTheaterStep,
        ProveStepResult,
    } from "./types";

    type View = "recorded" | "prove" | "live";

    type State =
        | "loading"
        | "poster"
        | "drafting"
        | "checking"
        | "vetoed"
        | "corrected"
        | "receipt"
        | "error";

    // One renderable beat of the replay: a recorded/live draft step, or a step the
    // oracle substituted after the veto.
    type Beat =
        | { type: "draft"; step: OracleTheaterStep }
        | { type: "fix"; corrected: OracleTheaterCorrectedStep };

    let data: OracleTheater | null = null;
    let state: State = "loading";
    let error = "";
    let view: View = "recorded";

    let idx = 0; // selected scenario
    let started = false; // has the current replay begun?
    let revealed = 0; // how many beats are shown
    let reduceMotion = false;
    let liveMsg = ""; // mirrored into the aria-live region
    let timer: ReturnType<typeof setTimeout> | null = null;

    const radios: HTMLButtonElement[] = [];
    let mql: MediaQueryList | null = null;

    // "Draft it live": the real model's draft, replayed through the oracle.
    let liveScenario: OracleTheaterScenario | null = null;
    let liveState: "idle" | "drafting" | "error" = "idle";
    let liveError = "";

    // "Your turn": the learner-built proof, oracle-checked move by move.
    let builtMoves: { premise_index: number; contrapositive: boolean }[] = [];
    let proveResult: ProveStepResult | null = null;
    let proveBusy = false;
    let proveError = "";

    $: recordedScenario = data && data.scenarios.length ? data.scenarios[idx] : null;
    // The replay (Watch / Draft it live) runs on this; the builder uses the recorded
    // scenario's chain + closed move options.
    $: activeScenario = view === "live" ? liveScenario : recordedScenario;
    $: frameScenario = activeScenario ?? recordedScenario;
    $: chipLabel =
        activeScenario?.provenance === "live"
            ? `live model draft${activeScenario?.model_used ? ` · ${activeScenario.model_used}` : ""}`
            : "recorded · replayed offline";
    $: beats = buildBeats(activeScenario);
    $: blockedBeatIndex = activeScenario
        ? activeScenario.steps.findIndex((s) => s.blocked)
        : -1;
    $: running = started && state !== "receipt";
    function labelFor(hasStarted: boolean, st: string): string {
        if (!hasStarted) {
            return "Run the verifier ▶";
        }
        return st === "receipt" ? "Run again ▶" : "Running…";
    }
    $: runLabel = labelFor(started, state);

    // Builder-derived state.
    $: proveSteps = proveResult?.steps ?? [];
    $: lastStepBlocked = proveSteps.some((s) => s.blocked);
    $: proved = !!proveResult?.proved;
    $: currentFrontier = proveResult?.frontier ?? recordedScenario?.start ?? "";

    function buildBeats(sc: OracleTheaterScenario | null): Beat[] {
        if (!sc) {
            return [];
        }
        return [
            ...sc.steps.map((step): Beat => ({ type: "draft", step })),
            ...sc.corrected.map((corrected): Beat => ({ type: "fix", corrected })),
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
        } else if (blockedBeatIndex < 0) {
            state = "checking";
        } else if (revealed <= blockedBeatIndex) {
            state = "checking";
        } else if (revealed === blockedBeatIndex + 1) {
            state = "vetoed";
        } else {
            state = "corrected";
        }
    }

    function announce(): void {
        if (!started || !activeScenario) {
            liveMsg = "";
            return;
        }
        if (revealed === 0) {
            liveMsg = `${chipLabel}. Checking ${activeScenario.steps.length} proposed steps against the oracle.`;
            return;
        }
        if (revealed >= beats.length) {
            liveMsg = `Proof complete. ${activeScenario.receipt.note}`;
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

    // Switch mode (Watch / Your turn / Draft it live), resetting the others.
    function setView(v: View): void {
        if (v === view) {
            return;
        }
        view = v;
        resetCascade();
        if (v !== "live") {
            liveScenario = null;
            liveState = "idle";
            liveError = "";
        }
        resetProve();
    }

    async function select(i: number, focusEl = false): Promise<void> {
        idx = i;
        resetCascade();
        liveScenario = null;
        liveState = "idle";
        liveError = "";
        resetProve();
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

    // "Draft it live": fetch a real model draft, then replay it through the oracle.
    async function draftLive(): Promise<void> {
        if (!recordedScenario) {
            return;
        }
        resetCascade();
        liveState = "drafting";
        liveError = "";
        liveScenario = null;
        try {
            const res = await client.oracleDraftLive(recordedScenario.id);
            if (!res.ok || !res.scenario) {
                liveError = res.reason ?? "Live draft unavailable.";
                liveState = "error";
                return;
            }
            liveScenario = res.scenario;
            liveState = "idle";
            await tick(); // let `beats`/`activeScenario` recompute before replaying
            run();
        } catch (e) {
            liveError = String(e);
            liveState = "error";
        }
    }

    // "Your turn": append a picked move and re-check the whole derivation live.
    function resetProve(): void {
        builtMoves = [];
        proveResult = null;
        proveBusy = false;
        proveError = "";
    }

    async function pickMove(opt: OracleTheaterMove): Promise<void> {
        if (!recordedScenario || proveBusy || proved || lastStepBlocked) {
            return;
        }
        const next = [
            ...builtMoves,
            { premise_index: opt.premise_index, contrapositive: opt.contrapositive },
        ];
        proveBusy = true;
        proveError = "";
        try {
            const res = await client.proveStep(recordedScenario.id, next);
            if (!res.ok) {
                proveError = res.reason ?? "Could not check that move.";
                return;
            }
            builtMoves = next;
            proveResult = res;
            announceProve();
        } catch (e) {
            proveError = String(e);
        } finally {
            proveBusy = false;
        }
    }

    async function undoMove(): Promise<void> {
        if (!recordedScenario || !builtMoves.length || proveBusy) {
            return;
        }
        const next = builtMoves.slice(0, -1);
        builtMoves = next;
        proveError = "";
        if (!next.length) {
            proveResult = null;
            return;
        }
        proveBusy = true;
        try {
            const res = await client.proveStep(recordedScenario.id, next);
            if (!res.ok) {
                proveError = res.reason ?? "Could not check that move.";
                return;
            }
            proveResult = res;
        } catch (e) {
            proveError = String(e);
        } finally {
            proveBusy = false;
        }
    }

    function announceProve(): void {
        const last = proveSteps[proveSteps.length - 1];
        if (!last) {
            liveMsg = "";
        } else if (proved) {
            liveMsg = `Proved. ${proveResult?.goal ?? ""}`;
        } else if (last.blocked) {
            liveMsg = `Blocked. ${last.reason ?? ""}`;
        } else {
            liveMsg = `Verified: ${last.claim}. Entails.`;
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
            A conditional-chain proof, checked <strong>live</strong>
            — one step at a time — by the same decision procedure our tests run. Watch a
            recorded draft get vetoed,
            <strong>build the proof yourself</strong>
            , or have the real model draft it. The verdicts are computed right now; a
            bad step can't reach the screen.
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

            <div class="modes" role="group" aria-label="Mode">
                <button
                    type="button"
                    class="mode"
                    class:on={view === "recorded"}
                    aria-pressed={view === "recorded"}
                    on:click={() => setView("recorded")}
                >
                    Watch
                </button>
                <button
                    type="button"
                    class="mode"
                    class:on={view === "prove"}
                    aria-pressed={view === "prove"}
                    on:click={() => setView("prove")}
                >
                    Your turn
                </button>
                {#if data.live_available}
                    <button
                        type="button"
                        class="mode"
                        class:on={view === "live"}
                        aria-pressed={view === "live"}
                        on:click={() => setView("live")}
                    >
                        Draft it live
                    </button>
                {/if}
            </div>
        {/if}
    </div>

    {#if state === "loading"}
        <p class="muted">Loading&hellip;</p>
    {:else if state === "error"}
        <div class="stage">
            <p class="muted">{error}</p>
            <button class="run" type="button" on:click={load}>Try again</button>
        </div>
    {:else if frameScenario}
        <div class="stage" class:vetoed={state === "vetoed"}>
            <div class="frame">
                <div class="block">
                    <span class="lbl">Premises</span>
                    <ul class="premises">
                        {#each frameScenario.premises as p, i (i)}
                            <li class="mono">{p}</li>
                        {/each}
                    </ul>
                </div>
                <div class="goalrow">
                    <span class="lbl">Prove</span>
                    <span class="mono goal">{frameScenario.goal}</span>
                </div>
            </div>

            {#if view === "prove"}
                <!-- YOUR TURN: assemble the proof; every pick is oracle-checked. -->
                <div class="draftbar">
                    <span class="aichip you">Your proof</span>
                    <span class="prov">every move checked by the oracle</span>
                </div>

                {#if proveSteps.length}
                    <ol class="steps">
                        {#each proveSteps as s (s.n)}
                            <li class="step" class:blocked={s.blocked}>
                                <div class="row">
                                    <span class="claim mono">{s.claim}</span>
                                    {#if s.blocked}
                                        <span class="pill bad">✗ blocked</span>
                                    {:else}
                                        <span class="pill ok">✓ entails</span>
                                    {/if}
                                </div>
                                <span class="cite mono">{s.cited}</span>
                                {#if s.blocked && s.reason}
                                    <p class="reason">{s.reason}</p>
                                {/if}
                                {#if s.blocked && s.world && s.world.length}
                                    <div class="world">
                                        <span class="world-lbl">
                                            Counterexample — a world where every premise
                                            holds but the step fails:
                                        </span>
                                        <ul>
                                            {#each s.world as line, i (i)}
                                                <li class="mono">{line}</li>
                                            {/each}
                                        </ul>
                                    </div>
                                {/if}
                            </li>
                        {/each}
                    </ol>
                {/if}

                {#if proved}
                    <div class="receipt">
                        <ProvenanceBadge tier="proven" label="Proven live" />
                        <p class="rnote">
                            You derived {frameScenario.goal} — every step re-checked by the
                            material-entailment oracle.
                        </p>
                    </div>
                {:else}
                    <p class="frontier-hint">
                        {#if lastStepBlocked}
                            That step is blocked — <strong>undo</strong>
                             and try another.
                        {:else}
                            Next step from <span class="mono">{currentFrontier}</span>
                            :
                        {/if}
                    </p>
                    <div class="moves" role="group" aria-label="Pick the next premise">
                        {#each recordedScenario?.options ?? [] as opt (`${opt.premise_index}:${opt.contrapositive}`)}
                            <button
                                type="button"
                                class="move"
                                disabled={proveBusy || lastStepBlocked}
                                on:click={() => pickMove(opt)}
                            >
                                {opt.text}
                            </button>
                        {/each}
                    </div>
                {/if}

                {#if proveError}<p class="muted err-note">{proveError}</p>{/if}
                {#if builtMoves.length}
                    <div class="builder-actions">
                        <button
                            class="stepper"
                            type="button"
                            on:click={undoMove}
                            disabled={proveBusy}
                        >
                            &#8624; Undo
                        </button>
                        <button
                            class="stepper"
                            type="button"
                            on:click={resetProve}
                            disabled={proveBusy}
                        >
                            Reset
                        </button>
                    </div>
                {/if}
            {:else if view === "live" && !liveScenario}
                <!-- DRAFT IT LIVE: not yet drafted. -->
                <button
                    class="run"
                    type="button"
                    on:click={draftLive}
                    disabled={liveState === "drafting"}
                >
                    {liveState === "drafting" ? "Drafting a proof…" : "Draft it live ▶"}
                </button>
                {#if liveState === "error"}
                    <p class="muted err-note">{liveError}</p>
                {/if}
            {:else}
                <!-- WATCH (recorded) or a completed live draft: the replay. -->
                <button
                    class="run"
                    type="button"
                    on:click={view === "live" ? draftLive : run}
                    disabled={running || liveState === "drafting"}
                >
                    {#if view === "live"}
                        {running ? "Running…" : "Draft again ▶"}
                    {:else}
                        {runLabel}
                    {/if}
                </button>

                {#if started}
                    <div class="draftbar">
                        <span class="aichip">AI draft</span>
                        <span class="prov">{chipLabel}</span>
                    </div>

                    <ol class="steps">
                        {#each beats as b, i (i)}
                            {#if i < revealed}
                                {#if b.type === "draft"}
                                    <li class="step" class:blocked={b.step.blocked}>
                                        <div class="row">
                                            <span class="claim mono">
                                                {b.step.claim}
                                            </span>
                                            {#if b.step.blocked}
                                                <span class="pill bad">
                                                    ✗ does not follow — blocked
                                                </span>
                                            {:else}
                                                <span class="pill ok">✓ entails</span>
                                            {/if}
                                        </div>
                                        <span class="cite mono">{b.step.cited}</span>
                                        {#if b.step.blocked && b.step.reason}
                                            <p class="reason">{b.step.reason}</p>
                                        {/if}
                                        {#if b.step.blocked && b.step.world && b.step.world.length}
                                            <div class="world">
                                                <span class="world-lbl">
                                                    Counterexample — a world where every
                                                    premise holds but the step fails:
                                                </span>
                                                <ul>
                                                    {#each b.step.world as line, wi (wi)}
                                                        <li class="mono">{line}</li>
                                                    {/each}
                                                </ul>
                                            </div>
                                        {/if}
                                    </li>
                                {:else}
                                    <li class="step fix">
                                        <div class="row">
                                            <span class="oraclechip">oracle</span>
                                            <span class="claim mono">
                                                {b.corrected.claim}
                                            </span>
                                            <span class="pill ok">✓ proven</span>
                                        </div>
                                        <span class="cite mono">
                                            {b.corrected.cited}
                                        </span>
                                    </li>
                                {/if}
                            {/if}
                        {/each}
                    </ol>

                    {#if reduceMotion && revealed < beats.length}
                        <button class="stepper" type="button" on:click={step}>
                            Step through &#9656;
                        </button>
                    {/if}

                    {#if state === "receipt"}
                        <div class="receipt">
                            <ProvenanceBadge tier="proven" label="Proven live" />
                            <p class="rnote">{activeScenario?.receipt.note}</p>
                        </div>
                    {/if}
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

    /* Mode switch (Watch / Your turn / Draft it live) — a segmented control that
     * reads as the primary "how do you want to engage" choice. */
    .modes {
        display: inline-flex;
        flex-wrap: wrap;
        gap: 0.25rem;
        margin-top: 0.15rem;
        padding: 0.25rem;
        background: var(--lsat-inset);
        border: 1px solid var(--lsat-border-subtle);
        border-radius: var(--lsat-radius-pill);
        width: fit-content;
    }
    .mode {
        padding: 0.35rem 0.85rem;
        font: inherit;
        font-size: 0.8rem;
        font-weight: 650;
        color: var(--lsat-fg-subtle);
        background: transparent;
        border: none;
        border-radius: var(--lsat-radius-pill);
        cursor: pointer;
        transition:
            color var(--lsat-transition) var(--lsat-ease),
            background var(--lsat-transition) var(--lsat-ease);
    }
    .mode:hover {
        color: var(--lsat-fg);
    }
    .mode.on {
        color: var(--lsat-ink-on-accent);
        background: var(--lsat-proven);
        box-shadow: var(--lsat-glow);
    }
    .mode:focus-visible {
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
        color: var(--lsat-ink-on-accent);
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
    .err-note {
        margin-top: 0.4rem;
        font-size: 0.82rem;
        color: var(--lsat-bad);
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
    /* The learner's own proof reads in the brand accent, not the AI violet. */
    .aichip.you {
        color: color-mix(in srgb, var(--lsat-accent) 74%, var(--lsat-fg));
        background: var(--lsat-accent-soft);
        border-color: color-mix(in srgb, var(--lsat-accent) 42%, transparent);
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

    /* The counterexample "world": a concrete countermodel the oracle produced —
     * premises all TRUE, the claimed step FALSE. The convincing "here's why". */
    .world {
        margin-top: 0.15rem;
        padding: 0.5rem 0.6rem;
        border-radius: var(--lsat-radius-sm);
        background: color-mix(in srgb, var(--lsat-bad) 8%, var(--lsat-surface));
        border: 1px dashed color-mix(in srgb, var(--lsat-bad) 38%, transparent);
    }
    .world-lbl {
        display: block;
        font-size: 0.72rem;
        font-weight: 650;
        color: color-mix(in srgb, var(--lsat-bad) 52%, var(--lsat-fg));
    }
    .world ul {
        margin: 0.35rem 0 0;
        padding-left: 1.1rem;
        display: flex;
        flex-direction: column;
        gap: 0.1rem;
    }
    .world li {
        font-size: 0.82rem;
        line-height: 1.4;
        color: var(--lsat-fg);
    }

    /* "Your turn" builder: the closed set of premise-edge moves. */
    .frontier-hint {
        margin: 0.1rem 0 0;
        font-size: 0.82rem;
        color: var(--lsat-fg-subtle);
    }
    .frontier-hint strong {
        color: var(--lsat-bad);
        font-weight: 700;
    }
    .moves {
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }
    .move {
        text-align: left;
        padding: 0.5rem 0.7rem;
        font: inherit;
        font-size: 0.9rem;
        color: var(--lsat-fg);
        background: var(--lsat-surface);
        border: 1px solid var(--lsat-border);
        border-radius: var(--lsat-radius-sm);
        cursor: pointer;
        transition:
            border-color var(--lsat-transition) var(--lsat-ease),
            background var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease);
    }
    .move:hover:not(:disabled) {
        border-color: var(--lsat-accent);
        background: var(--lsat-accent-tint);
    }
    .move:active:not(:disabled) {
        transform: scale(0.99);
    }
    .move:disabled {
        opacity: 0.5;
        cursor: default;
    }
    .move:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }
    .builder-actions {
        display: flex;
        gap: 0.4rem;
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
    .stepper:disabled {
        opacity: 0.5;
        cursor: default;
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
        .move:active:not(:disabled) {
            transform: none;
        }
    }
</style>
