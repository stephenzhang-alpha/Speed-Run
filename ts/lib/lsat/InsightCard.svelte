<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Shared wrapper for the "How you get questions wrong" insight panels: a titled
card that renders its content slot when the panel has evidence, and a calm,
non-punitive abstain message (never an error) when it does not.
-->
<script lang="ts">
    import Card from "./Card.svelte";
    import type { Status } from "./types";

    export let title: string;
    export let subtitle = "";
    export let status: Status = "neutral";
    export let available = true;
    export let reason = "";
    export let emptyHint = "";
</script>

<Card {title} {subtitle} {status}>
    {#if available}
        <slot />
    {:else}
        <div class="empty">
            <!-- A ghosted little chart: the panel's shape, waiting to be filled.
                 Calm and inviting -- an abstain, never an error. -->
            <span class="emblem" aria-hidden="true">
                <span class="ghost b1"></span>
                <span class="ghost b2"></span>
                <span class="ghost b3"></span>
            </span>
            <p>{reason || emptyHint || "Not enough evidence yet."}</p>
        </div>
    {/if}
</Card>

<style lang="scss">
    .empty {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        padding: 0.2rem 0;
        color: var(--lsat-fg-subtle);
    }
    .emblem {
        flex: none;
        display: inline-flex;
        align-items: flex-end;
        gap: 3px;
        width: 2.5rem;
        height: 2.5rem;
        padding: 0.55rem;
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-accent-soft);
        box-shadow: inset 0 0 0 1px var(--lsat-border-subtle);
    }
    .ghost {
        flex: 1;
        border-radius: 2px;
        background: color-mix(in srgb, var(--lsat-accent) 32%, transparent);
    }
    /* rising, ghosted bars -- your data will draw itself here */
    .b1 {
        height: 42%;
        opacity: 0.5;
    }
    .b2 {
        height: 68%;
        opacity: 0.72;
    }
    .b3 {
        height: 100%;
        opacity: 0.92;
    }
    p {
        margin: 0;
        font-size: 0.82rem;
        line-height: 1.45;
    }

    @media (prefers-reduced-motion: no-preference) {
        .emblem {
            animation: lsat-empty-breathe 3.2s var(--lsat-ease) infinite;
        }
        @keyframes lsat-empty-breathe {
            0%,
            100% {
                opacity: 0.72;
            }
            50% {
                opacity: 1;
            }
        }
    }
</style>
