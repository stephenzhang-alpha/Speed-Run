<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

One-tap confidence rating shown after a choice is picked (skippable). Emits the
selected label ("sure" | "likely" | "guess" | "").
-->
<script lang="ts">
    import { createEventDispatcher } from "svelte";

    const dispatch = createEventDispatcher<{ select: string }>();
    const opts: [string, string][] = [
        ["sure", "Sure"],
        ["likely", "Likely"],
        ["guess", "Guess"],
    ];
</script>

<div class="conf">
    <span class="q" id="conf-q">How sure?</span>
    <div class="btns" role="group" aria-labelledby="conf-q">
        {#each opts as [val, label] (val)}
            <button
                type="button"
                class="opt"
                class:sure={val === "sure"}
                class:likely={val === "likely"}
                class:guess={val === "guess"}
                on:click={() => dispatch("select", val)}
            >
                <span class="dot" aria-hidden="true"></span>{label}
            </button>
        {/each}
        <button type="button" class="skip" on:click={() => dispatch("select", "")}>skip</button>
    </div>
</div>

<style lang="scss">
    .conf {
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
    .btns {
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
    }
    button {
        flex: 1 1 auto;
        min-height: 44px;
        padding: 0.5rem 0.8rem;
        border-radius: var(--lsat-radius-pill);
        border: 1.5px solid var(--lsat-border);
        background: var(--lsat-surface);
        color: var(--lsat-fg);
        font: inherit;
        font-weight: 600;
        cursor: pointer;
        transition:
            border-color var(--lsat-transition) var(--lsat-ease),
            background var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease);
    }
    /* Confidence-coded options: a leading dot reads at a glance. */
    .opt {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.45rem;
    }
    .opt .dot {
        width: 9px;
        height: 9px;
        border-radius: var(--lsat-radius-pill);
        background: var(--dot);
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--dot) 22%, transparent);
    }
    .opt.sure {
        --dot: var(--lsat-good);
    }
    .opt.likely {
        --dot: var(--lsat-accent);
    }
    .opt.guess {
        --dot: var(--lsat-warn);
    }
    .opt:hover {
        border-color: var(--dot);
        background: color-mix(in srgb, var(--dot) 10%, transparent);
    }
    .opt:active {
        transform: scale(0.97);
    }
    .skip {
        flex: 0 0 auto;
        border-style: dashed;
        color: var(--lsat-fg-subtle);
        font-weight: 500;
    }
    .skip:hover {
        border-color: var(--lsat-accent);
    }
    .skip:active {
        transform: scale(0.97);
    }

    @media (prefers-reduced-motion: reduce) {
        button {
            transition: none;
        }
        .opt:active,
        .skip:active {
            transform: none;
        }
    }
</style>
