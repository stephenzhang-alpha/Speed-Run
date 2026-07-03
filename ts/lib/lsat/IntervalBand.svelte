<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

The "PROVEN" score primitive: a scale with a point tick + a filled CONFIDENCE
INTERVAL span (never a bare point estimate). When the score has not earned its
evidence it renders a HATCHED track with an "earning evidence" progress meter and
the unlock reason — abstention as a countable, proximal goal, not a broken blank.

When `available`, the earned CI span "inks in" (the gradient = proven) via a
one-shot clip-path reveal (reduced-motion: instant). `widened` renders the
readiness band-widening under measured overconfidence as geometry.
-->
<script lang="ts">
    import { onMount } from "svelte";

    export let available: boolean;
    export let min: number;
    export let max: number;
    export let point: number | null = null;
    export let low: number | null = null;
    export let high: number | null = null;
    export let unit = "";
    // abstain state
    export let progress: number | null = null; // 0..1 toward the evidence floor
    export let earnedNote = ""; // e.g. "6 of ~12 confidence-rated answers"
    export let unlockLabel = ""; // e.g. "unlocks Calibration"
    export let widened = false; // readiness band widened by overconfidence

    const clampPct = (v: number): number =>
        Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100));

    $: loPct = low != null ? clampPct(low) : 0;
    $: hiPct = high != null ? clampPct(high) : 0;
    $: ptPct = point != null ? clampPct(point) : 0;
    $: spanPct = Math.max(hiPct - loPct, 1.5);
    $: progPct = progress != null ? Math.max(0, Math.min(100, progress * 100)) : 0;

    // one-shot ink-in on mount (only when earned)
    let inked = false;
    onMount(() => {
        if (available) {
            requestAnimationFrame(() => (inked = true));
        }
    });
</script>

{#if available}
    <div class="band earned" class:inked class:widened>
        <div class="scale" role="img" aria-label={`${point}${unit}, interval ${low} to ${high}`}>
            <div class="track"></div>
            <div class="ci" style="left:{loPct}%;width:{spanPct}%"></div>
            {#if widened}
                <div class="widen-cap" style="left:{loPct}%;width:{spanPct}%" aria-hidden="true"></div>
            {/if}
            <div class="tick" style="left:{ptPct}%"></div>
        </div>
        <div class="ends"><span>{min}{unit}</span><span>{max}{unit}</span></div>
        {#if widened}
            <p class="widen-note">Band widened — your confidence runs ahead of your accuracy.</p>
        {/if}
    </div>
{:else}
    <div class="band abstain">
        <div class="scale">
            <div class="track hatched"></div>
            {#if progress != null}
                <div class="progress" style="width:{progPct}%"></div>
            {/if}
        </div>
        {#if earnedNote}
            <p class="meter-cap">
                <span class="ev">{earnedNote}</span>
                {#if unlockLabel}<span class="arrow" aria-hidden="true">→</span> {unlockLabel}{/if}
            </p>
        {/if}
    </div>
{/if}

<style lang="scss">
    .band {
        margin-top: 0.5rem;
    }
    .scale {
        position: relative;
        height: 12px;
    }
    .track {
        position: absolute;
        inset: 4px 0;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-inset);
        box-shadow: var(--lsat-elev-evidence);
    }
    .track.hatched {
        background: var(--lsat-hatch), var(--lsat-inset);
    }
    /* The earned confidence interval — the gradient means PROVEN. */
    .ci {
        position: absolute;
        top: 3px;
        height: 6px;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-proven);
        /* ink-in: revealed left→right once mounted */
        clip-path: inset(0 100% 0 0);
        transition: clip-path 620ms var(--lsat-ease);
    }
    .inked .ci {
        clip-path: inset(0 0 0 0);
    }
    /* the point estimate: a crisp high-contrast tick straddling the track */
    .tick {
        position: absolute;
        top: 0;
        width: 2px;
        height: 12px;
        margin-left: -1px;
        border-radius: 1px;
        background: var(--lsat-fg);
    }
    /* overconfidence widening: faint outline bracket around the CI */
    .widen-cap {
        position: absolute;
        top: 0;
        height: 12px;
        border: 1px dashed color-mix(in srgb, var(--lsat-warn) 55%, transparent);
        border-radius: 3px;
        pointer-events: none;
    }
    .ends {
        display: flex;
        justify-content: space-between;
        margin-top: 0.3rem;
        font-family: var(--lsat-mono);
        font-size: 0.68rem;
        font-variant-numeric: tabular-nums slashed-zero;
        color: var(--lsat-fg-faint);
    }
    /* abstain: the progress-to-unlock meter */
    .progress {
        position: absolute;
        top: 3px;
        left: 0;
        height: 6px;
        border-radius: var(--lsat-radius-pill);
        background: color-mix(in srgb, var(--lsat-accent) 45%, var(--lsat-inset));
        transition: width 620ms var(--lsat-ease);
    }
    .meter-cap {
        margin: 0.45rem 0 0;
        font-size: 0.74rem;
        line-height: 1.4;
        color: var(--lsat-fg-subtle);
    }
    .meter-cap .ev {
        font-family: var(--lsat-mono);
        font-variant-numeric: tabular-nums slashed-zero;
        color: var(--lsat-fg);
    }
    .meter-cap .arrow {
        color: var(--lsat-accent);
        font-weight: 700;
    }
    .widen-note {
        margin: 0.4rem 0 0;
        font-size: 0.72rem;
        color: color-mix(in srgb, var(--lsat-warn) 72%, var(--lsat-fg));
    }

    @media (prefers-reduced-motion: reduce) {
        .ci {
            transition: none;
            clip-path: inset(0 0 0 0);
        }
        .progress {
            transition: none;
        }
    }
</style>
