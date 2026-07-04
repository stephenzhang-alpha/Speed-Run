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
    <div class="brand">
        <span class="brandmark" aria-hidden="true">
            <svg viewBox="0 0 24 24"><path d="M8 4 V20 M8 12 H18" /></svg>
        </span>
        <span class="kicker">LSAT&nbsp;Prep</span>
    </div>
    <div class="proof">
        <ul class="premises">
            {#each premises as p (p)}<li>{p}</li>{/each}
        </ul>
        <span class="turnstile" aria-hidden="true">
            <svg viewBox="0 0 24 24"><path d="M8 4 V20 M8 12 H18" /></svg>
        </span>
        <p class="claim">{claim}</p>
    </div>
    <p class="honesty">
        <span class="dot" aria-hidden="true"></span>
        We only show a number when the evidence earns it.
    </p>
</header>

<style lang="scss">
    .proof-hero {
        position: relative;
        isolation: isolate;
        overflow: hidden;
        margin-bottom: 1.6rem;
        padding: clamp(1.4rem, 1rem + 2.6vw, 2.4rem);
        border-radius: var(--lsat-radius);
        /* a whisper of the brand accent in the top-right, over the surface -
         * presence without spending the "proven" gradient. */
        background:
            radial-gradient(130% 150% at 100% 0%, var(--lsat-accent-soft) 0%, transparent 55%),
            var(--lsat-surface);
        border: 1px solid var(--lsat-border-subtle);
        box-shadow: var(--lsat-shadow);
        animation: hero-in 480ms var(--lsat-ease) both;
    }
    .watermark {
        position: absolute;
        z-index: -1;
        top: 50%;
        right: -4%;
        transform: translateY(-50%);
        width: clamp(150px, 26vw, 260px);
        height: clamp(150px, 26vw, 260px);
        fill: none;
        stroke: var(--lsat-accent);
        stroke-width: 1.2;
        stroke-linecap: round;
        opacity: 0.08;
    }
    .brand {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-bottom: 1.2rem;
    }
    .brandmark {
        display: grid;
        place-items: center;
        width: 34px;
        height: 34px;
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-hero);
        box-shadow: var(--lsat-glow);
    }
    .brandmark svg {
        width: 20px;
        height: 20px;
        fill: none;
        stroke: var(--lsat-ink-on-accent);
        stroke-width: 1.8;
        stroke-linecap: round;
    }
    .kicker {
        font-weight: 750;
        font-size: 1.05rem;
        letter-spacing: -0.015em;
        color: var(--lsat-fg);
    }
    .proof {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.7rem 1rem;
    }
    .premises {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }
    .premises li {
        font-family: var(--lsat-mono);
        font-size: 0.8rem;
        font-variant-numeric: tabular-nums slashed-zero;
        color: var(--lsat-fg-subtle);
        padding: 0.28rem 0.7rem;
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-inset);
        border: 1px solid var(--lsat-border-subtle);
        width: fit-content;
    }
    .turnstile svg {
        width: 30px;
        height: 30px;
        fill: none;
        stroke: var(--lsat-accent);
        stroke-width: 2.2;
        stroke-linecap: round;
    }
    .claim {
        flex: 1 1 15rem;
        margin: 0;
        font-size: clamp(1.25rem, 1rem + 1.5vw, 1.85rem);
        font-weight: 750;
        line-height: 1.15;
        letter-spacing: -0.025em;
        color: var(--lsat-fg);
    }
    .honesty {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        margin: 1.2rem 0 0;
        font-family: var(--lsat-mono);
        font-size: 0.72rem;
        color: var(--lsat-fg-faint);
    }
    .honesty .dot {
        flex: 0 0 auto;
        width: 6px;
        height: 6px;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-good);
        box-shadow: 0 0 0 3px var(--lsat-good-soft);
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
