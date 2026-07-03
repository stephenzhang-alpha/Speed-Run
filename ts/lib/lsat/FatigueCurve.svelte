<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Fatigue Curve (DECISION-round2 #10): accuracy by cumulative minutes-on-task within
a study session (sessions inferred from event timestamps). A descriptive stamina
diagnostic -- it does not itself raise scores, and abstains below the evidence
floor. Negative slope = accuracy decays as a session wears on.
-->
<script lang="ts">
    import Bar from "./Bar.svelte";
    import InsightCard from "./InsightCard.svelte";
    import type { FatiguePanel, Status } from "./types";
    import { msToSeconds, pct, signed } from "./util";

    export let panel: FatiguePanel = {};

    $: slope = panel.accuracy_slope_per_30min ?? null;
    // A decaying curve is the actionable "watch your stamina" case.
    function slopeStatus(s: number | null): Status {
        if (s == null) {
            return "neutral";
        }
        return s < -0.03 ? "warn" : "good";
    }
    function accStatus(a: number): Status {
        if (a >= 0.7) {
            return "good";
        }
        return a >= 0.5 ? "warn" : "bad";
    }
    $: status = slopeStatus(slope);
</script>

<InsightCard
    title="Stamina"
    subtitle="Accuracy vs time on task"
    {status}
    available={!!panel.available}
    reason={panel.reason ?? ""}
    emptyHint="Study a few timed sessions to chart how accuracy holds up over time."
>
    <div class="rows">
        {#each panel.bins ?? [] as b (b.label)}
            <div class="row">
                <span class="lab">{b.label}</span>
                <Bar value={b.accuracy} status={accStatus(b.accuracy)} height={9} />
                <span class="val">{pct(b.accuracy)}</span>
                <span class="rt">{msToSeconds(b.median_response_ms)}</span>
            </div>
        {/each}
    </div>
    {#if slope != null}
        <p class="slope s-{status}">
            {signed(slope)} accuracy / 30 min on task
        </p>
    {/if}
    {#if panel.n_sessions}
        <p class="footer">across {panel.n_sessions} inferred session(s)</p>
    {/if}
</InsightCard>

<style lang="scss">
    .rows {
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }
    .row {
        display: grid;
        grid-template-columns: 4.6rem 1fr 2.6rem 2.6rem;
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
    .rt {
        text-align: right;
        color: var(--lsat-fg-faint);
        font-size: 0.72rem;
    }
    .slope {
        margin: 0.55rem 0 0;
        font-size: 0.86rem;
        font-weight: 650;
        font-variant-numeric: tabular-nums;
    }
    .slope.s-warn {
        color: var(--lsat-warn);
    }
    .slope.s-good {
        color: var(--lsat-good);
    }
    .footer {
        margin: 0.15rem 0 0;
        font-size: 0.74rem;
        color: var(--lsat-fg-subtle);
    }
</style>
