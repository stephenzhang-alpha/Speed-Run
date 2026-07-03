<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Elaborated Contrast Card (DECISION-round2 #13): on a miss, a two-column contrast
of why the credited answer is credited (left) vs why the letter you picked is a
trap (right), plus the one-line "minimal edit" that would make that trap correct.
Deterministic content from lsat/contrast.py -- no AI at feedback time. Renders
nothing when the contrast abstains.
-->
<script lang="ts">
    import type { AnswerContrast } from "./types";

    export let contrast: AnswerContrast;
    export let chosen = "";

    // Both sides present => render the centred "vs" pivot and the paired layout.
    $: paired = !!(contrast.why_credited && contrast.trap);
</script>

{#if contrast.available && (contrast.why_credited || contrast.trap)}
    <div class="contrast" class:paired>
        {#if contrast.why_credited}
            <div class="col credited">
                <span class="hd">
                    <svg class="hd-ic" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M20 6 9 17l-5-5" />
                    </svg>
                    Why the credited answer wins
                </span>
                <p>{contrast.why_credited}</p>
            </div>
        {/if}
        {#if paired}
            <span class="vs" aria-hidden="true">vs</span>
        {/if}
        {#if contrast.trap}
            <div class="col trap">
                <span class="hd">
                    <svg class="hd-ic" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M12 3 2 20h20L12 3zM12 10v4m0 3v.5" />
                    </svg>
                    Why ({chosen}) is a trap
                </span>
                <span class="trap-label">{contrast.trap.label}</span>
                <p>{contrast.trap.minimal_edit}</p>
                <span class="tip">
                    <svg class="tip-ic" viewBox="0 0 24 24" aria-hidden="true">
                        <path
                            d="M9 18h6m-5 3h4M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.2 1 2.5h6c0-1.3.3-1.8 1-2.5A6 6 0 0 0 12 3z"
                        />
                    </svg>
                    Fixable habit: {contrast.trap.tip}
                </span>
            </div>
        {/if}
    </div>
{/if}

<style lang="scss">
    .contrast {
        display: grid;
        grid-template-columns: 1fr;
        gap: 0.55rem;
        margin: 0.65rem 0 0.2rem;
    }
    /* Paired: credited | pivot | trap on a wide viewport. */
    .contrast.paired {
        grid-template-columns: 1fr auto 1fr;
        align-items: stretch;
    }
    @media (max-width: 460px) {
        .contrast.paired {
            grid-template-columns: 1fr;
        }
    }
    .col {
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
        padding: 0.75rem 0.8rem;
        border-radius: var(--lsat-radius);
        border: 1px solid var(--lsat-border);
        font-size: 0.86rem;
        line-height: 1.45;
        box-shadow: var(--lsat-shadow);
        animation: col-in var(--lsat-transition) var(--lsat-ease) both;
    }
    .col.credited {
        background: var(--lsat-good-soft);
        border-color: color-mix(in srgb, var(--lsat-good) 45%, transparent);
    }
    .col.trap {
        background: var(--lsat-bad-soft);
        border-color: color-mix(in srgb, var(--lsat-bad) 40%, transparent);
        animation-delay: 60ms;
    }
    .hd {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        font-weight: 700;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .credited .hd {
        color: var(--lsat-good);
    }
    .trap .hd {
        color: var(--lsat-bad);
    }
    .hd-ic {
        flex: 0 0 auto;
        width: 15px;
        height: 15px;
        fill: none;
        stroke: currentColor;
        stroke-width: 2.2;
        stroke-linecap: round;
        stroke-linejoin: round;
    }
    .col p {
        margin: 0;
        color: var(--lsat-fg);
    }
    /* The trap's family, called out as a distinct pill. */
    .trap-label {
        align-self: flex-start;
        padding: 0.14rem 0.55rem;
        border-radius: var(--lsat-radius-pill);
        background: color-mix(in srgb, var(--lsat-bad) 16%, transparent);
        color: var(--lsat-bad);
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .tip {
        display: flex;
        align-items: flex-start;
        gap: 0.35rem;
        margin-top: 0.1rem;
        font-size: 0.78rem;
        color: var(--lsat-fg-subtle);
    }
    .tip-ic {
        flex: 0 0 auto;
        width: 14px;
        height: 14px;
        margin-top: 0.12rem;
        fill: none;
        stroke: currentColor;
        stroke-width: 1.8;
        stroke-linecap: round;
        stroke-linejoin: round;
    }
    /* Signature pivot between the two verdicts: a gradient "vs" chip. It sits in
     * the centre column when wide, and between the stacked cards when narrow. */
    .vs {
        align-self: center;
        justify-self: center;
        display: grid;
        place-items: center;
        width: 34px;
        height: 34px;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-hero);
        color: #fff;
        font-size: 0.66rem;
        font-weight: 750;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        box-shadow: var(--lsat-shadow-lift);
    }

    @keyframes col-in {
        from {
            opacity: 0;
            transform: translateY(5px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    @media (prefers-reduced-motion: reduce) {
        .col {
            animation: none;
        }
    }
</style>
