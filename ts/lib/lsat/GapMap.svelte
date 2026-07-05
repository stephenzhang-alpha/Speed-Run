<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

The Blind-Review 2x2: a timed x untimed confusion matrix that separates a
knowledge gap from a pacing gap. Rows = timed outcome, columns = untimed
outcome; each quadrant is colour-coded by what it means and sized by its share.
-->
<script lang="ts">
    import InsightCard from "./InsightCard.svelte";
    import type { GapCounts, GapMapPanel, Status } from "./types";

    export let panel: GapMapPanel = {};

    $: counts = (panel.overall?.counts ?? {}) as Partial<GapCounts>;
    $: total = (Object.values(counts) as (number | undefined)[]).reduce<number>(
        (a, b) => a + (b ?? 0),
        0,
    );

    // Matrix reading order (row-major): timed-right row, then timed-wrong row.
    const cells: {
        key: keyof GapCounts;
        label: string;
        hint: string;
        status: Status;
    }[] = [
        {
            key: "mastered",
            label: "Mastered",
            hint: "timed + untimed right",
            status: "good",
        },
        {
            key: "fragile",
            label: "Fragile",
            hint: "timed right, untimed wrong",
            status: "warn",
        },
        {
            key: "pressure",
            label: "Pressure",
            hint: "only right untimed → pacing",
            status: "neutral",
        },
        {
            key: "knowledge",
            label: "Knowledge",
            hint: "wrong either way → content",
            status: "bad",
        },
    ];
</script>

<InsightCard
    title="Timed vs. untimed"
    subtitle="Don't-know-it vs. ran-out-of-time"
    status="neutral"
    available={!!panel.available}
    reason={panel.reason ?? ""}
    emptyHint="Do an untimed blind-review pass to split knowledge gaps from pacing gaps."
>
    {#if panel.headline}<p class="headline">{panel.headline}</p>{/if}

    {#if total}
        <div class="mix" aria-hidden="true">
            {#each cells as cell (cell.key)}
                {@const s = (counts[cell.key] ?? 0) / total}
                {#if s > 0}
                    <span
                        class="seg s-{cell.status}"
                        style="width:{s * 100}%"
                        title="{cell.label} {Math.round(s * 100)}%"
                    ></span>
                {/if}
            {/each}
        </div>
    {/if}

    <div class="matrix">
        <span class="axis-name col">Untimed</span>
        <span class="chd c1">right</span>
        <span class="chd c2">wrong</span>
        <span class="axis-name row">Timed</span>
        <span class="rhd r1">right</span>
        <span class="rhd r2">wrong</span>
        {#each cells as cell, i (cell.key)}
            {@const n = counts[cell.key] ?? 0}
            {@const s = total ? n / total : 0}
            {@const rr = 3 + Math.floor(i / 2)}
            {@const cc = 3 + (i % 2)}
            <div class="cell s-{cell.status}" style="grid-row:{rr};grid-column:{cc}">
                <div class="cell-top">
                    <span class="n">{n}</span>
                    {#if total}<span class="sh">{Math.round(s * 100)}%</span>{/if}
                </div>
                <div class="label">{cell.label}</div>
                <div class="hint">{cell.hint}</div>
                <span class="cell-bar" style="width:{s * 100}%"></span>
            </div>
        {/each}
    </div>

    {#if total}
        <p class="foot">{total} items scored both timed and untimed</p>
    {/if}
</InsightCard>

<style lang="scss">
    .headline {
        margin: 0 0 0.2rem;
        font-size: 0.9rem;
        line-height: 1.4;
    }

    /* one-glance mix: proportional split across the four quadrants */
    .mix {
        display: flex;
        height: 7px;
        border-radius: var(--lsat-radius-pill);
        overflow: hidden;
        background: var(--lsat-inset);
        border: 1px solid var(--lsat-border-subtle);
        margin: 0 0 0.15rem;
    }
    .seg {
        height: 100%;
        transition: width var(--lsat-transition) var(--lsat-ease);
    }
    .seg.s-good {
        background: var(--lsat-good);
    }
    .seg.s-warn {
        background: var(--lsat-warn);
    }
    .seg.s-bad {
        background: var(--lsat-bad);
    }
    .seg.s-neutral {
        background: var(--lsat-accent);
    }

    /* the 2x2 matrix with timed (rows) x untimed (columns) axes */
    .matrix {
        display: grid;
        grid-template-columns: 0.95rem 0.95rem 1fr 1fr;
        grid-template-rows: auto auto 1fr 1fr;
        column-gap: 0.4rem;
        row-gap: 0.35rem;
        align-items: stretch;
    }
    .axis-name {
        font-size: 0.62rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
        color: var(--lsat-fg-subtle);
        align-self: center;
        justify-self: center;
    }
    .axis-name.col {
        grid-column: 3 / 5;
        grid-row: 1;
    }
    .axis-name.row {
        grid-column: 1;
        grid-row: 3 / 5;
        writing-mode: vertical-rl;
        transform: rotate(180deg);
    }
    .chd {
        grid-row: 2;
        text-align: center;
        font-size: 0.66rem;
        font-weight: 600;
        color: var(--lsat-fg-subtle);
    }
    .chd.c1 {
        grid-column: 3;
    }
    .chd.c2 {
        grid-column: 4;
    }
    .rhd {
        grid-column: 2;
        align-self: center;
        justify-self: center;
        font-size: 0.66rem;
        font-weight: 600;
        color: var(--lsat-fg-subtle);
        writing-mode: vertical-rl;
        transform: rotate(180deg);
    }
    .rhd.r1 {
        grid-row: 3;
    }
    .rhd.r2 {
        grid-row: 4;
    }
    .cell {
        position: relative;
        overflow: hidden;
        border-radius: var(--lsat-radius-sm);
        padding: 0.5rem 0.55rem 0.6rem;
        background: var(--lsat-inset);
        border: 1px solid var(--lsat-border-subtle);
        border-left: 3px solid var(--lsat-fg-faint);
        display: flex;
        flex-direction: column;
        gap: 0.08rem;
    }
    .cell.s-good {
        border-left-color: var(--lsat-good);
        background: var(--lsat-good-soft);
    }
    .cell.s-warn {
        border-left-color: var(--lsat-warn);
        background: var(--lsat-warn-soft);
    }
    .cell.s-bad {
        border-left-color: var(--lsat-bad);
        background: var(--lsat-bad-soft);
    }
    .cell.s-neutral {
        border-left-color: var(--lsat-accent);
        background: var(--lsat-accent-soft);
    }
    .cell-top {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 0.3rem;
    }
    .n {
        font-size: 1.35rem;
        font-weight: 750;
        font-variant-numeric: tabular-nums;
        line-height: 1;
    }
    .sh {
        font-size: 0.66rem;
        color: var(--lsat-fg-subtle);
        font-variant-numeric: tabular-nums;
    }
    .label {
        font-size: 0.8rem;
        font-weight: 650;
    }
    .hint {
        font-size: 0.68rem;
        color: var(--lsat-fg-subtle);
        line-height: 1.25;
    }
    /* share-of-total footing bar, coloured to match the quadrant */
    .cell-bar {
        position: absolute;
        left: 0;
        bottom: 0;
        height: 3px;
        transition: width var(--lsat-transition) var(--lsat-ease);
    }
    .cell.s-good .cell-bar {
        background: var(--lsat-good);
    }
    .cell.s-warn .cell-bar {
        background: var(--lsat-warn);
    }
    .cell.s-bad .cell-bar {
        background: var(--lsat-bad);
    }
    .cell.s-neutral .cell-bar {
        background: var(--lsat-accent);
    }
    .foot {
        margin: 0.15rem 0 0;
        font-size: 0.72rem;
        color: var(--lsat-fg-subtle);
    }

    @media (prefers-reduced-motion: reduce) {
        .seg,
        .cell-bar {
            transition: none;
        }
    }
</style>
