<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Conditional-Chain Drill: read a 3+ arrow conditional chain and judge whether a
candidate inference MUST follow or DOES NOT follow (transitive chaining +
contrapositive, vs affirming-consequent / denying-antecedent). Grading is exact
+ deterministic server-side (lsat/conditional_chain.py); the reveal teaches why.
Mirrors StemPolarityDrill / QuantifierDrill states, double-submit guard, styling.
-->
<script lang="ts">
    import { onMount } from "svelte";

    import Card from "./Card.svelte";
    import * as client from "./client";
    import type { ChainDrill, ChainResult } from "./types";

    type State = "loading" | "asking" | "answered" | "done" | "error";

    let drill: ChainDrill | null = null;
    let state: State = "loading";
    let result: ChainResult | null = null;
    let picked = "";
    let error = "";
    let shownAt = 0;

    const OPTION_META: Record<string, { label: string; gloss: string }> = {
        must_follow: { label: "Must follow", gloss: "it's guaranteed by the chain" },
        does_not_follow: { label: "Doesn't follow", gloss: "it could be false" },
    };

    function meta(opt: string): { label: string; gloss: string } {
        return OPTION_META[opt] ?? { label: opt, gloss: "" };
    }

    async function load(): Promise<void> {
        state = "loading";
        result = null;
        picked = "";
        error = "";
        try {
            const d = await client.chainDrill();
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

    async function pick(chosen: string): Promise<void> {
        if (!drill || state !== "asking") {
            return;
        }
        picked = chosen;
        state = "answered"; // guard against a double tap during the round-trip
        try {
            result = await client.submitChain(drill.item_id, chosen, Date.now() - shownAt);
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
    <Card title="Conditional chains" subtitle="Does the conclusion have to follow?">
        <ul class="premises">
            {#each drill.premises as p (p)}
                <li>{p}</li>
            {/each}
        </ul>
        <div class="candidate">
            <span class="lbl">Candidate</span>
            <p>{drill.candidate}</p>
        </div>
        <div class="opts">
            {#each drill.options as opt (opt)}
                <button
                    type="button"
                    class="opt"
                    class:picked={picked === opt}
                    class:right={result?.graded && opt === result.verdict}
                    class:wrong={result?.graded && picked === opt && opt !== result.verdict}
                    disabled={state !== "asking"}
                    on:click={() => pick(opt)}
                >
                    <span class="key">{meta(opt).label}</span>
                    <span class="gloss">{meta(opt).gloss}</span>
                </button>
            {/each}
        </div>

        {#if state === "answered" && result}
            {#if result.graded}
                <p class="verdict" class:ok={result.correct}>
                    {result.correct
                        ? "Correct."
                        : "Not quite — see why below."}
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
            <button class="next" on:click={load}>Next drill</button>
        {/if}
    </Card>
{/if}

<style lang="scss">
    .muted {
        color: var(--lsat-fg-subtle);
        margin: 0;
    }
    /* The chain premises: a compact stacked list of the given conditionals. */
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
    /* The candidate inference is the thing being judged -> distinct block. */
    .candidate {
        margin: 0 0 0.7rem;
        padding: 0.6rem 0.75rem;
        border: 1px solid var(--lsat-border);
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-surface);
    }
    .candidate .lbl {
        display: block;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--lsat-fg-subtle);
    }
    .candidate p {
        margin: 0.15rem 0 0;
        font-size: 1.02rem;
        font-weight: 600;
        line-height: 1.4;
        color: var(--lsat-fg);
    }
    .opts {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .opt {
        display: flex;
        flex-direction: column;
        gap: 0.12rem;
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
        font-size: 0.98rem;
        font-weight: 650;
    }
    .gloss {
        font-size: 0.82rem;
        color: var(--lsat-fg-subtle);
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
    .explain .lbl {
        display: block;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--lsat-fg-subtle);
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
        color: white;
        font: inherit;
        font-weight: 650;
        cursor: pointer;
    }

    @media (prefers-reduced-motion: reduce) {
        .opt {
            transition: none;
        }
    }
</style>
