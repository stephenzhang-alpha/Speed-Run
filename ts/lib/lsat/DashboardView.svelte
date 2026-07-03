<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

The dashboard body (scores + "how you get questions wrong" insights + coverage +
per-topic table), shared by the desktop route and the mobile Progress tab. The
responsive `.grid` collapses to one column on narrow (phone) viewports.
-->
<script lang="ts">
    import Bar from "./Bar.svelte";
    import CalibrationDial from "./CalibrationDial.svelte";
    import ChokeMeter from "./ChokeMeter.svelte";
    import FatigueCurve from "./FatigueCurve.svelte";
    import FirstInstinctLedger from "./FirstInstinctLedger.svelte";
    import FluencyBadges from "./FluencyBadges.svelte";
    import GapMap from "./GapMap.svelte";
    import MasteryGrowthPanel from "./MasteryGrowthPanel.svelte";
    import MisconceptionPanel from "./MisconceptionPanel.svelte";
    import NextAction from "./NextAction.svelte";
    import OracleProofTheater from "./OracleProofTheater.svelte";
    import ProofHeader from "./ProofHeader.svelte";
    import RushErrorsPanel from "./RushErrorsPanel.svelte";
    import ScoreCard from "./ScoreCard.svelte";
    import TimeLeakPanel from "./TimeLeakPanel.svelte";
    import TrapBars from "./TrapBars.svelte";
    import type { Dashboard, Insights } from "./types";
    import { humanize, pct, pctRange, scoreStatus } from "./util";

    export let dashboard: Dashboard;

    $: memory = dashboard.scores.memory;
    $: performance = dashboard.scores.performance;
    $: readiness = dashboard.scores.readiness;
    $: coverage = dashboard.coverage;
    $: insights = (dashboard.insights ?? {}) as Insights;
    $: exam = dashboard.exam_schedule;
    $: adherence = dashboard.adherence;
    $: growth = dashboard.growth;
    // score availability (drives the interval band vs the earning-evidence meter)
    $: memAvail = memory.overall.memory != null;
    $: perfAvail = !!(performance.available && performance.overall && performance.overall.p != null);

    // "DO NEXT" recommendation (feed-forward primacy). The backend's
    // best_next_to_study is the considered pick; fall back to a start prompt on a
    // brand-new profile. (Confident-wrong retest priority is layered in below when
    // the misconception panel reports open items.)
    type Rec = { kind: "retest" | "study" | "start"; label: string; reason: string; count: string };
    function computeRec(
        misAvail: boolean,
        open: number,
        b: { name: string } | null | undefined,
        belowTarget: number,
    ): Rec {
        if (misAvail && open > 0) {
            return {
                kind: "retest",
                label: "Re-prove a high-confidence miss",
                reason: "confident-wrong answers are the highest-value fixes (hypercorrection)",
                count: `${open} to re-prove`,
            };
        }
        if (b?.name) {
            return {
                kind: "study",
                label: `Study ${b.name}`,
                reason: "your highest-yield next topic — build the evidence your scores need",
                count: belowTarget ? `${belowTarget} below target` : "",
            };
        }
        return {
            kind: "start",
            label: "Start a study session",
            reason: "review cards to earn your Memory, Performance and Readiness scores",
            count: "",
        };
    }
    $: misOpen = insights.misconceptions?.resolution?.open ?? 0;
    $: rec = computeRec(
        !!insights.misconceptions?.available,
        misOpen,
        readiness.best_next_to_study,
        exam?.n_below_target ?? 0,
    );

    // "How you get questions wrong" used to render nine diagnostic tiles that each
    // showed a ghost "not enough evidence yet" placeholder until its floor was met
    // -- a wall of empty cards on a fresh profile. Instead we now render only the
    // panels that have EARNED their data (so each present one is prominent), and
    // fold the rest into a single honest "unlocks as you study" strip that names
    // them + what to log. The analysis engines are unchanged; only the presentation.
    $: lockedInsights = (
        [
            ["Misconceptions", "confidence-rated answers", insights.misconceptions],
            ["Trap fingerprint", "a few wrong answers", insights.traps],
            ["Gap Map", "a blind-review pass", insights.gap_map],
            ["Calibration", "confidence-rated answers", insights.calibration],
            ["Choke index", "timed + blind-review answers", insights.choke],
            ["Fluency", "timed answers", insights.fluency],
            ["Stamina", "~20 timed answers over a few sessions", insights.fatigue],
            ["Rush errors", "timed + blind-review answers", insights.rush],
            ["Time-leak", "a blind-review pass", insights.time_leak],
        ] as [string, string, { available?: boolean } | undefined][]
    )
        .filter(([, , panel]) => !panel?.available)
        .map(([name, hint]) => ({ name, hint }));
    $: anyInsightShown = [
        insights.misconceptions,
        insights.traps,
        insights.gap_map,
        insights.calibration,
        insights.choke,
        insights.fluency,
        insights.fatigue,
        insights.rush,
        insights.time_leak,
    ].some((p) => (p as { available?: boolean } | undefined)?.available);
</script>

<!-- PROOF HEADER: premises \u22a2 an honest claim (shared desktop + Android). -->
<ProofHeader {dashboard} />

<!-- DO NEXT: the primacy slot \u2014 feed-forward before any ego-score. -->
<section class="do-next">
    <NextAction kind={rec.kind} label={rec.label} reason={rec.reason} count={rec.count} />
</section>

<!-- VERIFIED AI: the marquee demo \u2014 a recorded model draft checked live. -->
<OracleProofTheater />

<header class="sec">
    <span class="tick" aria-hidden="true"></span>
    <h2>Where you stand</h2>
    <p class="sec-sub">
        Confidence intervals, not bare numbers &mdash; a score appears only once the
        evidence earns it.
    </p>
</header>
<section class="grid scores">
    <ScoreCard
        title="Memory"
        available={memAvail}
        big={pct(memory.overall.memory)}
        unit="%"
        min={0}
        max={100}
        point={memory.overall.memory != null ? memory.overall.memory * 100 : null}
        low={memory.overall.low != null ? memory.overall.low * 100 : null}
        high={memory.overall.high != null ? memory.overall.high * 100 : null}
        note={memory.overall.note ?? ""}
    />
    <ScoreCard
        title="Performance"
        available={perfAvail}
        big={pct(performance.overall?.p ?? null)}
        unit="%"
        min={0}
        max={100}
        point={performance.overall?.p != null ? performance.overall.p * 100 : null}
        low={performance.overall?.low != null ? performance.overall.low * 100 : null}
        high={performance.overall?.high != null ? performance.overall.high * 100 : null}
        note={performance.note ?? ""}
    />
    <ScoreCard
        title="Readiness"
        available={!!readiness.available}
        big={readiness.available ? String(readiness.point_estimate) : ""}
        min={120}
        max={180}
        point={readiness.available ? (readiness.point_estimate ?? null) : null}
        low={readiness.available && readiness.range ? readiness.range[0] : null}
        high={readiness.available && readiness.range ? readiness.range[1] : null}
        widened={!!readiness.range_widened_by_miscalibration}
        earnedNote={!readiness.available ? `${readiness.missing?.length ?? 0} requirements left` : ""}
        unlockLabel={!readiness.available ? "unlocks your projected score" : ""}
        note={readiness.available
            ? `confidence: ${readiness.confidence?.[1] ?? ""}`
            : (readiness.reason ?? "")}
    >
        {#if readiness.available}
            {#if readiness.top_reasons?.length}
                <ul class="reasons">
                    {#each readiness.top_reasons as reason (reason)}<li>{reason}</li>{/each}
                </ul>
            {/if}
            {#if readiness.best_next_to_study}
                <p class="next">Best next: <b>{readiness.best_next_to_study.name}</b></p>
            {/if}
            {#if readiness.past_projection_track_record?.note}
                <p class="muted sm">{readiness.past_projection_track_record.note}</p>
            {/if}
        {:else if readiness.missing?.length}
            <ul class="reasons">
                {#each readiness.missing as item (item)}<li>{item}</li>{/each}
            </ul>
        {/if}
    </ScoreCard>
</section>

{#if adherence?.available}
    <div class="plan" class:replan={adherence.needs_replan}>
        <span class="plan-ic" aria-hidden="true">◎</span>
        <div class="plan-body">
            <p class="plan-if">{adherence.if_then}</p>
            <p class="plan-note">
                Completed on <b>{adherence.completed_days ?? 0}</b>/{adherence.window_days ?? 14}
                days{adherence.needs_replan ? " — want to re-plan a cue that fits better?" : "."}
            </p>
        </div>
    </div>
{/if}

{#if exam?.available}
    <div class="runway">
        <div class="runway-days">
            <span class="rd-num">{exam.days_until_exam}</span>
            <span class="rd-cap">days to exam</span>
        </div>
        <div class="runway-body">
            <p class="rd-note">{exam.note}</p>
            <div class="rd-stats">
                <span><b>{exam.n_below_target ?? 0}</b> below exam-day target</span>
                {#if exam.n_due_after_exam}
                    <span><b>{exam.n_due_after_exam}</b> not due before the exam</span>
                {/if}
                {#if exam.desired_retention != null}
                    <span>target {Math.round((exam.desired_retention ?? 0) * 100)}%</span>
                {/if}
            </div>
        </div>
    </div>
{/if}

{#if growth?.available}
    <header class="sec">
        <span class="tick" aria-hidden="true"></span>
        <h2>Your progress</h2>
        <p class="sec-sub">{growth.note}</p>
    </header>
    <MasteryGrowthPanel {growth} />
{/if}

<div class="grid ledger">
    <FirstInstinctLedger panel={dashboard.answer_change ?? {}} />
</div>

<header class="sec">
    <span class="tick" aria-hidden="true"></span>
    <h2>How you get questions wrong</h2>
    <p class="sec-sub">
        Signals no other SRS captures. Each panel appears the moment you&rsquo;ve
        logged enough evidence &mdash; the rest are listed below, not left as blanks.
    </p>
</header>
{#if anyInsightShown}
    <div class="grid insights">
        {#if insights.misconceptions?.available}
            <MisconceptionPanel panel={insights.misconceptions} />
        {/if}
        {#if insights.traps?.available}<TrapBars panel={insights.traps} />{/if}
        {#if insights.gap_map?.available}<GapMap panel={insights.gap_map} />{/if}
        {#if insights.calibration?.available}
            <CalibrationDial panel={insights.calibration} />
        {/if}
        {#if insights.choke?.available}
            <ChokeMeter panel={insights.choke} pacing={insights.pacing ?? {}} />
        {/if}
        {#if insights.fluency?.available}<FluencyBadges panel={insights.fluency} />{/if}
        {#if insights.fatigue?.available}<FatigueCurve panel={insights.fatigue} />{/if}
        {#if insights.rush?.available}<RushErrorsPanel panel={insights.rush} />{/if}
        {#if insights.time_leak?.available}<TimeLeakPanel panel={insights.time_leak} />{/if}
    </div>
{/if}
{#if lockedInsights.length}
    <div class="locked">
        <span class="locked-ic" aria-hidden="true">
            <svg viewBox="0 0 24 24"
                ><rect x="5" y="11" width="14" height="9" rx="2" /><path
                    d="M8 11V8a4 4 0 0 1 8 0v3"
                /></svg
            >
        </span>
        <p>
            <b
                >{lockedInsights.length} more diagnostic{lockedInsights.length > 1
                    ? "s"
                    : ""} unlock as you study:</b
            >
            {lockedInsights.map((d) => d.name).join(", ")}. Log timed answers, then a
            blind-review pass, and each appears here on its own the moment it has the
            evidence &mdash; never a fabricated number.
        </p>
    </div>
{/if}

<header class="sec">
    <span class="tick" aria-hidden="true"></span>
    <h2>Coverage</h2>
    <p class="sec-sub">
        Question types with enough reviewed cards, plus the primitive taxonomy the deck teaches.
    </p>
</header>
<div class="cov panel">
    <div class="cov-head">
        <div class="cov-metric">
            <span class="cov-num">{coverage.pct}<span class="cov-unit">%</span></span>
            <span class="cov-cap">question types covered</span>
        </div>
        <div class="cov-barwrap">
            <div class="bar"><div class="fill" style="width: {coverage.pct}%"></div></div>
            <p class="muted">
                {coverage.covered}/{coverage.total} question types with &ge;{coverage.min_items}
                reviewed cards ({coverage.pct}%)
            </p>
        </div>
    </div>
    {#if coverage.primitives?.families}
        <div class="prim">
            <p class="prim-title">Primitive taxonomy</p>
            {#each Object.entries(coverage.primitives.families) as [family, f] (family)}
                <div class="prim-row">
                    <span class="prim-name">{humanize(family)}</span>
                    <Bar value={(f.pct ?? 0) / 100} status="neutral" height={8} />
                    <span class="prim-val">{f.covered}/{f.total}</span>
                </div>
            {/each}
            <p class="muted sm">
                Primitive taxonomy the deck teaches (diction / logic / qtype) &mdash;
                {coverage.primitives.overall_pct}% overall; readiness abstains below the
                README threshold.
            </p>
        </div>
    {/if}
</div>

<header class="sec">
    <span class="tick" aria-hidden="true"></span>
    <h2>Per-topic memory</h2>
    <p class="sec-sub">Per-topic recall from FSRS; a row abstains until the topic has enough reviews.</p>
</header>
<div class="table-wrap">
    <table>
        <thead>
            <tr>
                <th>Topic</th>
                <th>Kind</th>
                <th>Memory</th>
                <th>Range / status</th>
                <th class="num">Cards</th>
                <th class="num">Reviews</th>
            </tr>
        </thead>
        <tbody>
            {#each memory.topics as t (t.node_id)}
                <tr class:abstained={!t.enough_evidence}>
                    <td class="topic">{t.name}</td>
                    <td><span class="kind">{t.kind === "question_type" ? "QT" : "skill"}</span></td>
                    <td class="mem">
                        {#if t.enough_evidence}
                            <span class="mem-val">{pct(t.memory)}</span>
                            <Bar value={t.memory ?? 0} status={scoreStatus(t.memory)} height={5} />
                        {:else}
                            <span class="muted">{"\u2014"}</span>
                        {/if}
                    </td>
                    <td class="muted">
                        {t.enough_evidence ? pctRange(t.low ?? null, t.high ?? null) : (t.note ?? "")}
                    </td>
                    <td class="num">{t.n_cards ?? 0}</td>
                    <td class="num">{t.n_reviews ?? 0}</td>
                </tr>
            {/each}
        </tbody>
    </table>
</div>

<style lang="scss">
    .muted {
        color: var(--lsat-fg-subtle);
        font-size: 0.85em;
    }
    .sm {
        font-size: 0.78rem;
    }
    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: var(--lsat-gap);
    }
    /* Three-up headline score band; collapses to one column on phones. */
    .grid.scores {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    @media (max-width: 680px) {
        .grid.scores {
            grid-template-columns: 1fr;
        }
    }
    /* First-Instinct Ledger sits as its own single-card strip below progress. */
    .grid.ledger {
        margin-top: var(--lsat-gap);
    }

    /* The single "unlocks as you study" strip that replaces the wall of ghost
     * diagnostic cards -- a calm, muted inset, not an alarming empty state. */
    .locked {
        display: flex;
        align-items: flex-start;
        gap: 0.6rem;
        margin-top: var(--lsat-gap);
        padding: 0.75rem var(--lsat-pad);
        background: var(--lsat-inset);
        border: 1px dashed var(--lsat-border-subtle);
        border-radius: var(--lsat-radius);
    }
    .locked-ic {
        flex: 0 0 auto;
        margin-top: 0.05rem;
    }
    .locked-ic svg {
        width: 18px;
        height: 18px;
        fill: none;
        stroke: var(--lsat-fg-subtle);
        stroke-width: 1.8;
        stroke-linecap: round;
        stroke-linejoin: round;
    }
    .locked p {
        margin: 0;
        font-size: 0.82rem;
        line-height: 1.45;
        color: var(--lsat-fg-subtle);
    }
    .locked b {
        color: var(--lsat-fg);
    }

    /* If-Then study plan (DECISION-round2 #4): a calm adherence strip. */
    .plan {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        margin-top: var(--lsat-gap);
        padding: 0.7rem var(--lsat-pad);
        background: var(--lsat-surface);
        border: 1px solid var(--lsat-border-subtle);
        border-left: 3px solid var(--lsat-accent);
        border-radius: var(--lsat-radius);
        box-shadow: var(--lsat-shadow);
    }
    .plan.replan {
        border-left-color: var(--lsat-warn);
    }
    .plan-ic {
        font-size: 1.3rem;
        color: var(--lsat-accent);
    }
    .plan.replan .plan-ic {
        color: var(--lsat-warn);
    }
    .plan-if {
        margin: 0;
        font-weight: 650;
        font-size: 0.92rem;
    }
    .plan-note {
        margin: 0.15rem 0 0;
        font-size: 0.8rem;
        color: var(--lsat-fg-subtle);
        font-variant-numeric: tabular-nums;
    }
    .plan-note b {
        color: var(--lsat-fg);
    }

    /* Exam runway (DECISION-round2 #7): days-to-exam + consolidation summary. */
    .runway {
        display: flex;
        align-items: stretch;
        gap: var(--lsat-pad);
        margin-top: var(--lsat-gap);
        padding: var(--lsat-pad);
        background: var(--lsat-surface);
        border: 1px solid var(--lsat-border-subtle);
        border-radius: var(--lsat-radius);
        box-shadow: var(--lsat-shadow);
    }
    .runway-days {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-width: 5.2rem;
        padding: 0.5rem 0.8rem;
        border-radius: var(--lsat-radius-sm);
        background: var(--lsat-hero);
        color: #fff;
        box-shadow: var(--lsat-glow);
    }
    .rd-num {
        font-size: 1.9rem;
        font-weight: var(--lsat-num);
        line-height: 1;
        font-variant-numeric: tabular-nums;
    }
    .rd-cap {
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        opacity: 0.92;
    }
    .runway-body {
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 0.35rem;
        min-width: 0;
    }
    .rd-note {
        margin: 0;
        font-size: 0.9rem;
        line-height: 1.4;
    }
    .rd-stats {
        display: flex;
        flex-wrap: wrap;
        gap: 0.3rem 0.9rem;
        font-size: 0.8rem;
        color: var(--lsat-fg-subtle);
        font-variant-numeric: tabular-nums;
    }
    .rd-stats b {
        color: var(--lsat-fg);
    }

    /* Section headers: a signature gradient tick, a confident title, and an
     * honest subtitle. */
    .sec {
        display: grid;
        grid-template-columns: auto 1fr;
        align-items: center;
        column-gap: 0.7rem;
        margin: 2.3rem 0 0.95rem;
    }
    /* The proof-rail motif: a gradient gutter that draws itself in on mount
     * (a derivation being written). */
    .sec .tick {
        grid-row: 1 / -1;
        align-self: stretch;
        width: var(--lsat-rail-w, 3px);
        min-height: 1.7rem;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-rail);
        transform: scaleY(0);
        transform-origin: top;
        animation: rail-in 420ms var(--lsat-ease) 60ms forwards;
    }
    .do-next {
        margin-top: 0.2rem;
    }
    @keyframes rail-in {
        to {
            transform: scaleY(1);
        }
    }
    .sec h2 {
        grid-column: 2;
        margin: 0;
        font-size: 1.12rem;
        font-weight: 700;
        letter-spacing: -0.01em;
    }
    .sec .sec-sub {
        grid-column: 2;
        margin: 0.15rem 0 0;
        font-size: 0.82rem;
        line-height: 1.4;
        color: var(--lsat-fg-subtle);
    }

    .reasons {
        margin: 0.4rem 0 0;
        padding-left: 1.1rem;
        font-size: 0.8rem;
        color: var(--lsat-fg-subtle);
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
    }
    .next {
        margin: 0.5rem 0 0;
        font-size: 0.9rem;
    }

    /* Surface panel wrapping the coverage visualization. */
    .panel {
        background: var(--lsat-surface);
        border: 1px solid var(--lsat-border-subtle);
        border-radius: var(--lsat-radius);
        box-shadow: var(--lsat-shadow);
        padding: var(--lsat-pad);
    }
    .cov-head {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 1.3rem;
    }
    .cov-metric {
        display: flex;
        flex-direction: column;
        line-height: 1;
    }
    .cov-num {
        width: fit-content;
        font-family: var(--lsat-mono);
        font-size: clamp(2rem, 1.5rem + 2vw, 2.6rem);
        font-weight: var(--lsat-num);
        line-height: 1;
        letter-spacing: -0.01em;
        /* Solid, high-contrast, tabular — a number you can trust (not gradient). */
        font-variant-numeric: tabular-nums slashed-zero;
        color: var(--lsat-fg);
    }
    .cov-unit {
        margin-left: 0.05em;
        font-size: 0.5em;
        font-weight: 700;
    }
    .cov-cap {
        margin-top: 0.4rem;
        font-size: 0.72rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--lsat-fg-subtle);
    }
    .cov-barwrap {
        flex: 1 1 240px;
        min-width: 200px;
    }
    .cov-barwrap .muted {
        margin: 0.45rem 0 0;
    }
    .cov .bar {
        height: 12px;
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-inset);
        border: 1px solid var(--lsat-border-subtle);
        overflow: hidden;
    }
    .cov .fill {
        height: 100%;
        border-radius: inherit;
        background: var(--lsat-hero);
        transition: width var(--lsat-transition) var(--lsat-ease);
    }
    .prim {
        margin-top: 1rem;
        padding-top: 0.9rem;
        border-top: 1px solid var(--lsat-border-subtle);
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }
    .prim-title {
        margin: 0 0 0.1rem;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--lsat-fg-subtle);
    }
    .prim-row {
        display: grid;
        grid-template-columns: 6.5rem 1fr 3rem;
        align-items: center;
        gap: 0.6rem;
        font-size: 0.8rem;
    }
    .prim-name {
        color: var(--lsat-fg);
    }
    .prim-val {
        text-align: right;
        color: var(--lsat-fg-subtle);
        font-variant-numeric: tabular-nums;
    }

    .table-wrap {
        overflow-x: auto;
        border: 1px solid var(--lsat-border-subtle);
        border-radius: var(--lsat-radius);
        background: var(--lsat-surface);
        box-shadow: var(--lsat-shadow);
    }
    table {
        width: 100%;
        border-collapse: collapse;
        font-variant-numeric: tabular-nums;
    }
    th,
    td {
        text-align: left;
        padding: 0.55rem 0.8rem;
        border-bottom: 1px solid var(--lsat-border-subtle);
        white-space: nowrap;
    }
    thead th {
        background: var(--lsat-inset);
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--lsat-fg-subtle);
    }
    th.num,
    td.num {
        text-align: right;
    }
    td.topic {
        font-weight: 600;
    }
    tbody tr {
        transition: background var(--lsat-transition) var(--lsat-ease);
    }
    tbody tr:hover {
        background: var(--lsat-accent-soft);
    }
    tbody tr:last-child td {
        border-bottom: none;
    }
    tr.abstained td {
        opacity: 0.55;
    }
    .kind {
        display: inline-block;
        padding: 1px 7px;
        border-radius: var(--lsat-radius-pill);
        border: 1px solid var(--lsat-border-subtle);
        background: var(--lsat-inset);
        font-size: 0.66rem;
        font-weight: 650;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--lsat-fg-subtle);
    }
    td.mem {
        min-width: 118px;
        white-space: normal;
    }
    .mem-val {
        display: block;
        margin-bottom: 3px;
        font-weight: 650;
    }

    @media (prefers-reduced-motion: reduce) {
        .sec .tick {
            animation: none;
            transform: scaleY(1);
        }
    }
</style>
