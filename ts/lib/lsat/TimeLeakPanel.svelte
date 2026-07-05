<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Time-Leak tile: on items you got right timed AND untimed (so the answer was
never in doubt), how much clock time could you have reclaimed by pacing better?
We sum the per-item reclaimable seconds over "winnable" pairs and report it in
minutes with a bootstrap 95% CI. This is STRICTLY descriptive -- reclaimable
minutes are TIME, never a promised score or point gain (see the `framing`
footnote). It abstains until there is a blind (untimed) pass to compare against.
-->
<script lang="ts">
    import InsightCard from "./InsightCard.svelte";
    import type { Status, TimeLeakPanel } from "./types";

    export let panel: TimeLeakPanel = {};

    // Warn once there is a measurable leak to reclaim; a calm "good" when we have
    // evidence but nothing to reclaim; neutral (abstain) before that.
    function statusOf(available: boolean, measurable: boolean): Status {
        if (!available) {
            return "neutral";
        }
        if (measurable) {
            return "warn";
        }
        return "good";
    }

    /** seconds -> minutes string, one decimal (em dash when null). */
    function toMin(sec: number | null | undefined): string {
        return sec == null ? "—" : (sec / 60).toFixed(1);
    }

    $: status = statusOf(!!panel.available, !!panel.measurable_leak);
    $: overall = panel.overall ?? null;
    $: ciLow = overall?.reclaimable_ci_low ?? null;
    $: ciHigh = overall?.reclaimable_ci_high ?? null;
    $: hasCI = ciLow != null && ciHigh != null;
    $: nUnwinnable = overall?.n_unwinnable ?? 0;
    $: nWinnable = overall?.n_winnable ?? 0;
    $: splitTotal = nUnwinnable + nWinnable;
    $: winPct = splitTotal ? (nWinnable / splitTotal) * 100 : 0;
    // Skills with the most reclaimable time first, for a small breakdown.
    $: topSkills = [...(panel.skills ?? [])]
        .filter((s) => (s.reclaimable_seconds ?? 0) > 0)
        .sort((a, b) => (b.reclaimable_seconds ?? 0) - (a.reclaimable_seconds ?? 0))
        .slice(0, 3);
</script>

<InsightCard
    title="Time leak"
    subtitle="Reclaimable seconds"
    {status}
    available={!!panel.available}
    reason={panel.reason ?? ""}
    emptyHint="Do an untimed blind pass first, so we can measure the time you could reclaim."
>
    {#if panel.headline}<p class="headline">{panel.headline}</p>{/if}

    {#if panel.measurable_leak && overall}
        <div class="head">
            <div class="big s-{status}">
                {toMin(overall.reclaimable_seconds)}
                <span class="unit">min</span>
            </div>
            <div class="meta">
                <div class="metric">reclaimable time</div>
                <div class="sub">
                    {#if hasCI}
                        95% CI {toMin(ciLow)}&ndash;{toMin(ciHigh)} min
                    {:else}
                        estimated across your blind pass
                    {/if}
                </div>
            </div>
        </div>

        {#if splitTotal}
            <div class="split" aria-hidden="true">
                <span class="seg win" style="width:{winPct}%"></span>
            </div>
        {/if}
        <p class="split-cap">
            <b>{nUnwinnable}</b>
            unwinnable
            <span class="dot">&middot;</span>
            <b>{nWinnable}</b>
             winnable
        </p>

        {#if topSkills.length}
            <div class="rows">
                {#each topSkills as s (s.node_id)}
                    <div class="row">
                        <span class="lab">{s.name}</span>
                        <span class="val">{toMin(s.reclaimable_seconds)} min</span>
                    </div>
                {/each}
            </div>
        {/if}
    {/if}

    <!-- honesty framing: reclaimable minutes are time, never points. -->
    {#if panel.framing}<p class="note">{panel.framing}</p>{/if}
</InsightCard>

<style lang="scss">
    .headline {
        margin: 0 0 0.2rem;
        font-size: 0.9rem;
        line-height: 1.4;
    }
    .head {
        display: flex;
        align-items: center;
        gap: 0.7rem;
    }
    .big {
        font-size: 1.8rem;
        font-weight: 750;
        font-variant-numeric: tabular-nums;
        line-height: 1;
    }
    .big.s-warn {
        color: var(--lsat-warn);
    }
    .big.s-good {
        color: var(--lsat-good);
    }
    .unit {
        margin-left: 0.15rem;
        font-size: 0.5em;
        font-weight: 700;
        color: var(--lsat-fg-subtle);
    }
    .meta {
        font-size: 0.82rem;
        min-width: 0;
    }
    .metric {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
    }
    .sub {
        color: var(--lsat-fg-subtle);
        font-size: 0.74rem;
        font-variant-numeric: tabular-nums;
    }

    /* winnable share of scored pairs: the reclaimable slice, in warn tone */
    .split {
        display: flex;
        height: 7px;
        border-radius: var(--lsat-radius-pill);
        overflow: hidden;
        background: var(--lsat-inset);
        border: 1px solid var(--lsat-border-subtle);
        margin: 0.1rem 0 0;
    }
    .seg {
        height: 100%;
    }
    .seg.win {
        background: var(--lsat-warn);
        transition: width var(--lsat-transition) var(--lsat-ease);
    }
    .split-cap {
        margin: 0.15rem 0 0;
        font-size: 0.78rem;
        color: var(--lsat-fg-subtle);
        font-variant-numeric: tabular-nums;
    }
    .split-cap b {
        color: var(--lsat-fg);
    }
    .dot {
        margin: 0 0.15rem;
        color: var(--lsat-fg-faint);
    }

    /* per-skill reclaimable-time breakdown */
    .rows {
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
    }
    .row {
        display: grid;
        grid-template-columns: 1fr auto;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.8rem;
        font-variant-numeric: tabular-nums;
    }
    .lab {
        color: var(--lsat-fg-subtle);
        font-size: 0.78rem;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .val {
        text-align: right;
        font-weight: 650;
    }

    /* honesty framing: descriptive time, not a score/point promise. */
    .note {
        margin: 0.1rem 0 0;
        font-size: 0.72rem;
        line-height: 1.4;
        color: var(--lsat-fg-faint);
    }

    @media (prefers-reduced-motion: reduce) {
        .seg.win {
            transition: none;
        }
    }
</style>
