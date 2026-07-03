<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

The Mastery-Growth panel: a self-referential progress surface. For every skill
with a directional readout (the CI cleared 0) we show the accuracy change in
percentage points, its 95% CI in the same unit, and the concrete next step.
This is a comparison of you-now against you-earlier -- never a rank, a
percentile, a scaled score, or a comparison to other people. Skills still
gathering evidence abstain into a single quiet line rather than reading as
failures.
-->
<script lang="ts">
    import type { GrowthSkill, MasteryGrowth, Status } from "./types";
    import { signedPoints, statusColor, statusSoft } from "./util";

    export let growth: MasteryGrowth;

    // "improved" celebrates (good/green); "slipped" flags gently (warn/amber),
    // never as a hard failure on a progress surface.
    function statusOf(s: GrowthSkill): Status {
        return s.status === "improved" ? "good" : "warn";
    }

    // A signed integer of percentage points, for the CI bounds (no unit, so we
    // can append a single "pts" to the range and read "+5 to +23 pts").
    function pts(x: number): string {
        const p = Math.round(x * 100);
        return `${p > 0 ? "+" : ""}${p}`;
    }

    $: shown = growth.skills.filter((s) => s.available);
    // Abstaining skills are surfaced as one calm count, not per-row "failures".
    $: gathering = growth.skills.length - shown.length;
</script>

<div class="growth">
    {#if growth.headline}<p class="headline">{growth.headline}</p>{/if}

    <div class="grid">
        {#each shown as s (s.node_id)}
            {@const st = statusOf(s)}
            <div class="skill" style="--c:{statusColor(st)};--bg:{statusSoft(st)}">
                <div class="skill-top">
                    <span class="label">{s.label}</span>
                    <span class="chip">
                        <span class="arr" aria-hidden="true"
                            >{s.status === "improved" ? "↑" : "↓"}</span
                        >{s.status}
                    </span>
                </div>
                <div class="delta">{signedPoints(s.delta)}</div>
                {#if s.ci_low != null && s.ci_high != null}
                    <p class="ci">
                        95% CI {pts(s.ci_low)} to {pts(s.ci_high)} pts &middot;
                        {s.n_early}→{s.n_recent} answers
                    </p>
                {/if}
                {#if s.next_step}
                    <p class="next">
                        <span class="next-arr" aria-hidden="true">→</span>{s.next_step}
                    </p>
                {/if}
            </div>
        {/each}
    </div>

    {#if gathering > 0}
        <p class="gathering">
            {gathering} more skill{gathering === 1 ? "" : "s"} still gathering evidence &mdash; keep
            going.
        </p>
    {/if}
</div>

<style lang="scss">
    .growth {
        display: flex;
        flex-direction: column;
        gap: var(--lsat-gap);
    }
    .headline {
        margin: 0;
        font-size: 0.9rem;
        font-weight: 650;
        color: var(--lsat-fg);
        font-variant-numeric: tabular-nums;
    }

    /* A responsive band of skill cards; collapses to one column on phones,
     * matching the score/insight grids. */
    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: var(--lsat-gap);
    }

    /* Surface card with a status-tinted left accent -- a sibling of the .plan
     * strip and the score cards (surface + subtle border + soft shadow). */
    .skill {
        position: relative;
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
        padding: var(--lsat-pad);
        background: var(--lsat-surface);
        border: 1px solid var(--lsat-border-subtle);
        border-left: 3px solid var(--c);
        border-radius: var(--lsat-radius);
        box-shadow: var(--lsat-shadow);
        overflow: hidden;
        transition:
            box-shadow var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease);
    }
    .skill:hover {
        box-shadow: var(--lsat-shadow-lift);
        transform: translateY(-1px);
    }
    .skill-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
    }
    .label {
        font-size: 0.95rem;
        font-weight: 650;
        letter-spacing: 0.01em;
        text-transform: capitalize;
        min-width: 0;
    }
    .chip {
        flex: none;
        display: inline-flex;
        align-items: center;
        gap: 0.15rem;
        padding: 0.08rem 0.45rem;
        border-radius: var(--lsat-radius-pill);
        background: var(--bg);
        color: var(--c);
        font-size: 0.66rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .arr {
        font-size: 0.8em;
        line-height: 1;
    }
    .delta {
        font-size: 1.8rem;
        font-weight: 750;
        line-height: 1;
        font-variant-numeric: tabular-nums;
        color: var(--c);
    }
    .ci {
        margin: 0;
        font-size: 0.74rem;
        color: var(--lsat-fg-subtle);
        font-variant-numeric: tabular-nums;
    }
    .next {
        display: flex;
        gap: 0.35rem;
        margin: 0.1rem 0 0;
        font-size: 0.82rem;
        line-height: 1.4;
        color: var(--lsat-fg);
    }
    .next-arr {
        flex: none;
        font-weight: 700;
        color: var(--c);
    }
    .gathering {
        margin: 0;
        font-size: 0.78rem;
        color: var(--lsat-fg-subtle);
        font-variant-numeric: tabular-nums;
    }

    @media (prefers-reduced-motion: reduce) {
        .skill {
            transition: none;
        }
        .skill:hover {
            transform: none;
        }
    }
</style>
