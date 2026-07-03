<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import type { Status } from "./types";
    import { statusColor } from "./util";

    export let title = "";
    export let subtitle = "";
    export let status: Status = "neutral";
    export let accent = false;
    // Semantic elevation: `flat` = recorded evidence (hairline inset, no hover
    // lift); default keeps the restrained resting shadow. `action` = interactive
    // (a hover lift is appropriate). Only ONE tier should read as "liftable".
    export let flat = false;
    export let action = false;

    $: c = statusColor(status);
</script>

<section class="lsat-card" class:accent class:flat class:action style="--c:{c}">
    {#if title}
        <header>
            <h3>{title}</h3>
            {#if subtitle}<p class="sub">{subtitle}</p>{/if}
        </header>
    {/if}
    <slot />
</section>

<style lang="scss">
    .lsat-card {
        position: relative;
        background: var(--lsat-surface);
        border: 1px solid var(--lsat-border-subtle);
        border-radius: var(--lsat-radius);
        padding: var(--lsat-pad);
        box-shadow: var(--lsat-shadow);
        color: var(--lsat-fg);
        display: flex;
        flex-direction: column;
        gap: 0.55rem;
        overflow: hidden; /* clip the accent strip to the rounded corners */
        transition:
            box-shadow var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease),
            border-color var(--lsat-transition) var(--lsat-ease);

        /* Recorded EVIDENCE: a flat hairline, never lifts (semantic elevation). */
        &.flat {
            box-shadow: var(--lsat-elev-evidence);
        }
        /* ACTIONABLE surfaces earn the hover lift. */
        &.action:hover {
            box-shadow: var(--lsat-shadow-lift);
            transform: translateY(-1px);
        }

        /* Accent cards (the three headline scores) get a signature gradient
         * strip tinted toward the status colour, with a faint header wash. */
        &.accent {
            border-top-color: transparent;
        }
        &.accent::before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 3px;
            background: linear-gradient(
                90deg,
                var(--c) 0%,
                color-mix(in srgb, var(--c) 45%, var(--lsat-accent-2)) 100%
            );
        }
        &.accent::after {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 68px;
            background: linear-gradient(
                180deg,
                color-mix(in srgb, var(--c) 8%, transparent) 0%,
                transparent 100%
            );
            pointer-events: none;
        }
    }
    header {
        min-width: 0;
        position: relative;
    }
    h3 {
        margin: 0;
        font-size: 0.95rem;
        font-weight: 650;
        letter-spacing: 0.01em;
    }
    .sub {
        margin: 0.15rem 0 0;
        font-size: 0.78rem;
        color: var(--lsat-fg-subtle);
        line-height: 1.35;
    }
    /* Keep slotted content above the ::after header wash. */
    .lsat-card > :global(*) {
        position: relative;
    }

    @media (prefers-reduced-motion: reduce) {
        .lsat-card {
            transition: none;
        }
        .lsat-card.action:hover {
            transform: none;
        }
    }
</style>
