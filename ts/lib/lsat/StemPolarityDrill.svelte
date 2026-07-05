<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Stem-Polarity Micro-Drill: read a real LSAT question stem and tap whether it is
direct / EXCEPT / LEAST / negated -- i.e. what the stem is really asking you to
find. Grading is deterministic server-side (lsat/stem_polarity.py); the reveal
teaches the search instruction the polarity implies plus the base task. Mirrors
ConditionalDrill / QuantifierDrill's states, double-submit guard, and styling.
-->
<script lang="ts">
    import { onMount, tick } from "svelte";

    import Card from "./Card.svelte";
    import * as client from "./client";
    import type { StemPolarityDrill, StemPolarityResult } from "./types";

    type State = "loading" | "asking" | "answered" | "done" | "error";

    let drill: StemPolarityDrill | null = null;
    let state: State = "loading";
    let result: StemPolarityResult | null = null;
    let picked = "";
    let shownAt = 0;
    let nextBtn: HTMLButtonElement | undefined;

    // Human label + one-line gloss for each fixed polarity key. Submit sends the
    // raw key (e.g. "except"); the gloss teaches the search task it implies.
    const OPTION_META: Record<string, { label: string; gloss: string }> = {
        direct: { label: "Direct", gloss: "find the one that does it" },
        except: { label: "EXCEPT", gloss: "find the one that does NOT" },
        least: { label: "LEAST", gloss: "find the one that does it least" },
        negated: { label: "Negated", gloss: "find where it does NOT hold" },
    };

    function meta(opt: string): { label: string; gloss: string } {
        return OPTION_META[opt] ?? { label: opt, gloss: "" };
    }

    async function load(): Promise<void> {
        state = "loading";
        result = null;
        picked = "";
        try {
            const d = await client.stemPolarityDrill();
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

    async function pick(chosen: string): Promise<void> {
        if (!drill || state !== "asking") {
            return;
        }
        picked = chosen;
        state = "answered"; // guard against a double tap during the round-trip
        try {
            result = await client.submitStemPolarity(
                drill.item_id,
                chosen,
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
    <Card title="No drills right now"><p class="muted">Check back later.</p></Card>
{:else if state === "error"}
    <Card title="Couldn't load a drill">
        <p class="muted">Couldn't reach the server. Try again.</p>
        <button class="next" on:click={load}>Try again</button>
    </Card>
{:else if drill}
    <Card title="Stem polarity" subtitle="What is the stem really asking?">
        <p class="stem">{drill.stem}</p>
        <div class="opts" aria-busy={state === "answered" && !result}>
            {#each drill.options as opt (opt)}
                <button
                    type="button"
                    class="opt"
                    class:picked={picked === opt}
                    class:right={result?.graded && opt === result.polarity}
                    class:wrong={result?.graded &&
                        picked === opt &&
                        opt !== result.polarity}
                    disabled={state !== "asking"}
                    on:click={() => pick(opt)}
                >
                    <span class="key">{meta(opt).label}</span>
                    <span class="gloss">{meta(opt).gloss}</span>
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
                        ? "Correct — that's what the stem is asking for."
                        : "Not quite — the highlighted polarity is the one to hold."}
                </p>
                {#if result.instruction}
                    <div class="explain">
                        <span class="lbl">What to look for</span>
                        <p>{result.instruction}</p>
                    </div>
                {/if}
                {#if result.base_task}
                    <span class="chip">task: {result.base_task}</span>
                {/if}
            {:else}
                <p class="muted">{result.reason}</p>
            {/if}
            <button class="next" bind:this={nextBtn} on:click={load}>Next drill</button>
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
    /* The stem is the thing being judged, so it gets a distinct bordered block
     * that reads like the question it is. */
    .stem {
        margin: 0.2rem 0 0.7rem;
        padding: 0.7rem 0.85rem;
        border: 1px solid var(--lsat-border);
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-surface);
        font-size: 1.06rem;
        font-weight: 600;
        line-height: 1.45;
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
    .chip {
        align-self: flex-start;
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
