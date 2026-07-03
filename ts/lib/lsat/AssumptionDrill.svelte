<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Necessary/Sufficient Discrimination Drill (r4 #5): read a gap argument (premises
+ conclusion) plus a candidate assumption, then tap whether the candidate is
necessary-only, sufficient-only, both, or neither. Grading is deterministic
server-side (lsat/assumption_discrimination.py, cells proven by the quantifier
model-checker); the reveal teaches the correct cell + a short note. Mirrors
ConditionalDrill / QuantifierDrill / StemPolarityDrill's states, double-submit
guard, and styling.
-->
<script lang="ts">
    import { onMount } from "svelte";

    import Card from "./Card.svelte";
    import * as client from "./client";
    import type { AssumptionDrill, AssumptionResult } from "./types";

    type State = "loading" | "asking" | "answered" | "done" | "error";

    let drill: AssumptionDrill | null = null;
    let state: State = "loading";
    let result: AssumptionResult | null = null;
    let picked = "";
    let error = "";
    let shownAt = 0;

    // Human label for each fixed cell key. Submit sends the raw key (e.g.
    // "necessary_only"); the label is only for display.
    const OPTION_META: Record<string, { label: string }> = {
        necessary_only: { label: "Necessary, not sufficient" },
        sufficient_only: { label: "Sufficient, not necessary" },
        both: { label: "Both" },
        neither: { label: "Neither" },
    };

    function meta(opt: string): { label: string } {
        return OPTION_META[opt] ?? { label: opt };
    }

    async function load(): Promise<void> {
        state = "loading";
        result = null;
        picked = "";
        error = "";
        try {
            const d = await client.assumptionDrill();
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
            result = await client.submitAssumption(
                drill.item_id,
                chosen,
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
    <Card title="Necessary vs sufficient" subtitle="Sort the assumption">
        <ul class="premises">
            {#each drill.premises as premise, i (i)}
                <li>
                    <span class="lbl">Premise</span>
                    <span class="txt">{premise}</span>
                </li>
            {/each}
        </ul>
        <div class="conclusion">
            <span class="lbl">Conclusion</span>
            <span class="txt">{drill.conclusion}</span>
        </div>
        <div class="candidate">
            <span class="lbl">Candidate assumption</span>
            <span class="txt">{drill.candidate}</span>
        </div>
        <div class="opts">
            {#each drill.options as opt (opt)}
                <button
                    type="button"
                    class="opt"
                    class:picked={picked === opt}
                    class:right={result?.graded && opt === result.cell}
                    class:wrong={result?.graded && picked === opt && opt !== result.cell}
                    disabled={state !== "asking"}
                    on:click={() => pick(opt)}
                >
                    {meta(opt).label}
                </button>
            {/each}
        </div>

        {#if state === "answered" && result}
            {#if result.graded}
                <p class="verdict" class:ok={result.correct}>
                    {result.correct
                        ? "Correct — that's the right sort."
                        : `Not quite — it's "${meta(result.cell ?? "").label}".`}
                </p>
                {#if result.note}
                    <div class="explain">
                        <span class="lbl">Why</span>
                        <p>{result.note}</p>
                    </div>
                {/if}
                <div class="chips">
                    <span class="chip">necessary {result.necessary ? "✓" : "✗"}</span>
                    <span class="chip">sufficient {result.sufficient ? "✓" : "✗"}</span>
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
    .premises {
        list-style: none;
        margin: 0.2rem 0 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }
    .premises li {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
        padding: 0.5rem 0.7rem;
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-inset);
    }
    /* The conclusion is what the argument drives at, so it gets a distinct
     * bordered block that lifts it out of the premise stack. */
    .conclusion {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
        margin: 0.5rem 0 0.2rem;
        padding: 0.65rem 0.8rem;
        border: 1px solid var(--lsat-border);
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-surface);
    }
    /* The candidate is the thing being judged, so it gets its own inset block
     * with a dashed edge to read as the statement to sort. */
    .candidate {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
        margin: 0.4rem 0 0.2rem;
        padding: 0.65rem 0.8rem;
        border: 1px dashed var(--lsat-border);
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-inset);
    }
    .lbl {
        display: block;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--lsat-fg-subtle);
    }
    .txt {
        font-size: 0.98rem;
        line-height: 1.45;
        color: var(--lsat-fg);
    }
    .conclusion .txt {
        font-size: 1.04rem;
        font-weight: 600;
    }
    .candidate .txt {
        font-weight: 600;
    }
    .opts {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        margin-top: 0.6rem;
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
    .chips {
        display: flex;
        gap: 0.4rem;
        margin-top: 0.5rem;
    }
    .chip {
        padding: 0.2rem 0.6rem;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-inset);
        color: var(--lsat-fg-subtle);
        font-size: 0.74rem;
        font-weight: 600;
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
