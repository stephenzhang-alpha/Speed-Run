<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import InsightCard from "./InsightCard.svelte";
    import type { FluencyPanel, Status } from "./types";
    import { statusColor, statusSoft } from "./util";

    export let panel: FluencyPanel = {};

    $: counts = (() => {
        const c: Record<string, number> = { automatic: 0, effortful: 0, not_yet: 0 };
        for (const nd of Object.values(panel.nodes ?? {})) {
            const s = nd?.state;
            if (s && s in c) {
                c[s] += 1;
            }
        }
        return c;
    })();

    // The fluency ladder, read left-to-right: raw recall climbs toward automatic.
    $: rungs = [
        {
            key: "not_yet",
            label: "not yet",
            status: "neutral" as Status,
            count: counts.not_yet,
        },
        {
            key: "effortful",
            label: "effortful",
            status: "warn" as Status,
            count: counts.effortful,
        },
        {
            key: "automatic",
            label: "automatic",
            status: "good" as Status,
            count: counts.automatic,
        },
    ];
</script>

<InsightCard
    title="Fluency"
    subtitle="Accurate and fast?"
    status="neutral"
    available={!!panel.available}
    reason={panel.reason ?? ""}
    emptyHint="Answer more timed items to grade speed, not just accuracy."
>
    <div class="ladder">
        {#each rungs as rung, i (rung.key)}
            {#if i > 0}<span class="arrow" aria-hidden="true"></span>{/if}
            <div
                class="rung"
                style="--c:{statusColor(rung.status)};--bg:{statusSoft(rung.status)}"
            >
                <span class="n">{rung.count}</span>
                <span class="lbl">{rung.label}</span>
            </div>
        {/each}
    </div>
    <p class="note">
        Retire a skill only when it's accurate <em>and</em>
        fast.
    </p>
</InsightCard>

<style lang="scss">
    .ladder {
        display: flex;
        align-items: stretch;
        gap: 0.35rem;
    }
    .rung {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.15rem;
        padding: 0.5rem 0.3rem;
        border-radius: var(--lsat-radius-sm);
        background: var(--bg);
        box-shadow: inset 0 2px 0 var(--c);
    }
    .n {
        font-size: 1.35rem;
        line-height: 1;
        font-weight: 750;
        font-variant-numeric: tabular-nums;
        color: color-mix(in srgb, var(--c) 70%, var(--lsat-fg));
    }
    .lbl {
        font-size: 0.72rem;
        line-height: 1.15;
        text-align: center;
        color: var(--lsat-fg-subtle);
    }
    /* a recessive chevron carrying the "improves toward" direction */
    .arrow {
        flex: none;
        align-self: center;
        width: 0.5rem;
        height: 0.5rem;
        border-top: 2px solid var(--lsat-fg-faint);
        border-right: 2px solid var(--lsat-fg-faint);
        transform: rotate(45deg);
    }
    .note {
        margin: 0.1rem 0 0;
        font-size: 0.78rem;
        line-height: 1.4;
        color: var(--lsat-fg-subtle);
    }
</style>
