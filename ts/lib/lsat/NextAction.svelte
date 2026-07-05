<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

The "DO NEXT" primacy band — the first interactive object on the dashboard.
Learning science: leading with self-level scores can HARM performance (Feedback
Intervention Theory, Kluger & DeNisi 1996); lead instead with feed-forward — the
single highest-yield next action + its reason (Hattie & Timperley 2007) — with one
strong default (Hick's Law) while preserving autonomy via a quiet "or choose"
(Self-Determination Theory). The one place the gradient is licensed: this is the
earned, primary action.
-->
<script lang="ts">
    export let label: string; // the recommended action, e.g. "Study Necessary Assumption"
    export let reason = ""; // why — e.g. "your weakest high-yield type"
    export let count = ""; // e.g. "12 due" / "3 to re-prove"
    export let kind: "retest" | "study" | "start" = "study";
    export let href = "/lsat-mobile";

    const EYEBROW: Record<string, string> = {
        retest: "Highest-value fix",
        study: "Do next",
        start: "Start here",
    };
</script>

<a class="next-action" {href} data-kind={kind}>
    <span class="rail" aria-hidden="true"></span>
    <span class="mark" aria-hidden="true">
        <svg viewBox="0 0 24 24"><path d="M8 5 V19 M8 12 H17" /></svg>
    </span>
    <span class="body">
        <span class="eyebrow">{EYEBROW[kind]}</span>
        <span class="label">{label}</span>
        {#if reason}<span class="reason">{reason}</span>{/if}
    </span>
    <span class="go">
        {#if count}<span class="count">{count}</span>{/if}
        <span class="cta">
            Start
            <span class="arrow" aria-hidden="true">→</span>
        </span>
    </span>
</a>

<style lang="scss">
    .next-action {
        position: relative;
        display: flex;
        align-items: center;
        gap: 0.9rem;
        padding: 1rem 1.1rem 1rem 1.35rem;
        border-radius: var(--lsat-radius);
        background: var(--lsat-surface);
        border: 1px solid var(--lsat-border-subtle);
        box-shadow: var(--lsat-shadow); /* actionable: the one resting lift */
        color: var(--lsat-fg);
        text-decoration: none;
        overflow: hidden;
        transition:
            box-shadow var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease);
    }
    .next-action:hover {
        box-shadow: var(--lsat-glow);
        transform: translateY(-1px);
    }
    .next-action:active {
        transform: translateY(0) scale(0.995);
    }
    .next-action:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }
    /* the proof-rail gutter, drawn in on mount */
    .rail {
        position: absolute;
        inset: 0 auto 0 0;
        width: var(--lsat-rail-w);
        background: var(--lsat-rail);
        transform: scaleY(0);
        transform-origin: top;
        animation: rail-in 420ms var(--lsat-ease) 80ms forwards;
    }
    .mark {
        flex: 0 0 auto;
        display: grid;
        place-items: center;
        width: 38px;
        height: 38px;
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-accent-soft);
    }
    .mark svg {
        width: 20px;
        height: 20px;
        fill: none;
        stroke: var(--lsat-accent);
        stroke-width: 2;
        stroke-linecap: round;
    }
    .body {
        display: flex;
        flex-direction: column;
        gap: 0.12rem;
        min-width: 0;
        flex: 1 1 auto;
    }
    .eyebrow {
        font-family: var(--lsat-mono);
        font-size: 0.66rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--lsat-fg-faint);
    }
    .label {
        font-size: 1.12rem;
        font-weight: 700;
        line-height: 1.25;
        letter-spacing: -0.01em;
    }
    .reason {
        font-size: 0.85rem;
        color: var(--lsat-fg-subtle);
        line-height: 1.35;
    }
    .go {
        flex: 0 0 auto;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 0.35rem;
    }
    .count {
        font-family: var(--lsat-mono);
        font-size: 0.72rem;
        font-variant-numeric: tabular-nums slashed-zero;
        color: var(--lsat-fg-subtle);
    }
    .cta {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.5rem 1.05rem;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-proven); /* earned/primary — gradient licensed here */
        color: var(--lsat-ink-on-accent);
        font-weight: 650;
        font-size: 0.9rem;
        white-space: nowrap;
    }
    .arrow {
        transition: transform var(--lsat-transition) var(--lsat-ease);
    }
    .next-action:hover .arrow {
        transform: translateX(3px);
    }

    @keyframes rail-in {
        to {
            transform: scaleY(1);
        }
    }
    @media (prefers-reduced-motion: reduce) {
        .next-action,
        .arrow {
            transition: none;
        }
        .next-action:hover {
            transform: none;
        }
        .rail {
            animation: none;
            transform: scaleY(1);
        }
    }
</style>
