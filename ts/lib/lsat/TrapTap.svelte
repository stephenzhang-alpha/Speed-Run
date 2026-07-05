<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"Which trap is (X)?" competitive-retrieval tap shown on a miss. Emits the chosen
family; the parent grades it and passes back `result` for feedback.
-->
<script lang="ts">
    import { createEventDispatcher } from "svelte";

    import type { TrapResult } from "./types";

    export let chosen: string;
    export let result: TrapResult | null = null;

    const dispatch = createEventDispatcher<{ select: string }>();
    const traps: [string, string][] = [
        ["out_of_scope", "Out of scope"],
        ["extreme_language", "Extreme language"],
        ["reversal", "Reversal"],
        ["half_right", "Half-right"],
        ["irrelevant_comparison", "Irrelevant comparison"],
    ];
</script>

<div class="trap">
    <span class="q">Why is ({chosen}) wrong?</span>
    <div class="chips">
        {#each traps as [fam, label] (fam)}
            <button
                type="button"
                disabled={result !== null}
                on:click={() => dispatch("select", fam)}
            >
                {label}
            </button>
        {/each}
    </div>
    {#if result && result.actual_label}
        <p class="fb" class:right={result.trap_correct}>
            {result.trap_correct ? "Yes \u2014 " : "Actually "}({chosen}) is {result.actual_label}.
        </p>
    {/if}
</div>

<style lang="scss">
    .trap {
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
    }
    .q {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--lsat-fg-faint);
    }
    .chips {
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
    }
    button {
        min-height: 40px;
        padding: 0.4rem 0.8rem;
        border-radius: var(--lsat-radius-pill);
        border: 1px solid var(--lsat-border);
        background: var(--lsat-surface);
        color: var(--lsat-fg);
        font: inherit;
        font-size: 0.85rem;
        font-weight: 550;
        cursor: pointer;
        transition:
            border-color var(--lsat-transition) var(--lsat-ease),
            background var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease);
    }
    button:hover:not(:disabled) {
        border-color: var(--lsat-accent);
        background: var(--lsat-accent-soft);
    }
    button:active:not(:disabled) {
        transform: scale(0.96);
    }
    button:disabled {
        opacity: 0.5;
        cursor: default;
    }
    button:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }
    /* Verdict pill, mirroring the identification feedback for a consistent voice. */
    .fb {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        align-self: flex-start;
        margin: 0.15rem 0 0;
        padding: 0.32rem 0.7rem;
        border-radius: var(--lsat-radius-pill);
        font-size: 0.82rem;
        font-weight: 600;
        color: var(--lsat-bad);
        background: var(--lsat-bad-soft);
    }
    .fb::before {
        content: "\2715";
        font-weight: 800;
    }
    .fb.right {
        color: var(--lsat-good);
        background: var(--lsat-good-soft);
    }
    .fb.right::before {
        content: "\2713";
    }

    @media (prefers-reduced-motion: reduce) {
        button {
            transition: none;
        }
        button:active:not(:disabled) {
            transform: none;
        }
    }
</style>
