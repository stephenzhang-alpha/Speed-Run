<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Oracle-Verified Faded Worked Example (research feature #1): the first proven
steps of a conditional-chain derivation are shown, and the FINAL step is blanked
for the learner to complete (backward fading). Each option is a premise applied
as-is or as its contrapositive. Every step is derived + checked by the exact
material-entailment oracle server-side (lsat/worked_example.py), so a
hallucinated step is never served; the correct move is withheld until submit.
Mirrors ChainDrill's states, double-submit guard, and styling.
-->
<script lang="ts">
    import { onMount, tick } from "svelte";

    import Card from "./Card.svelte";
    import * as client from "./client";
    import ProvenanceBadge from "./ProvenanceBadge.svelte";
    import type { WorkedExampleDrill, WorkedStepResult } from "./types";

    type State = "loading" | "asking" | "answered" | "done" | "error";

    let drill: WorkedExampleDrill | null = null;
    let state: State = "loading";
    let result: WorkedStepResult | null = null;
    let picked = "";
    let shownAt = 0;
    let nextBtn: HTMLButtonElement | undefined;

    // Provenance label (the tier is always "proven" — every served worked example
    // is oracle-derived or oracle-verified; the source just says how).
    const SOURCE_LABEL: Record<string, string> = {
        ai_verified: "AI-drafted → oracle-verified",
        deterministic: "Oracle-derived proof",
        deterministic_fallback: "AI draft rejected → oracle-derived",
    };
    function sourceLabel(src: string | undefined): string {
        return SOURCE_LABEL[src ?? "deterministic"] ?? "Oracle-derived proof";
    }

    async function load(): Promise<void> {
        state = "loading";
        result = null;
        picked = "";
        try {
            const d = await client.workedExampleDrill();
            if (d.done || !d.item_id) {
                drill = null;
                state = "done";
                return;
            }
            drill = d;
            shownAt = Date.now();
            state = "asking";
        } catch (e) {
            console.error(e);
            state = "error";
        }
    }

    async function pick(moveId: string): Promise<void> {
        if (!drill || state !== "asking") {
            return;
        }
        picked = moveId;
        state = "answered"; // guard against a double tap during the round-trip
        try {
            result = await client.submitWorkedStep(
                drill.item_id,
                moveId,
                Date.now() - shownAt,
            );
            await tick();
            nextBtn?.focus();
        } catch (e) {
            console.error(e);
            state = "error";
        }
    }

    onMount(load);
</script>

{#if state === "loading"}
    <Card><p class="muted">Loading&hellip;</p></Card>
{:else if state === "done"}
    <Card title="No worked examples right now">
        <p class="muted">Check back later.</p>
    </Card>
{:else if state === "error"}
    <Card title="Couldn't load a worked example">
        <p class="muted">Couldn't reach the server. Try again.</p>
        <button class="next" on:click={load}>Try again</button>
    </Card>
{:else if drill}
    <Card
        title="Worked example"
        subtitle="Finish the proof: pick the step that reaches the goal"
    >
        <div class="receipt" title={drill.verification?.claim ?? ""}>
            <ProvenanceBadge tier="proven" label={sourceLabel(drill.source)} />
        </div>
        <ul class="premises">
            {#each drill.premises as p, i (i)}
                <li>{p}</li>
            {/each}
        </ul>
        <div class="goal">
            <span class="lbl">Goal</span>
            <p>{drill.goal}</p>
        </div>
        {#if drill.shown_steps.length}
            <ol class="steps">
                {#each drill.shown_steps as s, i (i)}
                    <li>
                        <span class="tick" aria-hidden="true">✓</span>
                        {s}
                    </li>
                {/each}
            </ol>
        {/if}
        {#if drill.verification}
            <p class="proof-note">
                {drill.verification.steps_verified} step{drill.verification
                    .steps_verified === 1
                    ? ""
                    : "s"} verified by {drill.verification.method}. A step an AI
                proposes that doesn't check out is discarded — a hallucinated step can't
                appear here.
            </p>
        {/if}
        <p class="prompt">{drill.prompt}</p>
        <div class="opts" aria-busy={state === "answered" && !result}>
            {#each drill.options as opt (opt.move_id)}
                <button
                    type="button"
                    class="opt"
                    class:picked={picked === opt.move_id}
                    class:right={result?.graded &&
                        result.correct &&
                        picked === opt.move_id}
                    class:wrong={result?.graded &&
                        !result.correct &&
                        picked === opt.move_id}
                    disabled={state !== "asking"}
                    on:click={() => pick(opt.move_id)}
                >
                    <span class="key">{opt.text}</span>
                </button>
            {/each}
        </div>

        {#if state === "answered" && !result}
            <p class="checking" aria-live="polite">Checking&hellip;</p>
        {/if}

        {#if state === "answered" && result}
            {#if result.graded}
                <p class="verdict" class:ok={result.correct} aria-live="polite">
                    {result.correct
                        ? `Correct — that reaches “${result.to_text ?? drill.goal}”, completing the chain.`
                        : "Not quite — that step doesn't complete the chain to the goal."}
                </p>
                {#if result.note}
                    <div class="explain">
                        <span class="lbl">Why</span>
                        <p>{result.note}</p>
                    </div>
                {/if}
            {:else}
                <p class="muted">{result.reason}</p>
            {/if}
            <button class="next" bind:this={nextBtn} on:click={load}>
                Next worked example
            </button>
        {/if}
    </Card>
{/if}

<style lang="scss">
    .muted {
        color: var(--lsat-fg-subtle);
        margin: 0;
    }
    .checking {
        margin: 0.6rem 0 0;
        font-size: 0.85rem;
        color: var(--lsat-fg-subtle);
    }
    /* Proof receipt: the visible "this is verified, not vibes" trust marker. */
    .receipt {
        margin: 0 0 0.5rem;
    }
    .tick {
        color: var(--lsat-good);
        font-weight: 700;
        margin-right: 0.4rem;
    }
    .proof-note {
        margin: 0 0 0.7rem;
        font-size: 0.78rem;
        line-height: 1.45;
        color: var(--lsat-fg-subtle);
    }
    .premises {
        margin: 0.2rem 0 0.6rem;
        padding-left: 1.1rem;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }
    .premises li {
        font-size: 0.96rem;
        line-height: 1.4;
        color: var(--lsat-fg);
    }
    .goal {
        margin: 0 0 0.7rem;
        padding: 0.6rem 0.75rem;
        border: 1px solid var(--lsat-border);
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-surface);
    }
    .goal .lbl,
    .explain .lbl {
        display: block;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--lsat-fg-subtle);
    }
    .goal p {
        margin: 0.15rem 0 0;
        font-size: 1.02rem;
        font-weight: 600;
        line-height: 1.4;
        color: var(--lsat-fg);
    }
    /* The already-worked steps: a numbered, proven prefix of the derivation. */
    .steps {
        margin: 0 0 0.6rem;
        padding-left: 1.2rem;
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
    }
    .steps li {
        font-size: 0.92rem;
        line-height: 1.45;
        color: var(--lsat-fg);
    }
    .prompt {
        margin: 0 0 0.5rem;
        font-weight: 600;
        color: var(--lsat-fg);
    }
    .opts {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .opt {
        display: flex;
        min-height: 46px;
        padding: 0.6rem 0.85rem;
        text-align: left;
        border: 1px solid var(--lsat-border);
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-surface);
        color: var(--lsat-fg);
        font: inherit;
        cursor: pointer;
        transition:
            border-color var(--lsat-transition) var(--lsat-ease),
            background var(--lsat-transition) var(--lsat-ease);
    }
    .opt:hover:not(:disabled) {
        border-color: var(--lsat-accent);
    }
    .opt:disabled {
        cursor: default;
    }
    .opt:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }
    .opt.picked {
        border-width: 2px;
    }
    .opt.right {
        border-color: var(--lsat-good);
        background: var(--lsat-good-soft);
    }
    .opt.wrong {
        border-color: var(--lsat-bad);
        background: var(--lsat-bad-soft);
    }
    .key {
        font-size: 0.96rem;
        font-weight: 600;
    }
    .verdict {
        margin: 0.7rem 0 0.3rem;
        font-weight: 650;
        color: var(--lsat-bad);
    }
    .verdict.ok {
        color: var(--lsat-good);
    }
    .explain {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
        padding: 0.6rem 0.7rem;
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-inset);
    }
    .explain p {
        margin: 0;
        font-size: 0.9rem;
        line-height: 1.5;
        color: var(--lsat-fg);
    }
    .next {
        align-self: flex-start;
        min-height: 44px;
        margin-top: 0.6rem;
        padding: 0.55rem 1.1rem;
        border: none;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-hero);
        color: var(--lsat-ink-on-accent);
        font: inherit;
        font-weight: 650;
        cursor: pointer;
    }
    .next:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }

    @media (prefers-reduced-motion: reduce) {
        .opt {
            transition: none;
        }
    }
</style>
