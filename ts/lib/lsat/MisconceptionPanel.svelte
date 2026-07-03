<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

SPOV 2 / B2+B4: the confidence x correctness states, the re-test ledger, and
grounded misconception hypotheses (each traceable to a taxonomy label).
-->
<script lang="ts">
    import InsightCard from "./InsightCard.svelte";
    import type { MisconceptionPanelData, Status } from "./types";
    import { statusColor } from "./util";

    export let panel: MisconceptionPanelData = {};

    $: s = panel.states ?? {};
    $: res = panel.resolution ?? { open: 0, resolved: 0, relapsed: 0 };
    $: owed = (res.open ?? 0) + (res.relapsed ?? 0);

    // Confidence x correctness, ordered solid -> danger so the bar reads as a
    // spectrum that ends on the "confident-wrong" danger zone.
    $: states = [
        {
            key: "mastery",
            label: "mastery",
            status: "good" as Status,
            count: s.mastery ?? 0,
        },
        {
            key: "fragile",
            label: "fragile",
            status: "warn" as Status,
            count: s.fragile ?? 0,
        },
        {
            key: "honest_gap",
            label: "honest gap",
            status: "neutral" as Status,
            count: s.honest_gap ?? 0,
        },
        {
            key: "misconception",
            label: "misconception",
            status: "bad" as Status,
            count: s.misconception ?? 0,
        },
    ];
</script>

<InsightCard
    title="Misconceptions"
    subtitle="Confident-wrong is the danger zone"
    status={owed > 0 ? "bad" : "good"}
    available={!!panel.available}
    reason={panel.reason ?? ""}
    emptyHint="Rate your confidence on answers; confident misses show up here."
>
    {#if panel.headline}<p class="headline">{panel.headline}</p>{/if}

    <!-- the four states as a single proportional spectrum -->
    <div class="spectrum" aria-hidden="true">
        {#each states as st (st.key)}
            {#if st.count > 0}
                <span
                    class="seg"
                    style="flex:{st.count};--c:{statusColor(st.status)}"
                ></span>
            {/if}
        {/each}
    </div>
    <ul class="legend">
        {#each states as st (st.key)}
            <li class:danger={st.key === "misconception"}>
                <span class="dot" style="--c:{statusColor(st.status)}"></span>
                <span class="k">{st.label}</span>
                <b class="v">{st.count}</b>
            </li>
        {/each}
    </ul>

    <!-- re-test ledger: confident errors owe a re-test until proven fixed -->
    <div class="ledger">
        <span class="lg-title">re-test ledger</span>
        <div class="lg-items">
            <span class="lg owed">
                <b>{res.open}</b>
                <span>owed</span>
            </span>
            <span class="lg ok">
                <b>{res.resolved}</b>
                <span>resolved</span>
            </span>
            {#if res.relapsed}
                <span class="lg bad">
                    <b>{res.relapsed}</b>
                    <span>relapsed</span>
                </span>
            {/if}
        </div>
    </div>

    {#if panel.hypotheses?.length}
        <ul class="hyps">
            {#each panel.hypotheses as h (h.item_id ?? h.source_label)}
                <li>
                    <span class="hyp-text">{h.text}</span>
                    <span class="src">{h.label}</span>
                </li>
            {/each}
        </ul>
    {/if}
</InsightCard>

<style lang="scss">
    .headline {
        margin: 0 0 0.1rem;
        font-size: 0.85rem;
        line-height: 1.4;
    }
    .spectrum {
        display: flex;
        gap: 2px; /* 2px surface gap between segments */
        height: 12px;
        padding: 2px;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-inset);
        box-shadow: inset 0 0 0 1px var(--lsat-border-subtle);
        overflow: hidden;
    }
    .seg {
        min-width: 4px;
        border-radius: var(--lsat-radius-pill);
        background:
            linear-gradient(
                180deg,
                rgba(255, 255, 255, 0.22) 0%,
                rgba(255, 255, 255, 0) 55%
            ),
            var(--c);
    }
    .legend {
        list-style: none;
        margin: 0.1rem 0 0;
        padding: 0;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.25rem 0.7rem;
        font-size: 0.78rem;
    }
    .legend li {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        min-width: 0;
    }
    .dot {
        flex: none;
        width: 0.55rem;
        height: 0.55rem;
        border-radius: 50%;
        background: var(--c);
    }
    .k {
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        color: var(--lsat-fg-subtle);
    }
    .v {
        flex: none;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
    }
    .legend li.danger .k {
        color: var(--lsat-fg);
        font-weight: 600;
    }
    .ledger {
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
        padding: 0.5rem 0.6rem;
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-inset);
        box-shadow: inset 0 0 0 1px var(--lsat-border-subtle);
    }
    .lg-title {
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--lsat-fg-faint);
    }
    .lg-items {
        display: flex;
        flex-wrap: wrap;
        gap: 0.7rem;
        font-size: 0.8rem;
        color: var(--lsat-fg-subtle);
    }
    .lg {
        display: inline-flex;
        align-items: baseline;
        gap: 0.25rem;
    }
    .lg b {
        font-size: 0.95rem;
        font-weight: 750;
        font-variant-numeric: tabular-nums;
        color: color-mix(in srgb, var(--c) 72%, var(--lsat-fg));
    }
    .lg.owed {
        --c: var(--lsat-warn);
    }
    .lg.ok {
        --c: var(--lsat-good);
    }
    .lg.bad {
        --c: var(--lsat-bad);
    }
    .hyps {
        list-style: none;
        margin: 0.1rem 0 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
        font-size: 0.8rem;
        line-height: 1.4;
    }
    .hyps li {
        padding-left: 0.6rem;
        border-left: 2px solid var(--lsat-border);
    }
    .hyp-text {
        color: var(--lsat-fg);
    }
    .src {
        display: inline-block;
        margin-left: 0.3rem;
        padding: 0.02rem 0.4rem;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-accent-soft);
        color: color-mix(in srgb, var(--lsat-accent) 78%, var(--lsat-fg));
        font-size: 0.68rem;
        font-weight: 600;
        white-space: nowrap;
    }
</style>
