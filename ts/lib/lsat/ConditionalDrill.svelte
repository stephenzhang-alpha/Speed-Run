<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Conditional Translation Drill (DECISION-round2 #19): read a conditional, tap which
clause is the SUFFICIENT condition (the trigger), then see the canonical
sufficient -> necessary arrow and its contrapositive. Grading is deterministic
server-side (lsat/conditional.py); the reveal teaches the direction + contrapositive.
-->
<script lang="ts">
    import { onMount } from "svelte";

    import Card from "./Card.svelte";
    import * as client from "./client";
    import type { ConditionalDrillData, ConditionalResult } from "./types";

    type State = "loading" | "asking" | "answered" | "done" | "error";

    let drill: ConditionalDrillData | null = null;
    let state: State = "loading";
    let result: ConditionalResult | null = null;
    let picked = "";
    let error = "";
    let shownAt = 0;

    async function load(): Promise<void> {
        state = "loading";
        result = null;
        picked = "";
        error = "";
        try {
            const d = await client.conditionalDrill();
            if (d.done || !d.item_id) {
                drill = null;
                state = "done";
                return;
            }
            drill = d;
            shownAt = Date.now();
            state = "asking";
        } catch (e) {
            error = String(e);
            state = "error";
        }
    }

    async function pick(clause: string): Promise<void> {
        if (!drill || state !== "asking") {
            return;
        }
        picked = clause;
        state = "answered"; // guard against a double tap during the round-trip
        const other = (drill.options ?? []).find((o) => o !== clause) ?? "";
        try {
            result = await client.submitConditional(
                drill.item_id,
                clause,
                other,
                Date.now() - shownAt,
            );
        } catch (e) {
            error = String(e);
            state = "error";
        }
    }

    onMount(load);
</script>

{#if state === "loading"}
    <Card><p class="muted">Loading&hellip;</p></Card>
{:else if state === "done"}
    <Card title="No drills right now"><p class="muted">Check back later.</p></Card>
{:else if state === "error"}
    <Card title="Couldn't load a drill">
        <p class="muted">{error}</p>
        <button class="next" on:click={load}>Try again</button>
    </Card>
{:else if drill}
    <Card title="Conditional logic" subtitle="Which clause is the sufficient condition?">
        <p class="sentence">{drill.sentence}</p>
        <div class="opts">
            {#each drill.options as opt (opt)}
                <button
                    type="button"
                    class="opt"
                    class:picked={picked === opt}
                    class:right={result?.graded && opt === result.sufficient}
                    class:wrong={result?.graded && picked === opt && opt !== result.sufficient}
                    disabled={state !== "asking"}
                    on:click={() => pick(opt)}
                >
                    {opt}
                </button>
            {/each}
        </div>

        {#if state === "answered" && result}
            {#if result.graded}
                <p class="verdict" class:ok={result.correct}>
                    {result.correct
                        ? "Correct — that's the trigger (sufficient) condition."
                        : "Not quite — the sufficient condition is the trigger."}
                </p>
                <div class="arrows">
                    <div><span class="lbl">Translation</span><code>{result.arrow}</code></div>
                    <div><span class="lbl">Contrapositive</span><code>{result.contrapositive}</code></div>
                </div>
            {:else}
                <p class="muted">{result.reason}</p>
            {/if}
            <button class="next" on:click={load}>Next drill</button>
        {/if}
    </Card>
{/if}

<style lang="scss">
    .muted {
        color: var(--lsat-fg-subtle);
        margin: 0;
    }
    .sentence {
        font-size: 1.02rem;
        line-height: 1.5;
        margin: 0.2rem 0 0.6rem;
    }
    .opts {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .opt {
        min-height: 46px;
        padding: 0.65rem 0.85rem;
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
    .verdict {
        margin: 0.7rem 0 0.3rem;
        font-weight: 650;
        color: var(--lsat-bad);
    }
    .verdict.ok {
        color: var(--lsat-good);
    }
    .arrows {
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
        padding: 0.6rem 0.7rem;
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-inset);
    }
    .arrows .lbl {
        display: block;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--lsat-fg-subtle);
    }
    .arrows code {
        font-size: 0.92rem;
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
        color: white;
        font: inherit;
        font-weight: 650;
        cursor: pointer;
    }
</style>
