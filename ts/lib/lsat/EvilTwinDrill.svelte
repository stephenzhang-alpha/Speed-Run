<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Oracle-Proven "Skill or Luck?" Evil Twin: a minimally-edited variant of a
formal-logic item whose correct answer FLIPS (reverse the arrow, swap a
quantifier, convert subject/predicate). Get it right and you understood; miss it
and you pattern-matched. Every twin's answer is re-derived by a decision procedure
server-side (lsat/evil_twin.py) via the stateless twin_key -- an LLM only targets
which proven twin to show, never the answer. Mirrors ChainDrill's states/styling.
-->
<script lang="ts">
    import { onMount } from "svelte";

    import Card from "./Card.svelte";
    import * as client from "./client";
    import ProvenanceBadge from "./ProvenanceBadge.svelte";
    import type { EvilTwinDrill, EvilTwinResult } from "./types";

    type State = "loading" | "asking" | "answered" | "done" | "error";

    let drill: EvilTwinDrill | null = null;
    let state: State = "loading";
    let result: EvilTwinResult | null = null;
    let picked = "";
    let error = "";
    let shownAt = 0;

    const VERDICT_LABEL: Record<string, string> = {
        must_be_true: "Must be true",
        cannot_be_true: "Cannot be true",
        could_be_either: "Could be either",
        must_follow: "Must follow",
        does_not_follow: "Doesn't follow",
    };
    function label(v: string): string {
        return VERDICT_LABEL[v] ?? v;
    }

    async function load(): Promise<void> {
        state = "loading";
        result = null;
        picked = "";
        error = "";
        try {
            const d = await client.evilTwinDrill();
            if (d.done || !d.twin_key) {
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
            result = await client.submitEvilTwin(drill.twin_key, chosen, Date.now() - shownAt);
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
    <Card title="No twins right now"><p class="muted">Check back later.</p></Card>
{:else if state === "error"}
    <Card title="Couldn't load a twin">
        <p class="muted">{error}</p>
        <button class="next" on:click={load}>Try again</button>
    </Card>
{:else if drill}
    <Card title="Skill or luck?" subtitle="A one-edit twin of an item you'd get right — does THIS one follow?">
        <div class="receipt"><ProvenanceBadge tier="proven" label="Oracle-proven twin" /></div>
        <ul class="premises">
            {#each drill.premises as p (p)}
                <li>{p}</li>
            {/each}
        </ul>
        <div class="goal">
            <span class="lbl">Conclusion</span>
            <p>{drill.conclusion}</p>
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
                    <span class="key">{label(opt)}</span>
                </button>
            {/each}
        </div>

        {#if state === "answered" && result}
            {#if result.graded}
                <p class="verdict" class:ok={result.correct}>
                    {result.correct
                        ? "Correct — you saw the edit, not the surface."
                        : "Caught! The one-token edit flipped the answer."}
                </p>
                {#if result.edit_note}
                    <div class="explain">
                        <span class="lbl">The edit</span>
                        <p>
                            We {result.edit_note}. That flips the answer from
                            <b>{label(result.original_verdict ?? "")}</b> to
                            <b>{label(result.verdict ?? "")}</b>.
                        </p>
                    </div>
                {/if}
            {:else}
                <p class="muted">{result.reason}</p>
            {/if}
            <button class="next" on:click={load}>Next twin</button>
        {/if}
    </Card>
{/if}

<style lang="scss">
    .muted {
        color: var(--lsat-fg-subtle);
        margin: 0;
    }
    .receipt {
        margin: 0 0 0.5rem;
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
