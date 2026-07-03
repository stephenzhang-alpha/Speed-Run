<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

The honest "tiered assurance" badge, shared across every AI-touched / scored
surface (the Proof Theater, Worked Example, Evil Twin, Misconception panel, and
the ScoreCard abstain state). Three tiers, distinguished by GEOMETRY + WORD +
colour (never colour alone):

  proven   — a decision procedure re-derived every step (the turnstile mark)
  grounded — no procedure, but tied to a documented source/catalog span
  abstain  — not enough evidence yet (hatched; an earnable goal, not "broken")

One stroke-SVG icon language (no text glyphs), AA-darkened label text.
-->
<script lang="ts">
    export let tier: "proven" | "grounded" | "abstain" = "proven";
    export let label = "";

    const DEFAULT_LABEL: Record<string, string> = {
        proven: "Proven",
        grounded: "Grounded",
        abstain: "Not yet proven",
    };
    const TITLE: Record<string, string> = {
        proven: "A decision procedure re-derived every step — provably correct.",
        grounded: "No decision procedure, but tied to a documented source span.",
        abstain: "Not enough evidence yet — this unlocks as you study.",
    };
    $: text = label || DEFAULT_LABEL[tier];
</script>

<span class="pb {tier}" title={TITLE[tier]}>
    <svg class="mk" viewBox="0 0 24 24" aria-hidden="true">
        {#if tier === "proven"}
            <!-- turnstile ⊢ : premises entail the conclusion -->
            <path d="M8 5 V19 M8 12 H17" />
        {:else if tier === "grounded"}
            <!-- anchored to a source: a tick citing a baseline -->
            <path d="M12 5 V15 M8 11 l4 4 4-4 M6 19 H18" />
        {:else}
            <!-- unproven: a hatched square -->
            <rect x="5.5" y="5.5" width="13" height="13" rx="2" />
            <path d="M7 15 L15 7 M9 17 L17 9" class="hatch" />
        {/if}
    </svg>
    <span class="lbl">{text}</span>
</span>

<style lang="scss">
    .pb {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.2rem 0.6rem 0.2rem 0.5rem;
        border-radius: var(--lsat-radius-pill);
        border: 1px solid;
        font-family: var(--lsat-mono);
        font-size: 0.7rem;
        font-weight: 650;
        letter-spacing: 0.02em;
        white-space: nowrap;
        line-height: 1;
    }
    .mk {
        width: 13px;
        height: 13px;
        fill: none;
        stroke-width: 2;
        stroke-linecap: round;
        stroke-linejoin: round;
        flex: 0 0 auto;
    }
    .mk .hatch {
        stroke-width: 1.4;
        opacity: 0.7;
    }

    /* proven — earned green; text darkened toward fg for AA on soft fill */
    .proven {
        color: color-mix(in srgb, var(--lsat-good) 72%, var(--lsat-fg));
        background: var(--lsat-good-soft);
        border-color: color-mix(in srgb, var(--lsat-good) 40%, transparent);
    }
    .proven .mk {
        stroke: var(--lsat-good);
    }
    /* grounded — accent anchor */
    .grounded {
        color: color-mix(in srgb, var(--lsat-accent) 72%, var(--lsat-fg));
        background: var(--lsat-accent-soft);
        border-color: color-mix(in srgb, var(--lsat-accent) 40%, transparent);
    }
    .grounded .mk {
        stroke: var(--lsat-accent);
    }
    /* abstain — faint, hatched: intentional, not broken */
    .abstain {
        color: var(--lsat-fg-subtle);
        background: var(--lsat-hatch);
        border-color: var(--lsat-border-subtle);
    }
    .abstain .mk {
        stroke: var(--lsat-fg-faint);
    }
</style>
