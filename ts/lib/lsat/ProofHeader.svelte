<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

The PROOF HEADER — the learner's own facts as premises, a turnstile ⊢, and an
honest claim. Shared by the desktop dashboard route AND the mobile Progress tab
(rendered inside DashboardView) so the "PROVEN" identity is identical on Mac and
Android. Honest even when abstaining (0 is shown, not hidden).
-->
<script lang="ts">
    // The raw dashboard JSON (typed loosely — every field is guarded).
    export let dashboard: {
        exam?: string;
        scores?: { performance?: { topics?: { n_events?: number }[] } };
        exam_schedule?: { available?: boolean; days_until_exam?: number | null };
    } = {};

    $: gradedItems = (dashboard?.scores?.performance?.topics ?? []).reduce(
        (s, t) => s + (t?.n_events ?? 0),
        0,
    );
    $: exam = dashboard?.exam_schedule;
    $: premises = [
        `${gradedItems} item${gradedItems === 1 ? "" : "s"} graded`,
        exam?.available && exam?.days_until_exam != null
            ? `${exam.days_until_exam} days to exam`
            : "LSAT · scored 120–180",
    ];
    $: claim =
        gradedItems > 0
            ? "Three scores you can trust — and the one thing to do next."
            : "Log a few answers — each score appears the moment its evidence is earned.";
</script>

<header class="proof-hero">
    <svg class="watermark" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M8 4 V20 M8 12 H18" />
    </svg>
    <p class="kicker">Anki for LSAT</p>
    <div class="proof">
        <ul class="premises">
            {#each premises as p (p)}<li>{p}</li>{/each}
        </ul>
        <span class="turnstile" aria-hidden="true">
            <svg viewBox="0 0 24 24"><path d="M8 4 V20 M8 12 H18" /></svg>
        </span>
        <p class="claim">{claim}</p>
    </div>
    <p class="honesty">We only show a number when the evidence earns it.</p>
</header>

<style lang="scss">
    .proof-hero {
        position: relative;
        isolation: isolate;
        overflow: hidden;
        margin-bottom: 1.6rem;
        padding: clamp(1.3rem, 1rem + 2.4vw, 2.2rem);
        border-radius: var(--lsat-radius);
        background: var(--lsat-surface);
        box-shadow: var(--lsat-elev-evidence);
        animation: hero-in 480ms var(--lsat-ease) both;
    }
    .watermark {
        position: absolute;
        z-index: -1;
        top: 50%;
        right: -2%;
        transform: translateY(-50%);
        width: clamp(110px, 22vw, 200px);
        height: clamp(110px, 22vw, 200px);
        fill: none;
        stroke: var(--lsat-fg);
        stroke-width: 1.4;
        stroke-linecap: round;
        opacity: 0.04;
    }
    .kicker {
        margin: 0 0 0.9rem;
        font-family: var(--lsat-mono);
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--lsat-fg-faint);
    }
    .proof {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.7rem 0.9rem;
    }
    .premises {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
    }
    .premises li {
        font-family: var(--lsat-mono);
        font-size: 0.82rem;
        font-variant-numeric: tabular-nums slashed-zero;
        color: var(--lsat-fg-subtle);
        padding: 0.18rem 0.6rem;
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-inset);
        width: fit-content;
    }
    .turnstile svg {
        width: 34px;
        height: 34px;
        fill: none;
        stroke: var(--lsat-accent);
        stroke-width: 2;
        stroke-linecap: round;
    }
    .claim {
        flex: 1 1 16rem;
        margin: 0;
        font-size: clamp(1.15rem, 0.9rem + 1.4vw, 1.7rem);
        font-weight: 700;
        line-height: 1.18;
        letter-spacing: -0.02em;
        color: var(--lsat-fg);
    }
    .honesty {
        margin: 1rem 0 0;
        font-family: var(--lsat-mono);
        font-size: 0.72rem;
        color: var(--lsat-fg-faint);
    }

    @keyframes hero-in {
        from {
            opacity: 0;
            transform: translateY(8px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    @media (prefers-reduced-motion: reduce) {
        .proof-hero {
            animation: none;
        }
    }
</style>
