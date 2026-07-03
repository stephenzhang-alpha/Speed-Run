<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

One of the three headline scores (Memory / Performance / Readiness), rebuilt on
the "PROVEN" language: a solid, high-contrast MONO numeral (never gradient-clipped
— trustworthy numbers must look trustworthy) sitting over a confidence-INTERVAL
band. When the score has not earned its evidence it shows an honest abstain badge
+ a hatched "earning evidence" meter (a countable goal, not a broken em-dash).
-->
<script lang="ts">
    import Card from "./Card.svelte";
    import IntervalBand from "./IntervalBand.svelte";
    import ProvenanceBadge from "./ProvenanceBadge.svelte";

    export let title: string;
    export let available = true;
    export let big = ""; // earned headline value, e.g. "72%" or "162"
    export let unit = "";
    export let min: number;
    export let max: number;
    export let point: number | null = null;
    export let low: number | null = null;
    export let high: number | null = null;
    // abstain state
    export let earnedNote = "";
    export let unlockLabel = "";
    export let progress: number | null = null;
    export let widened = false;
    export let note = "";
</script>

<Card {title} flat>
    <div class="head">
        {#if available}
            <div class="value">{big}</div>
        {:else}
            <ProvenanceBadge tier="abstain" label="Earning evidence" />
        {/if}
    </div>

    <IntervalBand
        {available}
        {min}
        {max}
        {point}
        {low}
        {high}
        {unit}
        {earnedNote}
        {unlockLabel}
        {progress}
        {widened}
    />

    {#if note}<p class="note">{note}</p>{/if}
    <slot />
</Card>

<style lang="scss">
    .head {
        min-height: 2.3rem;
        display: flex;
        align-items: center;
    }
    /* Solid, tabular, high-contrast — a number you can trust. */
    .value {
        font-family: var(--lsat-mono);
        font-size: var(--lsat-display);
        font-weight: var(--lsat-num);
        line-height: 1.02;
        letter-spacing: -0.01em;
        font-variant-numeric: tabular-nums slashed-zero;
        color: var(--lsat-fg);
    }
    .note {
        margin: 0.5rem 0 0;
        font-size: 0.78rem;
        color: var(--lsat-fg-subtle);
        line-height: 1.4;
    }
</style>
