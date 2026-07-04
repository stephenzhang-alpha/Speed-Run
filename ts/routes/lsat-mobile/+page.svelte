<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

The mobile PWA shell: a sticky header, a scrollable body (Study or Progress),
and a bottom tab bar with safe-area insets. Reuses the same shared components as
the desktop dashboard and the same HTTP-backed study flow.
-->
<script lang="ts">
    import "$lib/lsat/theme.scss";

    import { onMount, tick } from "svelte";

    import AssumptionDrill from "$lib/lsat/AssumptionDrill.svelte";
    import ChainDrill from "$lib/lsat/ChainDrill.svelte";
    import ConditionalDrill from "$lib/lsat/ConditionalDrill.svelte";
    import DashboardView from "$lib/lsat/DashboardView.svelte";
    import DrillPicker from "$lib/lsat/DrillPicker.svelte";
    import EvilTwinDrill from "$lib/lsat/EvilTwinDrill.svelte";
    import { lastPracticed, markPracticed, recency } from "$lib/lsat/drillProgress";
    import { installPwaMeta } from "$lib/lsat/pwa";
    import QuantifierDrill from "$lib/lsat/QuantifierDrill.svelte";
    import StemPolarityDrill from "$lib/lsat/StemPolarityDrill.svelte";
    import StudyItem from "$lib/lsat/StudyItem.svelte";
    import WorkedExampleDrill from "$lib/lsat/WorkedExampleDrill.svelte";

    import type { PageData } from "./$types";

    export let data: PageData;

    type Tab = "study" | "logic" | "progress";
    let tab: Tab = "study";
    const MODE_LABEL: Record<Tab, string> = {
        study: "Practice",
        logic: "Logic",
        progress: "Progress",
    };

    // Logic tab: a scannable "Drill Launcher" (grouped picker cards) replaces the
    // old five-segment control. The picker lists these drills under three
    // taxonomy groups; selecting one mounts the matching drill. The `icon` paths
    // follow the same 24x24 stroke-SVG convention as the bottom `.tabs` icons.
    const LOGIC_DRILLS: {
        id: string;
        name: string;
        blurb: string;
        group: string;
        icon: string;
    }[] = [
        {
            id: "translate",
            name: "Translate",
            blurb: "Turn an if/then into its arrow + contrapositive",
            group: "CONDITIONALS",
            icon: "M5 12h11m0 0l-4-4m4 4l-4 4",
        },
        {
            id: "chain",
            name: "Chains",
            blurb: "Chain 3+ conditionals + their contrapositives",
            group: "CONDITIONALS",
            icon: "M4 12h4m0 0l-2-2m2 2l-2 2m4-2h4m0 0l-2-2m2 2l-2 2m4-2h2",
        },
        {
            id: "worked",
            name: "Worked example",
            blurb: "Finish an oracle-checked chain proof, step by step",
            group: "CONDITIONALS",
            icon: "M5 4h14M5 4v16M5 20h14M9 9h6m-6 4h6m-6 4h3",
        },
        {
            id: "twin",
            name: "Skill or luck?",
            blurb: "A one-edit twin that flips the answer — did you really get it?",
            group: "CONDITIONALS",
            icon: "M8 3a5 5 0 100 10A5 5 0 008 3zm8 8a5 5 0 100 10 5 5 0 000-10zM10 8h4m-2-2v4",
        },
        {
            id: "validity",
            name: "Validity",
            blurb: "Must / cannot / could be true?",
            group: "QUANTIFIERS",
            icon: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zm-3.5 9l2.5 2.5 4.5-5",
        },
        {
            id: "negation",
            name: "Negation",
            blurb: "What is the exact logical negation?",
            group: "QUANTIFIERS",
            icon: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM7 7l10 10",
        },
        {
            id: "stems",
            name: "Stem polarity",
            blurb: "Catch EXCEPT / LEAST / negated stems",
            group: "QUESTION TACTICS",
            icon: "M6 21V4m0 0h11l-2 4 2 4H6",
        },
        {
            id: "assumption",
            name: "Nec / Suf",
            blurb: "Sort an assumption: necessary / sufficient / both / neither",
            group: "QUESTION TACTICS",
            icon: "M9 8a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm6 0a5 5 0 1 0 0 10 5 5 0 0 0 0-10z",
        },
    ];
    // `null` shows the launcher; a drill id mounts that drill. Focus moves to the
    // back button on open and returns to the launching card on close.
    let openDrill: string | null = null;
    let backEl: HTMLButtonElement | undefined;

    // The header pill shows the open logic drill's name (or the tab's label).
    $: headerLabel =
        tab === "logic" && openDrill
            ? (LOGIC_DRILLS.find((d) => d.id === openDrill)?.name ?? MODE_LABEL.logic)
            : MODE_LABEL[tab];

    // Session mode (Feature 4): a blind/relaxed pass stamps its phase onto each
    // answer so the Gap Map / Choke Index / honest-mastery filter receive untimed
    // events -- without this control the mobile flow only ever logs "timed".
    type Phase = "timed" | "blind" | "relaxed";
    let studyPhase: Phase = "timed";
    const PHASES: [Phase, string][] = [
        ["timed", "Timed"],
        ["blind", "Blind"],
        ["relaxed", "Relaxed"],
    ];
    // Index of the active phase, used only to slide the segmented-control thumb.
    $: activeIndex = PHASES.findIndex(([p]) => p === studyPhase);

    // Opening a drill records it for the recency hint, mounts it, then moves focus
    // to the back button so keyboard/AT users land inside the drill.
    async function openLogicDrill(id: string): Promise<void> {
        markPracticed(id);
        openDrill = id;
        await tick();
        backEl?.focus();
    }

    // Closing returns to the launcher and restores focus to the card that opened it.
    async function closeLogicDrill(): Promise<void> {
        const id = openDrill;
        openDrill = null;
        await tick();
        (document.querySelector(`.drill[data-id="${id}"]`) as HTMLElement | null)?.focus();
    }

    onMount(() => installPwaMeta());
</script>

<svelte:head>
    <title>LSAT Prep</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
</svelte:head>

<div class="app">
    <header class="bar">
        <div class="bar-inner">
            <div class="identity">
                <span class="mark" aria-hidden="true">
                    <!-- the turnstile ⊢ : the "PROVEN" brand mark -->
                    <svg viewBox="0 0 24 24"><path d="M8 4 V20 M8 12 H18" /></svg>
                </span>
                <span class="brand">LSAT&nbsp;Prep</span>
            </div>
            <span class="mode">{headerLabel}</span>
        </div>
    </header>

    <main>
        {#if tab === "study"}
            <div
                class="phasebar"
                role="group"
                aria-label="Study mode"
                style="--idx:{activeIndex}; --n:{PHASES.length}"
            >
                <span class="thumb" aria-hidden="true"></span>
                {#each PHASES as [p, label] (p)}
                    <button
                        type="button"
                        class:active={studyPhase === p}
                        on:click={() => (studyPhase = p)}>{label}</button
                    >
                {/each}
            </div>
            {#if studyPhase !== "timed"}
                <p class="phase-hint">
                    Untimed pass &mdash; answers refine your Gap Map without inflating mastery.
                </p>
            {/if}
            <a class="section-cta" href="/lsat-section-runner">
                Start a timed section
                <span class="arrow" aria-hidden="true">&rarr;</span>
            </a>
            <StudyItem phase={studyPhase} />
        {:else if tab === "logic"}
            {#if openDrill === null}
                <DrillPicker
                    drills={LOGIC_DRILLS}
                    recency={(id) => recency(lastPracticed(id))}
                    on:select={(e) => openLogicDrill(e.detail)}
                />
            {:else}
                <button
                    class="backbar"
                    type="button"
                    bind:this={backEl}
                    on:click={closeLogicDrill}>&lsaquo; All drills</button
                >
                {#if openDrill === "translate"}
                    <ConditionalDrill />
                {:else if openDrill === "chain"}
                    <ChainDrill />
                {:else if openDrill === "worked"}
                    <WorkedExampleDrill />
                {:else if openDrill === "twin"}
                    <EvilTwinDrill />
                {:else if openDrill === "validity"}
                    <QuantifierDrill mode="validity" />
                {:else if openDrill === "negation"}
                    <QuantifierDrill mode="negation" />
                {:else if openDrill === "stems"}
                    <StemPolarityDrill />
                {:else}
                    <AssumptionDrill />
                {/if}
            {/if}
        {:else if data.dashboard}
            <DashboardView dashboard={data.dashboard} />
        {:else}
            <div class="notice">
                <h2>Not connected</h2>
                <p>
                    Open this page from your desktop's <b>Study on your phone</b> dialog to load your
                    progress.
                </p>
                {#if data.error}<p class="err">{data.error}</p>{/if}
            </div>
        {/if}
    </main>

    <nav class="tabs">
        <div class="tabs-inner">
        <button class:active={tab === "study"} on:click={() => (tab = "study")}>
            <svg viewBox="0 0 24 24" aria-hidden="true"
                ><path
                    d="M4 5h11l5 5v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zm0 6h9m-9 4h9"
                /></svg
            >
            <span>Study</span>
        </button>
        <button
            class:active={tab === "logic"}
            on:click={() => {
                if (tab === "logic") {
                    openDrill = null;
                }
                tab = "logic";
            }}
        >
            <svg viewBox="0 0 24 24" aria-hidden="true"
                ><path d="M5 7h6M5 12h4M8 3v18M14 8l3 3-3 3m5-3h-8" /></svg
            >
            <span>Logic</span>
        </button>
        <button class:active={tab === "progress"} on:click={() => (tab = "progress")}>
            <svg viewBox="0 0 24 24" aria-hidden="true"
                ><path d="M4 20V10m6 10V4m6 16v-7" /></svg
            >
            <span>Progress</span>
        </button>
        </div>
    </nav>
</div>

<style lang="scss">
    :global(html),
    :global(body) {
        margin: 0;
        background: var(--lsat-canvas);
    }
    .app {
        display: flex;
        flex-direction: column;
        height: 100dvh;
        /* soft brand-aura background — matches the desktop dashboard so the
         * "PROVEN" surface is identical on Mac and Android. */
        background: var(--lsat-bg);
        color: var(--lsat-fg);
        font-size: 15px;
    }
    .bar {
        position: sticky;
        top: 0;
        z-index: 5;
        padding: calc(env(safe-area-inset-top, 0px) + 0.75rem) 1rem 0.75rem;
        background: var(--lsat-surface);
        border-bottom: 1px solid var(--lsat-border-subtle);
        box-shadow: var(--lsat-shadow);
    }
    .bar-inner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.6rem;
        width: 100%;
        max-width: 960px;
        margin: 0 auto;
    }
    .identity {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        min-width: 0;
    }
    .mark {
        flex: 0 0 auto;
        display: grid;
        place-items: center;
        width: 32px;
        height: 32px;
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-hero);
        box-shadow: var(--lsat-glow);
    }
    .mark svg {
        width: 19px;
        height: 19px;
        fill: none;
        stroke: #fff;
        stroke-width: 1.7;
        stroke-linecap: round;
    }
    .brand {
        font-weight: 750;
        font-size: 1.02rem;
        letter-spacing: -0.015em;
    }
    .mode {
        flex: 0 0 auto;
        padding: 0.22rem 0.62rem;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-inset);
        border: 1px solid var(--lsat-border-subtle);
        font-size: 0.72rem;
        font-weight: 650;
        letter-spacing: 0.01em;
        color: var(--lsat-fg-subtle);
    }
    main {
        flex: 1 1 auto;
        /* Centre the content column so the phone layout does not stretch on
         * wide viewports (tablet / Android landscape / desktop preview). */
        align-self: center;
        width: 100%;
        max-width: 960px;
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
        padding: 1.1rem 1rem 1.6rem;
    }
    .phasebar {
        position: relative;
        display: flex;
        gap: 0;
        margin-bottom: 0.7rem;
        padding: 0.25rem;
        background: var(--lsat-inset);
        border: 1px solid var(--lsat-border-subtle);
        border-radius: var(--lsat-radius-pill);
    }
    /* Sliding gradient thumb behind the active segment. The segment count is fed
     * in as `--n` (3 for the study phases, 5 for the logic drills) so one rule
     * serves both bars; the transform slides by whole thumb-widths. */
    .thumb {
        position: absolute;
        top: 0.25rem;
        bottom: 0.25rem;
        left: 0.25rem;
        width: calc((100% - 0.5rem) / var(--n, 3));
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-hero);
        box-shadow: var(--lsat-glow);
        transform: translateX(calc(var(--idx) * 100%));
        transition: transform var(--lsat-transition) var(--lsat-ease);
    }
    .phasebar button {
        position: relative;
        z-index: 1;
        flex: 1 1 0;
        min-height: 38px;
        border: none;
        border-radius: var(--lsat-radius-pill);
        background: transparent;
        color: var(--lsat-fg-subtle);
        font: inherit;
        font-size: 0.8rem;
        font-weight: 650;
        cursor: pointer;
        transition:
            color var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease);
    }
    .phasebar button.active {
        color: #fff;
    }
    .phasebar button:active {
        transform: scale(0.96);
    }
    /* Back to the Drill Launcher from an open logic drill. */
    .backbar {
        display: inline-flex;
        align-items: center;
        min-height: 44px;
        margin-bottom: 0.7rem;
        padding: 0.4rem 0.9rem 0.4rem 0.7rem;
        border: 1px solid var(--lsat-border-subtle);
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-surface);
        color: var(--lsat-fg-subtle);
        font: inherit;
        font-size: 0.82rem;
        font-weight: 600;
        cursor: pointer;
        transition:
            border-color var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease);
    }
    .backbar:hover {
        border-color: color-mix(in srgb, var(--lsat-accent) 40%, var(--lsat-border-subtle));
    }
    .backbar:active {
        transform: scale(0.97);
    }
    .backbar:focus-visible {
        outline: none;
        box-shadow: var(--lsat-ring);
    }
    .phase-hint {
        margin: -0.3rem 0 0.7rem;
        font-size: 0.78rem;
        color: var(--lsat-fg-subtle);
    }
    /* Launches the self-contained Timed Section Runner route. */
    .section-cta {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.4rem;
        margin-bottom: 0.8rem;
        min-height: 46px;
        padding: 0.6rem 1rem;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-hero);
        color: #fff;
        text-decoration: none;
        font-weight: 650;
        box-shadow: var(--lsat-shadow);
        transition:
            box-shadow var(--lsat-transition) var(--lsat-ease),
            transform var(--lsat-transition) var(--lsat-ease);
    }
    .section-cta:hover {
        box-shadow: var(--lsat-glow);
    }
    .section-cta:active {
        transform: scale(0.98);
    }
    .section-cta .arrow {
        transition: transform var(--lsat-transition) var(--lsat-ease);
    }
    .section-cta:hover .arrow {
        transform: translateX(3px);
    }
    .notice {
        text-align: center;
        color: var(--lsat-fg-subtle);
        padding: 2rem 1rem;
    }
    .notice h2 {
        color: var(--lsat-fg);
    }
    .err {
        font-size: 0.78rem;
        opacity: 0.7;
        word-break: break-word;
    }
    .tabs {
        border-top: 1px solid var(--lsat-border-subtle);
        background: var(--lsat-surface);
        padding-bottom: env(safe-area-inset-bottom, 0px);
    }
    .tabs-inner {
        display: flex;
        width: 100%;
        max-width: 960px;
        margin: 0 auto;
    }
    .tabs button {
        position: relative;
        flex: 1 1 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.15rem;
        min-height: 56px;
        padding: 0.55rem 0;
        border: none;
        background: transparent;
        color: var(--lsat-fg-subtle);
        font: inherit;
        font-size: 0.72rem;
        font-weight: 600;
        cursor: pointer;
        transition: color var(--lsat-transition) var(--lsat-ease);
    }
    /* Animated top indicator that grows under the active tab. */
    .tabs button::before {
        content: "";
        position: absolute;
        top: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 0;
        height: 2.5px;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-hero);
        transition: width var(--lsat-transition) var(--lsat-ease);
    }
    .tabs button.active {
        color: var(--lsat-accent);
    }
    .tabs button.active::before {
        width: 42%;
    }
    .tabs button:active {
        transform: scale(0.94);
    }
    .tabs svg {
        width: 22px;
        height: 22px;
        fill: none;
        stroke: currentColor;
        stroke-width: 2;
        stroke-linecap: round;
        stroke-linejoin: round;
    }

    @media (prefers-reduced-motion: reduce) {
        .thumb,
        .phasebar button,
        .tabs button,
        .tabs button::before,
        .section-cta,
        .section-cta .arrow,
        .backbar {
            transition: none;
        }
        .phasebar button:active,
        .tabs button:active,
        .section-cta:active,
        .backbar:active {
            transform: none;
        }
        .section-cta:hover .arrow {
            transform: none;
        }
    }
</style>
