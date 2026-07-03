<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    export let correct: boolean;
    export let correctLetter = "";
</script>

<div class="fb" class:correct class:wrong={!correct} role="status" aria-live="polite">
    <span class="icon" aria-hidden="true">
        {#if correct}
            <!-- a checkmark that draws itself in (transform/opacity-free stroke) -->
            <svg class="glyph draw" viewBox="0 0 24 24"><path d="M5 13 l4 4 L19 7" /></svg>
        {:else}
            <svg class="glyph" viewBox="0 0 24 24"><path d="M7 7 L17 17 M17 7 L7 17" /></svg>
        {/if}
    </span>
    <span class="msg">
        {#if correct}
            Correct
        {:else if correctLetter}
            Not quite &mdash; the answer is <b class="ltr">{correctLetter}</b>
        {:else}
            Not quite
        {/if}
    </span>
</div>

<style lang="scss">
    .fb {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.7rem 0.85rem;
        border-radius: var(--lsat-radius);
        border: 1px solid transparent;
        font-weight: 600;
        animation: fb-in var(--lsat-transition) var(--lsat-ease) both;
    }
    .fb.correct {
        background: var(--lsat-good-soft);
        border-color: color-mix(in srgb, var(--lsat-good) 35%, transparent);
        color: var(--lsat-good);
    }
    .fb.wrong {
        background: var(--lsat-bad-soft);
        border-color: color-mix(in srgb, var(--lsat-bad) 30%, transparent);
        color: var(--lsat-bad);
    }
    .msg {
        min-width: 0;
    }
    /* Circular verdict badge. */
    .icon {
        flex: 0 0 auto;
        display: grid;
        place-items: center;
        width: 26px;
        height: 26px;
        border-radius: var(--lsat-radius-pill);
    }
    .glyph {
        width: 15px;
        height: 15px;
        fill: none;
        stroke-width: 2.6;
        stroke-linecap: round;
        stroke-linejoin: round;
    }
    .fb.correct .icon {
        background: var(--lsat-good);
    }
    .fb.correct .glyph {
        stroke: #fff;
    }
    /* Correct: the check draws itself in (one-shot; a small trust signal). */
    .glyph.draw path {
        stroke-dasharray: 26;
        stroke-dashoffset: 26;
        animation: draw-check 340ms var(--lsat-ease) 60ms forwards;
    }
    /* Softer, non-punitive treatment on a miss — no draw, no shake. */
    .fb.wrong .icon {
        background: color-mix(in srgb, var(--lsat-bad) 18%, transparent);
    }
    .fb.wrong .glyph {
        stroke: var(--lsat-bad);
    }
    /* The credited letter reads as a positive pill, even inside the miss banner. */
    .ltr {
        display: inline-grid;
        place-items: center;
        min-width: 1.5em;
        padding: 0 0.35em;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-good-soft);
        color: var(--lsat-good);
        font-weight: 750;
        font-variant-numeric: tabular-nums;
    }

    @keyframes fb-in {
        from {
            opacity: 0;
            transform: translateY(4px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    @keyframes draw-check {
        to {
            stroke-dashoffset: 0;
        }
    }
    @media (prefers-reduced-motion: reduce) {
        .fb {
            animation: none;
        }
        .glyph.draw path {
            animation: none;
            stroke-dashoffset: 0;
        }
    }
</style>
