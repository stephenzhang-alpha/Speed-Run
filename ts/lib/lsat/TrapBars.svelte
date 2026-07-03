<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import Bar from "./Bar.svelte";
    import InsightCard from "./InsightCard.svelte";
    import type { TrapPanel } from "./types";
    import { humanize } from "./util";

    export let panel: TrapPanel = {};

    $: families = Object.entries(panel.by_family ?? {}).sort(
        (a, b) => (b[1].share ?? 0) - (a[1].share ?? 0),
    );
</script>

<InsightCard
    title="Trap fingerprint"
    subtitle="Which answer traps keep catching you"
    status="bad"
    available={!!panel.available}
    reason={panel.reason ?? ""}
    emptyHint="Miss a few trap answers and this maps which traps own you."
>
    {#if panel.headline}<p class="headline">{panel.headline}</p>{/if}
    <ol class="chart">
        {#each families as [fam, v], i (fam)}
            <li class:lead={i === 0}>
                <div class="row">
                    <span class="rank" aria-hidden="true">{i + 1}</span>
                    <span class="name">{humanize(fam)}</span>
                    <b class="val">{Math.round((v.share ?? 0) * 100)}%</b>
                </div>
                <Bar value={v.share ?? 0} status="bad" height={8} />
            </li>
        {/each}
    </ol>
    <p class="caption">
        A longer bar is a trap that catches you more often &mdash; each one a fixable
        habit once you learn its tell.
    </p>
</InsightCard>

<style lang="scss">
    .headline {
        margin: 0 0 0.2rem;
        font-size: 0.9rem;
        line-height: 1.4;
    }
    .chart {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.6rem;
    }
    .row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.3rem;
        font-size: 0.82rem;
    }
    .rank {
        flex: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.2rem;
        height: 1.2rem;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-inset);
        box-shadow: inset 0 0 0 1px var(--lsat-border-subtle);
        color: var(--lsat-fg-faint);
        font-size: 0.68rem;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
    }
    .name {
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .val {
        flex: none;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
        color: var(--lsat-fg);
    }
    /* The #1 trap gets the spotlight: a filled rank + a bolder name. */
    .lead .rank {
        color: color-mix(in srgb, var(--lsat-bad) 72%, var(--lsat-fg));
        background: var(--lsat-bad-soft);
        box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--lsat-bad) 30%, transparent);
    }
    .lead .name {
        font-weight: 650;
    }
    .caption {
        margin: 0.15rem 0 0;
        font-size: 0.75rem;
        line-height: 1.4;
        color: var(--lsat-fg-subtle);
    }
</style>
