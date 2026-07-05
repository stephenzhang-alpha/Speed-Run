<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Are you as right as you feel? A reliability read that plots, for every stated
confidence band, what you *claimed* against what you *actually* got -- the gap
between the two is your miscalibration, summarised by the overconfidence index.
-->
<script lang="ts">
    import InsightCard from "./InsightCard.svelte";
    import type { CalibrationPanel, Status } from "./types";
    import { clamp01, signed, statusColor } from "./util";

    export let panel: CalibrationPanel = {};

    // Overconfidence index: > 0 means you claim more than you deliver.
    function statusOf(x: number | null): Status {
        if (x == null) {
            return "neutral";
        }
        if (x > 0.1) {
            return "bad";
        }
        if (x > 0.03) {
            return "warn";
        }
        return "good";
    }

    function verdictOf(x: number | null): string {
        if (x == null) {
            return "";
        }
        if (x > 0.1) {
            return "overconfident";
        }
        if (x > 0.03) {
            return "a touch overconfident";
        }
        if (x < -0.03) {
            return "underconfident";
        }
        return "well calibrated";
    }

    // Per-band calibration error (actual - stated): negative = overconfident.
    function relStatus(stated: number, actual: number): Status {
        const d = actual - stated;
        if (d <= -0.1) {
            return "bad";
        }
        if (d <= -0.03) {
            return "warn";
        }
        if (d >= 0.05) {
            return "neutral";
        }
        return "good";
    }

    $: oc = panel.overconfidence_index ?? null;
    $: status = statusOf(oc);
    $: verdict = verdictOf(oc);
    $: reliability = panel.reliability ?? [];
    $: sureWrong = panel.sure_and_wrong?.length ?? 0;
</script>

<InsightCard
    title="Calibration"
    subtitle="Confidence vs. reality"
    {status}
    available={!!panel.available}
    reason={panel.reason ?? ""}
    emptyHint="Tap your confidence on answers to see if you're as right as you feel."
>
    <div class="head">
        <div class="big s-{status}">{signed(oc)}</div>
        <div class="meta">
            <div class="metric">
                overconfidence
                {#if verdict}<span class="verdict" style="--c:{statusColor(status)}">
                        {verdict}
                    </span>{/if}
            </div>
            <div class="sub">
                resolution {panel.resolution_auc?.toFixed(2) ?? "—"} &middot; ECE
                {panel.ece?.toFixed(2) ?? "—"}
            </div>
        </div>
    </div>

    {#if reliability.length}
        <div class="rel">
            <div class="legend">
                <span>
                    <i class="mk claimed-mk"></i>
                    you said
                </span>
                <span>
                    <i class="mk actual-mk"></i>
                    you were
                </span>
            </div>
            <ul class="rows">
                {#each reliability as r (r.confidence_label)}
                    {@const stated = clamp01(r.stated_prob ?? 0) * 100}
                    {@const actual = clamp01(r.actual_accuracy ?? 0) * 100}
                    {@const st = relStatus(r.stated_prob ?? 0, r.actual_accuracy ?? 0)}
                    {@const lo = Math.min(stated, actual)}
                    {@const hi = Math.max(stated, actual)}
                    <li style="--c:{statusColor(st)}">
                        <span class="lbl">{r.confidence_label}</span>
                        <div class="track">
                            <span
                                class="gap"
                                style="left:{lo}%;width:{hi - lo}%"
                            ></span>
                            <span class="claimed" style="left:{stated}%"></span>
                            <span class="actual" style="left:{actual}%"></span>
                        </div>
                        <span class="vals">
                            <b>{Math.round(actual)}%</b>
                            <i>said {Math.round(stated)}%</i>
                        </span>
                    </li>
                {/each}
            </ul>
        </div>
    {/if}

    {#if sureWrong}
        <p class="footer">
            <span class="pin"></span>
            {sureWrong} "sure but wrong" to revisit
        </p>
    {/if}
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
    .big.s-bad {
        color: var(--lsat-bad);
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
        gap: 0.1rem;
    }
    .verdict {
        margin-left: 0.35rem;
        padding: 0.05rem 0.42rem;
        border-radius: var(--lsat-radius-pill);
        color: var(--c);
        background: color-mix(in srgb, var(--c) 15%, transparent);
        font-size: 0.62rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .sub {
        color: var(--lsat-fg-subtle);
        font-size: 0.74rem;
    }

    /* reliability diagram: stated (claimed) vs. actual accuracy per band */
    .rel {
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
        margin-top: 0.1rem;
    }
    .legend {
        display: flex;
        gap: 0.9rem;
        font-size: 0.64rem;
        color: var(--lsat-fg-subtle);
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .mk {
        display: inline-block;
        vertical-align: middle;
        margin-right: 0.3rem;
    }
    .claimed-mk {
        width: 2px;
        height: 11px;
        border-radius: 2px;
        background: var(--lsat-fg-faint);
    }
    .actual-mk {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: var(--lsat-fg-subtle);
    }
    .rows {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
    }
    .rows li {
        display: grid;
        grid-template-columns: 3rem 1fr 3.4rem;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.74rem;
    }
    .lbl {
        font-weight: 600;
        text-transform: capitalize;
    }
    .track {
        position: relative;
        height: 22px;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-inset);
        border: 1px solid var(--lsat-border-subtle);
    }
    /* faint gridlines at 25 / 50 / 75% so the track reads as a 0-100% scale */
    .track::before {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: inherit;
        background-image: repeating-linear-gradient(
            90deg,
            transparent 0,
            transparent calc(25% - 1px),
            var(--lsat-border-subtle) calc(25% - 1px),
            var(--lsat-border-subtle) 25%
        );
        opacity: 0.5;
    }
    /* the calibration error: the span between what you claimed and got */
    .gap {
        position: absolute;
        top: 50%;
        height: 5px;
        transform: translateY(-50%);
        border-radius: var(--lsat-radius-pill);
        background: var(--c);
        opacity: 0.5;
        transition:
            left var(--lsat-transition) var(--lsat-ease),
            width var(--lsat-transition) var(--lsat-ease);
    }
    .claimed {
        position: absolute;
        top: 3px;
        bottom: 3px;
        width: 2px;
        transform: translateX(-50%);
        border-radius: 2px;
        background: var(--lsat-fg-faint);
        transition: left var(--lsat-transition) var(--lsat-ease);
    }
    .actual {
        position: absolute;
        top: 50%;
        width: 11px;
        height: 11px;
        transform: translate(-50%, -50%);
        border-radius: 50%;
        background: var(--c);
        box-shadow:
            0 0 0 2px var(--lsat-surface),
            var(--lsat-shadow);
        transition: left var(--lsat-transition) var(--lsat-ease);
    }
    .vals {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        line-height: 1.1;
    }
    .vals b {
        font-weight: 700;
        font-variant-numeric: tabular-nums;
    }
    .vals i {
        font-style: normal;
        font-size: 0.62rem;
        color: var(--lsat-fg-subtle);
    }
    .footer {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        margin: 0.1rem 0 0;
        font-size: 0.78rem;
        color: var(--lsat-fg-subtle);
    }
    .pin {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--lsat-bad);
        flex: none;
    }

    @media (prefers-reduced-motion: reduce) {
        .gap,
        .claimed,
        .actual {
            transition: none;
        }
    }
</style>
