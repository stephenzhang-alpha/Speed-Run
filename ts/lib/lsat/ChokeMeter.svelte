<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Paired within-item Choke Index (DECISION-round2 #24): the mean of per-item
(untimed - timed) deltas over items answered BOTH ways, with a bootstrap 95% CI.
A positive index means you know more than the clock lets you show (a pacing gap,
not a knowledge gap); we only call it a *confident* gap when the CI excludes 0.
The estimate + CI are plotted on a number line centred on 0 (= no clock cost);
the unpaired accuracy aggregate is shown as a labelled low-confidence fallback.
-->
<script lang="ts">
    import InsightCard from "./InsightCard.svelte";
    import type { ChokePanel, PacingPanel, Status } from "./types";
    import { clamp01, msToSeconds, pct, signed, statusColor } from "./util";

    export let panel: ChokePanel = {};
    export let pacing: PacingPanel = {};

    // A confident positive gap is the actionable case (warn); otherwise neutral.
    function statusOf(index: number | null, flag: boolean): Status {
        if (index == null) {
            return "neutral";
        }
        if (flag) {
            return "warn";
        }
        return "good";
    }

    $: choke = panel.overall?.choke_index ?? null;
    $: flagged = !!panel.overall?.flag;
    $: ciLow = panel.overall?.ci_low ?? null;
    $: ciHigh = panel.overall?.ci_high ?? null;
    $: hasCI = ciLow != null && ciHigh != null;
    $: status = statusOf(choke, flagged);
    $: fb = panel.fallback?.overall ?? null;

    // Symmetric scale around 0 that comfortably contains the estimate and CI.
    $: bound =
        Math.max(0.12, Math.abs(ciLow ?? 0), Math.abs(ciHigh ?? 0), Math.abs(choke ?? 0)) *
        1.2;
    // Map a signed delta onto the 0-100% track (0 sits at the centre).
    $: toPct = (v: number) => clamp01((v / bound + 1) / 2) * 100;
    $: pZero = toPct(0);
    $: pChoke = choke == null ? null : toPct(choke);
    $: pLow = ciLow == null ? null : toPct(ciLow);
    $: pHigh = ciHigh == null ? null : toPct(ciHigh);
</script>

<InsightCard
    title="Pacing & choke"
    subtitle="What the clock costs you"
    {status}
    available={!!panel.available}
    reason={panel.note ?? panel.reason ?? ""}
    emptyHint="Answer items timed, then blind-review them, to measure the clock's cost."
>
    <div class="head">
        <div class="big s-{status}">{signed(choke)}</div>
        <div class="meta">
            <div class="metric">
                paced choke index
                {#if flagged}<span class="chip">confident gap</span>{/if}
            </div>
            <div class="sub">
                {#if hasCI}
                    95% CI {signed(ciLow)}&ndash;{signed(ciHigh)}
                    {#if panel.overall?.n_paired}&middot; {panel.overall.n_paired} paired{/if}
                {:else}
                    within-item paired estimate
                {/if}
            </div>
        </div>
    </div>

    {#if pChoke != null}
        <div class="line" style="--c:{statusColor(status)}">
            <span class="axis"></span>
            <span class="zero" style="left:{pZero}%"></span>
            {#if hasCI && pLow != null && pHigh != null}
                <span class="band" style="left:{pLow}%;width:{Math.max(pHigh - pLow, 2)}%"></span>
            {/if}
            <span class="point" style="left:{pChoke}%"></span>
        </div>
        <div class="scale">
            <span class="end">timed wins</span>
            <span class="zt" style="left:{pZero}%">0</span>
            <span class="end hi">clock costs you</span>
        </div>
        <p class="axis-note">
            {#if hasCI}
                Bar is the 95% CI. Right of 0 = points the clock is hiding.
            {:else}
                Right of 0 = points the clock is hiding.
            {/if}
        </p>
    {/if}

    {#if fb}
        <p class="footer">
            unpaired: untimed {pct(fb.untimed_accuracy)} vs timed {pct(fb.timed_accuracy)}
            <span class="tag">low-confidence</span>
        </p>
    {/if}
    {#if pacing.available && pacing.overall}
        <p class="footer">
            median {msToSeconds(pacing.overall.median_response_ms)} &middot;
            {Math.round((pacing.overall.slow_share ?? 0) * 100)}% slow
        </p>
    {/if}
    {#if panel.headline}<p class="footer">{panel.headline}</p>{/if}
</InsightCard>

<style lang="scss">
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
    .meta {
        font-size: 0.82rem;
        min-width: 0;
    }
    .metric {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
    }
    .chip {
        margin-left: 0.35rem;
        padding: 0.05rem 0.4rem;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-warn-soft);
        color: var(--lsat-warn);
        font-size: 0.66rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .sub {
        color: var(--lsat-fg-subtle);
        font-size: 0.74rem;
    }

    /* the CI number line: estimate (dot) + 95% CI (band) over a 0 reference */
    .line {
        position: relative;
        height: 26px;
        margin-top: 0.1rem;
    }
    .axis {
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        height: 6px;
        transform: translateY(-50%);
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-inset);
        border: 1px solid var(--lsat-border-subtle);
    }
    .zero {
        position: absolute;
        top: 2px;
        bottom: 2px;
        width: 2px;
        transform: translateX(-50%);
        border-radius: 2px;
        background: var(--lsat-fg-faint);
    }
    .band {
        position: absolute;
        top: 50%;
        height: 10px;
        transform: translateY(-50%);
        border-radius: var(--lsat-radius-pill);
        background: color-mix(in srgb, var(--c) 26%, transparent);
        border: 1px solid color-mix(in srgb, var(--c) 55%, transparent);
        transition: left var(--lsat-transition) var(--lsat-ease),
            width var(--lsat-transition) var(--lsat-ease);
    }
    .point {
        position: absolute;
        top: 50%;
        width: 13px;
        height: 13px;
        transform: translate(-50%, -50%);
        border-radius: 50%;
        background: var(--c);
        box-shadow: 0 0 0 2.5px var(--lsat-surface), var(--lsat-shadow);
        transition: left var(--lsat-transition) var(--lsat-ease);
    }
    .scale {
        position: relative;
        height: 0.95rem;
        font-size: 0.64rem;
        color: var(--lsat-fg-subtle);
    }
    .end {
        position: absolute;
        left: 0;
        top: 0;
    }
    .end.hi {
        left: auto;
        right: 0;
    }
    .zt {
        position: absolute;
        top: 0;
        transform: translateX(-50%);
        font-weight: 700;
        color: var(--lsat-fg);
        font-variant-numeric: tabular-nums;
    }
    .axis-note {
        margin: 0.1rem 0 0;
        font-size: 0.68rem;
        line-height: 1.35;
        color: var(--lsat-fg-subtle);
    }
    .tag {
        font-size: 0.66rem;
        opacity: 0.7;
        font-style: italic;
    }
    .footer {
        margin: 0.1rem 0 0;
        font-size: 0.78rem;
        color: var(--lsat-fg-subtle);
    }

    @media (prefers-reduced-motion: reduce) {
        .band,
        .point {
            transition: none;
        }
    }
</style>
