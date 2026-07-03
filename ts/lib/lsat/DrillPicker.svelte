<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

The mobile Logic "Drill Launcher": a scannable, grouped list of picker cards that
replaces the cramped five-segment control. Each card shows an icon, a name, a
one-line blurb, and an optional recency hint; tapping one dispatches `select`
with its id. Recency is optional -- with the default empty accessor the pure
picker still renders cleanly.
-->
<script lang="ts">
    import { createEventDispatcher } from "svelte";

    type Drill = { id: string; name: string; blurb: string; group: string; icon: string };

    export let drills: Drill[];
    export let recency: (id: string) => { label: string; tone: string } = () => ({
        label: "",
        tone: "",
    });

    const dispatch = createEventDispatcher<{ select: string }>();

    // Fold the flat list into [groupLabel, drills][] preserving list order, so the
    // sections render in the taxonomy order the parent supplies.
    $: groups = drills.reduce<[string, Drill[]][]>((acc, d) => {
        const last = acc[acc.length - 1];
        if (last && last[0] === d.group) {
            last[1].push(d);
        } else {
            acc.push([d.group, [d]]);
        }
        return acc;
    }, []);
</script>

<nav aria-label="Logic drills">
    <h2 class="lead">Pick a drill</h2>
    {#each groups as [label, items], i (label)}
        {@const headingId = `drill-group-${i}`}
        <section aria-labelledby={headingId}>
            <h3 class="group-label" id={headingId}>{label}</h3>
            {#each items as d (d.id)}
                {@const rec = recency(d.id)}
                <button
                    class="drill"
                    type="button"
                    data-id={d.id}
                    aria-label={`${d.name}. ${d.blurb}${rec.label ? `. ${rec.label}` : ""}`}
                    on:click={() => dispatch("select", d.id)}
                >
                    <span class="chip" aria-hidden="true">
                        <svg viewBox="0 0 24 24"><path d={d.icon} /></svg>
                    </span>
                    <span class="txt">
                        <span class="name">{d.name}</span>
                        <span class="blurb">{d.blurb}</span>
                    </span>
                    {#if rec.label}
                        <span class="rec rec--{rec.tone}" aria-hidden="true">
                            <span class="dot"></span>{rec.label}
                        </span>
                    {/if}
                    <span class="chev" aria-hidden="true">
                        <svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6" /></svg>
                    </span>
                </button>
            {/each}
        </section>
    {/each}
</nav>

<style lang="scss">
    nav {
        display: flex;
        flex-direction: column;
    }
    .lead {
        margin: 0 0 0.55rem;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--lsat-fg-subtle);
    }
    section {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    section + section {
        margin-top: 0.85rem;
    }
    .group-label {
        margin: 0 0 0.1rem;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--lsat-fg-subtle);
    }
    .drill {
        display: grid;
        grid-template-columns: auto 1fr auto auto;
        align-items: center;
        gap: 0.75rem;
        width: 100%;
        min-height: 64px;
        padding: 0.7rem 0.8rem;
        border: 1px solid var(--lsat-border-subtle);
        border-radius: var(--lsat-radius);
        background: var(--lsat-surface);
        box-shadow: var(--lsat-shadow);
        color: var(--lsat-fg);
        font: inherit;
        text-align: left;
        cursor: pointer;
        transition:
            box-shadow var(--lsat-transition) var(--lsat-ease),
            border-color var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease);
    }
    .drill:hover {
        box-shadow: var(--lsat-shadow-lift);
        border-color: color-mix(in srgb, var(--lsat-accent) 40%, var(--lsat-border-subtle));
        transform: translateY(-1px);
    }
    .drill:active {
        transform: scale(0.985);
    }
    .drill:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }
    .chip {
        display: grid;
        place-items: center;
        width: 40px;
        height: 40px;
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-accent-soft);
    }
    .chip svg {
        width: 24px;
        height: 24px;
        fill: none;
        stroke: var(--lsat-accent);
        stroke-width: 2;
        stroke-linecap: round;
        stroke-linejoin: round;
    }
    .txt {
        display: flex;
        flex-direction: column;
        gap: 0.12rem;
        min-width: 0;
    }
    .name {
        font-size: 0.95rem;
        font-weight: 650;
        color: var(--lsat-fg);
    }
    .blurb {
        font-size: 0.78rem;
        line-height: 1.3;
        color: var(--lsat-fg-subtle);
    }
    /* Recency lives only in the dot's colour; the label text stays subtle (AA), so
     * tone never leaks into hard-to-read coloured text. */
    .rec {
        grid-column: 3;
        display: inline-flex;
        align-items: center;
        gap: 0.32rem;
        font-size: 0.72rem;
        font-weight: 600;
        white-space: nowrap;
        color: var(--lsat-fg-subtle);
    }
    .dot {
        width: 7px;
        height: 7px;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-fg-subtle);
    }
    .rec--new .dot {
        background: var(--lsat-accent);
    }
    .rec--good .dot {
        background: var(--lsat-good);
    }
    .rec--neutral .dot {
        background: var(--lsat-fg-subtle);
    }
    .rec--warn .dot {
        background: var(--lsat-warn);
    }
    .chev {
        grid-column: 4;
        display: grid;
        place-items: center;
        color: var(--lsat-fg-faint);
    }
    .chev svg {
        width: 20px;
        height: 20px;
        fill: none;
        stroke: currentColor;
        stroke-width: 2;
        stroke-linecap: round;
        stroke-linejoin: round;
    }

    @media (prefers-reduced-motion: reduce) {
        .drill {
            transition: none;
        }
        .drill:hover,
        .drill:active {
            transform: none;
        }
    }
</style>
