<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

First-Instinct Ledger (DECISION-round4 #17): the learner's OWN answer-change
tally on timed sections -- wrong->right vs right->wrong -- with a bootstrap 95%
CI. It reports a direction only when the CI excludes 0; otherwise it abstains and
says exactly that, rather than parrot the folk "never change" rule or the
population ~2:1 base rate (applying either to an individual is the ecological
fallacy). A DIAGNOSTIC, never an always/never prescription and never a
percentile/score.
-->
<script lang="ts">
    import InsightCard from "./InsightCard.svelte";
    import type { AnswerChangeLedger, Status } from "./types";

    export let panel: AnswerChangeLedger = {};

    // changing_helps_you -> good, changing_costs_you -> warn, abstain -> neutral.
    function statusOf(direction: string | undefined): Status {
        if (direction === "changing_helps_you") {
            return "good";
        }
        if (direction === "changing_costs_you") {
            return "warn";
        }
        return "neutral";
    }

    $: status = statusOf(panel.direction);
    $: wr = panel.wrong_to_right ?? 0;
    $: rw = panel.right_to_wrong ?? 0;
</script>

<InsightCard
    title="First-instinct ledger"
    subtitle="Should you change answers?"
    {status}
    available={!!panel.available}
    reason={panel.reason ?? ""}
    emptyHint="Take a timed section to build your answer-change record."
>
    {#if panel.headline}<p class="headline">{panel.headline}</p>{/if}
    <div class="split">
        <div class="count s-good">
            <span class="n">{wr}</span>
            <span class="lab">wrong &rarr; right</span>
        </div>
        <div class="count s-warn">
            <span class="n">{rw}</span>
            <span class="lab">right &rarr; wrong</span>
        </div>
    </div>
    {#if panel.framing}<p class="framing">{panel.framing}</p>{/if}
</InsightCard>

<style lang="scss">
    .headline {
        margin: 0;
        font-size: 0.9rem;
        line-height: 1.45;
        color: var(--lsat-fg);
    }
    /* The two directional counts, side by side -- your own tally, not a rule. */
    .split {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.5rem;
    }
    .count {
        display: flex;
        flex-direction: column;
        gap: 0.1rem;
        padding: 0.55rem 0.7rem;
        border-radius: var(--lsat-radius-sm);
        border: 1px solid var(--lsat-border-subtle);
        background: var(--lsat-inset);
    }
    .count.s-good {
        background: var(--lsat-good-soft);
    }
    .count.s-warn {
        background: var(--lsat-warn-soft);
    }
    .n {
        font-size: 1.5rem;
        font-weight: 750;
        line-height: 1;
        font-variant-numeric: tabular-nums;
    }
    .count.s-good .n {
        color: var(--lsat-good);
    }
    .count.s-warn .n {
        color: var(--lsat-warn);
    }
    .lab {
        font-size: 0.72rem;
        color: var(--lsat-fg-subtle);
    }
    .framing {
        margin: 0.1rem 0 0;
        font-size: 0.7rem;
        line-height: 1.4;
        color: var(--lsat-fg-faint);
    }
</style>
