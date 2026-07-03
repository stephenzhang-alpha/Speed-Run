<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Quantifier Reasoning Drill Suite. Two deterministic, server-graded drills that
share this component via the `mode` prop:

  - "validity": read a couple of quantifier premises and a conclusion, then tap
    whether the conclusion must be true, cannot be true, or could be either. The
    reveal teaches the correct verdict plus a short note.
  - "negation": read a quantified sentence and tap its exact logical negation.

Grading is deterministic server-side (lsat/quantifier.py). Mirrors
ConditionalDrill's states, double-submit guard, and styling.
-->
<script lang="ts">
    import { onMount } from "svelte";

    import Card from "./Card.svelte";
    import * as client from "./client";
    import type {
        QuantifierNegationDrill,
        QuantifierNegationResult,
        QuantifierValidityDrill,
        QuantifierValidityResult,
        QuantifierVerdict,
    } from "./types";

    export let mode: "validity" | "negation" = "validity";

    type State = "loading" | "asking" | "answered" | "done" | "error";

    let state: State = "loading";
    let error = "";
    let shownAt = 0;
    let picked = "";

    // Validity mode.
    let validity: QuantifierValidityDrill | null = null;
    let validityResult: QuantifierValidityResult | null = null;

    // Negation mode.
    let negation: QuantifierNegationDrill | null = null;
    let negationResult: QuantifierNegationResult | null = null;

    const VERDICTS: [QuantifierVerdict, string][] = [
        ["must_be_true", "Must be true"],
        ["cannot_be_true", "Cannot be true"],
        ["could_be_either", "Could be either"],
    ];

    function verdictLabel(v: QuantifierVerdict | undefined): string {
        return VERDICTS.find(([value]) => value === v)?.[1] ?? "";
    }

    async function load(): Promise<void> {
        state = "loading";
        error = "";
        picked = "";
        validity = null;
        validityResult = null;
        negation = null;
        negationResult = null;
        try {
            if (mode === "validity") {
                const d = await client.quantifierValidityDrill();
                if (d.done || !d.item_id) {
                    state = "done";
                    return;
                }
                validity = d;
            } else {
                const d = await client.quantifierNegationDrill();
                if (d.done || !d.item_id) {
                    state = "done";
                    return;
                }
                negation = d;
            }
            shownAt = Date.now();
            state = "asking";
        } catch (e) {
            error = String(e);
            state = "error";
        }
    }

    async function pickValidity(chosen: QuantifierVerdict): Promise<void> {
        if (!validity || state !== "asking") {
            return;
        }
        picked = chosen;
        state = "answered"; // guard against a double tap during the round-trip
        try {
            validityResult = await client.submitQuantifierValidity(
                validity.item_id,
                chosen,
                Date.now() - shownAt,
            );
        } catch (e) {
            error = String(e);
            state = "error";
        }
    }

    async function pickNegation(chosen: string): Promise<void> {
        if (!negation || state !== "asking") {
            return;
        }
        picked = chosen;
        state = "answered"; // guard against a double tap during the round-trip
        try {
            negationResult = await client.submitQuantifierNegation(
                negation.item_id,
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
{:else if mode === "validity" && validity}
    <Card title="Quantifier validity" subtitle="Does the conclusion follow?">
        <ul class="premises">
            {#each validity.premises as premise, i (i)}
                <li>
                    <span class="lbl">Premise</span>
                    <span class="txt">{premise}</span>
                </li>
            {/each}
        </ul>
        <div class="conclusion">
            <span class="lbl">Conclusion</span>
            <span class="txt">{validity.conclusion}</span>
        </div>
        <div class="opts">
            {#each VERDICTS as [value, label] (value)}
                <button
                    type="button"
                    class="opt"
                    class:picked={picked === value}
                    class:right={validityResult?.graded && value === validityResult.verdict}
                    class:wrong={validityResult?.graded &&
                        picked === value &&
                        value !== validityResult.verdict}
                    disabled={state !== "asking"}
                    on:click={() => pickValidity(value)}
                >
                    {label}
                </button>
            {/each}
        </div>

        {#if state === "answered" && validityResult}
            {#if validityResult.graded}
                <p class="verdict" class:ok={validityResult.correct}>
                    {validityResult.correct
                        ? "Correct."
                        : `Not quite — the answer is "${verdictLabel(validityResult.verdict)}".`}
                </p>
                {#if validityResult.note}
                    <div class="explain">
                        <span class="lbl">Why</span>
                        <p>{validityResult.note}</p>
                    </div>
                {/if}
            {:else}
                <p class="muted">{validityResult.reason}</p>
            {/if}
            <button class="next" on:click={load}>Next drill</button>
        {/if}
    </Card>
{:else if mode === "negation" && negation}
    <Card title="Negation" subtitle="What is the exact logical negation?">
        <p class="sentence">{negation.sentence}</p>
        <div class="opts">
            {#each negation.options as opt (opt.quant)}
                <button
                    type="button"
                    class="opt"
                    class:picked={picked === opt.quant}
                    class:right={negationResult?.graded && opt.quant === negationResult.answer}
                    class:wrong={negationResult?.graded &&
                        picked === opt.quant &&
                        opt.quant !== negationResult.answer}
                    disabled={state !== "asking"}
                    on:click={() => pickNegation(opt.quant)}
                >
                    {opt.text}
                </button>
            {/each}
        </div>

        {#if state === "answered" && negationResult}
            {#if negationResult.graded}
                <p class="verdict" class:ok={negationResult.correct}>
                    {negationResult.correct
                        ? "Correct — that's the exact negation."
                        : "Not quite — the highlighted option is the exact negation."}
                </p>
            {:else}
                <p class="muted">{negationResult.reason}</p>
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
    /* The conclusion is the thing being judged, so it gets a distinct bordered
     * block that lifts it out of the premise stack. */
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
