<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Rush-Error tile: on items answered faster than a personal speed threshold, do you
miss more than you do at your normal pace? We compare the error rate on fast
answers against the error rate on the rest, and report the excess in percentage
points with a bootstrap 95% CI. This is a *gentle* diagnostic -- a nudge to slow
down on flagged skills, never a punitive score (see the `framing` footnote). It
abstains until there are enough timed + baseline answers to say anything at all.
-->
<script lang="ts">
    import Bar from "./Bar.svelte";
    import InsightCard from "./InsightCard.svelte";
    import type { RushPanel, Status } from "./types";
    import { pct, signedPoints } from "./util";

    export let panel: RushPanel = {};

    // Warn only when the estimator confidently flags rushing; a calm "good" once
    // we have evidence but no flag; neutral (abstain) before that.
    function statusOf(available: boolean, flag: boolean): Status {
        if (!available) {
            return "neutral";
        }
        if (flag) {
            return "warn";
        }
        return "good";
    }

    /** signed points range, e.g. "+40..+78 pts" (empty when incomplete). */
    function ptsRange(low: number | null, high: number | null): string {
        if (low == null || high == null) {
            return "";
        }
        const l = Math.round(low * 100);
        const h = Math.round(high * 100);
        return `${l > 0 ? "+" : ""}${l}..${h > 0 ? "+" : ""}${h} pts`;
    }

    $: overall = panel.overall ?? null;
    $: flagged = !!overall?.flag;
    $: status = statusOf(!!panel.available, flagged);
    $: excess = overall?.rush_excess ?? null;
    $: ciLow = overall?.excess_ci_low ?? null;
    $: ciHigh = overall?.excess_ci_high ?? null;
    $: hasCI = ciLow != null && ciHigh != null;
    $: excessCi = ptsRange(ciLow, ciHigh);
    // Flagged skills, by display name (derived from the per-skill flags).
    $: flaggedNames = (panel.skills ?? []).filter((s) => s.flag).map((s) => s.name);
</script>

<InsightCard
    title="Rush errors"
    subtitle="Fast answers, extra misses"
    {status}
    available={!!panel.available}
    reason={panel.note ?? ""}
    emptyHint="Answer items timed, then blind-review some untimed, to measure rushing."
>
    {#if panel.headline}<p class="headline">{panel.headline}</p>{/if}

    <div class="head">
        <div class="big s-{status}">{signedPoints(excess)}</div>
        <div class="meta">
            <div class="metric">
                extra misses when rushing
                {#if flagged}<span class="chip">flagged</span>{/if}
            </div>
            <div class="sub">
                {#if hasCI}
                    95% CI {excessCi}
                {:else}
                    fast vs slower error gap
                {/if}
            </div>
        </div>
    </div>

    {#if overall}
        <div class="rows">
            <div class="row">
                <span class="lab">fast</span>
                <Bar value={overall.fast_error_rate ?? 0} {status} height={9} />
                <span class="val">{pct(overall.fast_error_rate)}</span>
            </div>
            <div class="row">
                <span class="lab">slower</span>
                <Bar
                    value={overall.nonfast_error_rate ?? 0}
                    status="neutral"
                    height={9}
                />
                <span class="val">{pct(overall.nonfast_error_rate)}</span>
            </div>
        </div>
        <p class="rowcap">share of answers wrong</p>
    {/if}

    {#if flaggedNames.length}
        <div class="skills">
            <span class="skills-lab">watch on</span>
            {#each flaggedNames as name (name)}<span class="skill">{name}</span>{/each}
        </div>
    {/if}

    {#if overall}
        <p class="footer">
            {overall.n_fast ?? 0} of {overall.n_timed ?? 0} answers fast
        </p>
    {/if}
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
        color: color-mix(in srgb, var(--lsat-warn) 68%, var(--lsat-fg));
        font-size: 0.66rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .sub {
        color: var(--lsat-fg-subtle);
        font-size: 0.74rem;
        font-variant-numeric: tabular-nums;
    }

    /* fast vs slower error-rate comparison bars */
    .rows {
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }
    .row {
        display: grid;
        grid-template-columns: 3rem 1fr 2.6rem;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.8rem;
        font-variant-numeric: tabular-nums;
    }
    .lab {
        color: var(--lsat-fg-subtle);
        font-size: 0.74rem;
    }
    .val {
        text-align: right;
        font-weight: 650;
    }
    .rowcap {
        margin: 0.1rem 0 0;
        font-size: 0.68rem;
        color: var(--lsat-fg-subtle);
    }

    /* flagged-skill chips */
    .skills {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.3rem;
    }
    .skills-lab {
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--lsat-fg-subtle);
    }
    .skill {
        padding: 0.1rem 0.5rem;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-warn-soft);
        color: color-mix(in srgb, var(--lsat-warn) 68%, var(--lsat-fg));
        font-size: 0.72rem;
        font-weight: 600;
    }

    .footer {
        margin: 0.1rem 0 0;
        font-size: 0.74rem;
        color: var(--lsat-fg-subtle);
        font-variant-numeric: tabular-nums;
    }
    /* honesty framing: a gentle diagnostic, never a punishment. */
    .note {
        margin: 0.1rem 0 0;
        font-size: 0.72rem;
        line-height: 1.4;
        color: var(--lsat-fg-faint);
    }
</style>
