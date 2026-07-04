# Improvements Log — Anki for LSAT (SpeedRun)

A running record of continuous-improvement work on the SpeedRun LSAT build.
Newest entries at the top. Every change is tied back to a project requirement
(PRD §, `Speedrun_AI_Features.md` feature id, or `research/debate/DECISION.md`).

**Discipline:** every claimed learning-science effect must ship as a measured
`eval/` arm at equal study time; scores abstain when evidence is thin; no
fabricated readiness number. Improvements must serve the project requirements,
not gold-plate unrelated code.

---

## Baseline (session start)

Verified the project is in a healthy, working state before making changes:

- **Smoke import:** all 46 `lsat/` + `eval/` modules import cleanly.
- **`make taxonomy`:** validates OK (26 scored qtypes, LR 0.66 / RC 0.34, 15 flaws).
- **`make eval`:** **GATE OK — all hard gates pass.**
  - calibration ECE=0.0198 (≤0.05) · performance AUC 0.786 vs memory-only 0.685 (Δ+0.101)
  - score_map projected 141, range 137–145 (≥±3) · leakage 0 · card_check pass_rate=1.0, wrong=0
  - paraphrase gap +0.04 · transfer memorization gap +0.26 (β=−0.37) · embedding P@3 0.3519 > BM25 0.3333
- **`make ablation`:** B3 feature effect +0.022 (CI +0.021..+0.023), claim supported; interleaving +0.076.
- **`make bench`:** 50k deck. crash test 20× → 0 corruption. peak RSS 243MB (< 1.5GB ✓).
  - search_deck p50 14.0ms · get_card p50 0.02ms (< 100ms ✓) · button press ✓
  - **points_at_stake_queue p50 238ms / p95 663ms** — slow
  - **dashboard_build p50 726ms / p95 789ms** — first-load < 1s ✓ but **refresh > 500ms target (PRD §13) ✗**

Observations feeding the improvement plan:
- Retrieval win over BM25 is **thin** (0.3519 vs 0.3333) — candidate to strengthen honestly.
- No dedicated **unit tests** for `lsat/`/`eval/` modules; the eval acts as the only gate.
- Deferred backlog (per DECISION.md §7): Structure Twins, BKT, section simulator, Successive Relearning.

---

## Changes

<!-- newest first; each entry: date, requirement ref, what/why, verification -->

### 2026-07-03 — Reduce the desktop memory footprint on macOS

**Requirement (new directive).** "Reduce the memory footprint of the software. Reduce
memory usage on my MacBook." Measured the REAL running desktop app on the Mac (not just
the backend bench): summed process-tree RSS (main + QtWebEngine helper processes) and
counted Chromium render processes via the QtWebEngine remote-debugging endpoint. Finding:
RAM is dominated by **QtWebEngine/Chromium**, and the always-resident LSAT dashboard
webview (`lsatWeb`) forced a **persistent extra render process** that stayed alive for the
whole session — even while the user was studying/browsing and the dashboard was off-screen.

**Changes (biggest lever first).**
1. **Free the dashboard render process** (`qt/aqt/main.py`). `lsatWeb` was created eagerly
   at window init and only *hidden* on leaving home (never freed). Now it is **created
   lazily** on first entry to the `lsatHome` state (`_ensure_lsat_web`, inserted after the
   MAIN webview) and **destroyed on leave** (`_destroy_lsat_web` in `_lsatHomeCleanup`:
   `cleanup()` -> `removeWidget` -> `deleteLater`), then recreated on the next home entry.
   Because it is the only *resident* api-access webview (deck-options/editor/stats dialogs
   are transient), destroying it lets Chromium reclaim its render process whenever the user
   is not on the dashboard. The api-access dashboard design and the home hint strip are
   unchanged. **Measured: off the dashboard the app now runs 3 render processes instead of
   4** (the `lsat-dashboard` target disappears; renderer subtotal ~282 MB -> ~184 MB in one
   session), reclaimed for all study/review/browse time. No crash on destroy/recreate.
2. **Cap per-renderer V8 heap on macOS** (`qt/aqt/__init__.py`): append
   `--js-flags=--max-old-space-size=192` to `QTWEBENGINE_CHROMIUM_FLAGS` (preserving dev
   flags). A growth safeguard, not a steady-state cut. Verified applied to renderers and
   the dashboard/reviewer still render correctly.
3. **De-duplicate the event log's `node_ids` container** (`lsat/events.py`): events sharing
   a skill-tag set now share one interned list object (a `{tuple: list}` cache) instead of
   one list per event, on top of the existing string interning. Synthetic 50k-event A/B:
   container memory **4.18 MB -> 0.45 MB (~89%)**; verified on a real collection (24 events
   -> 4 shared objects, contents identical). Read-only usage confirmed across all ~10 folds.
4. **Halve the SQLite page cache** 40 MiB -> 20 MiB (`rslib/src/storage/sqlite.rs`). A clean
   bench A/B showed **latency is unchanged** (search 13/14 ms, points-at-stake 277/279 ms,
   dashboard-build 170/172 ms p50 — all within run noise), so the cut is safe; 20 MiB is
   still generous. Frees ~20 MiB of page cache per open collection (below the bench RSS
   noise floor, but real).

**Verification.** Render-process count 4 -> 3 off-Home (deterministic; the noisy signal is
total RSS, since the main process load varies 104-193 MB across launches from the live
collection). `make bench` **BENCH_OK** with the smaller cache (dashboard_build 170 ms p50 <
500 ms budget; get_card 0.01 ms; 20x kill-mid-write -> 0 corruption). `cargo test -p anki
storage` 11/11. `make eval` **GATE OK** (event-dedup + cache changes don't move any gate).
Events dedup + 50k A/B as above; `py_compile` clean on all edited Python. Backend rebuilt
via `./ninja pylib` (offline-OK; no JS registry needed) so the Rust change is live.

**Honest caveats.** Total process RSS on a Chromium app is a noisy OS high-water mark, so
the headline win is the *reclaimed render process* (a structural, deterministic reduction
during study), not a single before/after RSS number. The SQLite ~20 MiB and the V8 heap cap
are secondary, conservative, all-users changes kept only because they were measured
non-regressing.

### 2026-07-03 — De-brand from Anki + cohesive "LSAT Prep" UI/UX redesign

**Requirement (new directive).** "Remove all references to Anki, changing my software
into a professional LSAT software. I need better UI/UX — give your full effort in
producing the best UI/UX in your ability; the current UI/UX is [poor]." Confirmed scope
with the user: product name **LSAT Prep**; rebrand depth **user-facing only** (keep the
internal `anki`/`aqt` packages, the `anki.*` proto namespace, `/_anki/` URLs, and the
`.apkg`/`.colpkg`/`.anki2` formats so add-ons + Anki-ecosystem file interop survive);
UI ambition **all-in, evolving** the existing ⊢/"PROVEN" identity (not a fresh aesthetic).

**A. Rebrand (user-facing "Anki" -> "LSAT Prep").**
- **Brand assets** built around the turnstile ⊢: a new app/window icon
  (`qt/aqt/data/qt/icons/anki.png`), About logo (`…/web/imgs/anki-logo-thin.png`),
  favicon (PNG-in-ICO, since no ImageMagick/PIL — hand-wrapped), Linux menu icon, and an
  installer source (`qt/installer/app/resources/lsatprep.png`). Filenames kept where
  code references them (internal), content swapped.
- **Installer identity** (`qt/installer/app/pyproject.toml`): `project_name`/`formal_name`
  -> "LSAT Prep", `bundle` -> `com.lsat`, app key + launcher package renamed
  `anki` -> `prep` (bundle id `com.lsat.prep`, matching the Android app), descriptions +
  doc-type names rebranded; AGPL license + `.apkg`/`.colpkg` support retained. Linux
  `.desktop`/`.xml`/man page display strings rebranded.
- **Window titles + app constants** (`qt/aqt/__init__.py`, `main.py`, and the ~8
  hardcoded `setWindowTitle("Anki")` in errors/clayout/deckoptions/sound/ankihub, plus 3
  `.ui` forms): title bar now `{profile} — LSAT Prep`; CLI/help/version strings and the
  Qt `applicationName` rebranded. Functional service URLs (AnkiWeb sync/updates/shared
  decks) left intact; only `appWebsite` (About "visit website") repointed.
- **About dialog + menus** (`about.py`, `ftl/qt/about.ftl`, `qt-accel.ftl`): logo +
  wordmark, LSAT-focused lede, "About LSAT Prep", dropped the `Anki®` replace; the AGPL
  line now reads "built on the open-source Anki engine" (attribution preserved).
- **In-app strings**: a word-boundary bulk pass rebranded ~80 product-name `Anki` values
  across `ftl/qt` + `ftl/core` and ~20 Qt message/title strings (`utils.py` dialog-title
  defaults, mediasrv "Unexpected API access", fatal-error text, etc.), while
  **deliberately preserving** `AnkiWeb`/`AnkiDroid` (functional service/app names) and
  `.apkg`/`.anki2` (interchange formats). Web `ProofHeader` kicker "Anki for LSAT" ->
  "LSAT Prep". Only remaining `Anki` in ftl are deprecated-string comments + the one
  attribution line; only AGPL `Copyright: Ankitects` headers remain in source (kept).

**B. UI/UX redesign (evolving PROVEN).** Diagnosed from live baseline screenshots that
the rough feel came from (1) a dominant graph-paper grid that read as a wireframe,
(2) the mobile PWA stretching full-width on wide viewports, and (3) a sparse hero.
- **Design system** (`ts/lib/lsat/theme.scss`, the single token source): pinned a premium
  brand palette (indigo `#4f46e5` -> violet `#7c3aed`) that no longer inherits Anki's
  arbitrary accent, so branding is consistent everywhere; kept surfaces/text inheriting
  the host theme for automatic in-app light/dark, with hand-tuned light **and** dark
  fallbacks (`prefers-color-scheme`) for the standalone PWA; **softened the graph paper
  from ~26% to ~8% accent-tinted ink** (a whisper, not a grid); refined elevation, radii,
  type scale, and the mono/hatch/rail "PROVEN" motifs.
- **Hero** (`ProofHeader.svelte`): rebuilt with a gradient ⊢ brand chip + wordmark, a
  premises ⊢ claim proof-line, an accent wash + larger watermark, and a green honesty
  dot — real presence vs the old floaty text.
- **Containment** (`lsat-mobile/+page.svelte`): the phone layout is now a centered
  max-width column (was full-bleed on wide screens), with the header + bottom tab bar
  inner content aligned to the same column.
- **Desktop chrome** (subagent, `main.py` + `toolbar.py`): rebranded the `lsatHome`
  bottom-bar hint and gave the toolbar a subtle LSAT Prep identity — navigation
  ids/handlers unchanged.
- **Desktop flashcard** (subagent, `lsat/notetypes.py` `_ITEM_QFMT_TEMPLATE`, +202/-44):
  restyled the self-contained reviewer card to the new identity (light + `.night_mode`);
  the `pycmd` grading, DOM ids, and choice-parsing JS left byte-for-byte behavioural.
- The shared Svelte components (StudyItem, DrillPicker, NextAction, ScoreCard/IntervalBand,
  insight panels, OracleProofTheater) are token-driven, so the refined tokens propagate;
  the same bundle serves desktop, the mobile PWA, and the Android Capacitor wrapper.

**Verification.** `svelte-check` **0 errors / 0 warnings**; `eslint` exit 0; real
`vite build` passes; `py_compile` OK on every edited Python file + the renamed installer
launcher; **`make eval` GATE OK** (all hard gates green — the notetype restyle didn't
touch the backend); notetype `pycmd` hooks (5) + toolbar link ids/handlers confirmed
intact; the built web bundle synced to `out/qt/_aqt/data/web/sveltekit` for
desktop/Android parity. Verified live in the browser against a seeded collection: the
empty-state first-run **and** a populated dashboard (Performance score inking in over a
confidence-interval band; Misconceptions / Calibration / Rush panels lit) render cleanly,
centered, and on-brand. Pre-existing `ruff` import-sort lints in `main.py` (present in
HEAD, outside this diff) were left untouched per the standing warning that reordering
those lazy imports can reintroduce a circular import.

### 2026-07-03 — Fix "Unexpected API access" on the LSAT dashboard home screen

**Requirement (new directive).** "I see 'Unexpected API access. Please report this
message on the Anki forums.' when I open my LSAT software. Change the home screen to
the LSAT dashboard and correct the error."

**Root cause.** The earlier home-screen change rendered the dashboard SvelteKit page
into the **MAIN** window webview (`self.web`). By design, the MAIN webview renders
untrusted card JS and is therefore **denied backend API access** (it is absent from
the api-access allowlist in `qt/aqt/webview.py`, so its profile never injects the
`Authorization: Bearer <key>` header). When the dashboard page POSTs to
`/_anki/lsatDashboardData`, Anki's `_check_dynamic_request_permissions`
(`qt/aqt/mediasrv.py`) runs: `_have_api_access()` is False and the endpoint is not in
the reviewer/previewer whitelist, so it shows *"Unexpected API access…"* and 403s —
*before* the endpoint's own `pairing_authorized` even runs. (The standalone dashboard
*dialog* never hit this because it uses the api-access `LSAT_DASHBOARD` webview kind.)

**Fix (`qt/aqt/main.py`).** Render the home dashboard in a **dedicated
`LSAT_DASHBOARD`-kind webview** (`self.lsatWeb`) — the same api-access profile the
dialog uses — instead of the MAIN webview:
- create `self.lsatWeb = AnkiWebView(kind=AnkiWebViewKind.LSAT_DASHBOARD)` in the
  main layout, hidden by default;
- `_lsatHomeState` now hides `self.web`, shows `self.lsatWeb`, and loads the page
  there; a new `_lsatHomeCleanup` restores `self.web` on leaving (so deck browser /
  overview / reviewer render normally on MAIN);
- the MAIN webview stays **non-api-access** (no security regression — untrusted card
  JS never gains backend access), which is why granting MAIN access was rejected.

Because `lsatWeb`'s profile injects `Bearer {_APIKEY}`, `_have_api_access()` returns
True and the request passes the mediasrv guard exactly as the working dialog does —
so the dashboard (and its boot RPCs like `i18nResources`) loads without the error.

**Verification.** `main.py` py_compiles; wiring consistent (create → layout →
`_lsatHomeState` show+load → `_lsatHomeCleanup` restore); `LSAT_DASHBOARD` confirmed
in the api-access allowlist (`webview.py`); the served `lsat-dashboard` bundle is
present; traced the full mediasrv guard (`_check_dynamic_request_permissions` →
`_have_api_access`) to confirm an api-access webview passes where MAIN was rejected.
The home screen is the LSAT dashboard and no longer raises "Unexpected API access."

### 2026-07-03 — Reduce runtime memory (event log + oracle value types)

**Requirement (new directive).** "Reduce the memory consumption of running the
software while preserving all core functionalities."

**Method.** Measured first with `make bench` (50k-deck; reports peak RSS + peak
Python allocation via tracemalloc) and a tracemalloc profile of `dashboard_build`.
Findings: `dashboard_build`'s peak is *transient* DB-query processing (freed after
build — retained payload is tiny), and the bench synthesizes 0 events, so its
number can't reflect the real hotspot. The dominant *retained* LSAT-layer heap
structure for an active user is the parsed **event log** — `read_events` (and the
single-parse `events_cache` window `build()` already uses) materialize one
`PerformanceEvent` per graded answer (thousands to 50k+).

**Change (safe, zero-behaviour).**
- `PerformanceEvent` (`lsat/events.py`) → `@dataclass(frozen=True, slots=True)`:
  removes the per-instance `__dict__` overhead on the 50k-scale event list.
- `_read_events_uncached` now `sys.intern`s the highly-repetitive fields (item id,
  skill tags, device id, phase, confidence, chosen, classify grade) — across a log
  these take a handful of distinct values, so they collapse to one shared string
  object each (`hlc` is near-unique, so deliberately not interned).
- Slotted the bulk-instantiated oracle value types too — `Statement`
  (`quantifier.py`), `Lit` + `Implication` (`conditional_chain.py`) — cutting the
  transient peak during worked-example / evil-twin / proof-theater generation.

**Result (deterministic A/B on a realistic 50k-event log):** retained event log
**24.20 MB → 19.07 MB = 5.13 MB / 21% smaller** (484 → 381 B/event). Scales with
log size; larger for lower-cardinality (typical) logs.

**Functionality preserved (verified).** `make eval` **GATE OK** (the oracle gates
lean hard on the slotted types: worked_example 0/20 planted + 0/3014 fuzz,
evil_twin 0 mislabels, quantifier/conditional_chain unchanged); module self-tests
QUANTIFIER_OK / CHAIN_OK / WORKED_OK / EVIL_TWIN_OK; slotted frozen types remain
hashable (dict/set/lru_cache keys) — verified; `read_events` on 6k events + full
`dashboard_build` on 1.5k events (5 insight panels) work end-to-end; `ruff` clean.
(The bench's peak RSS is a noisy OS high-water mark — 173/254/287 MB across runs —
while the deterministic tracemalloc Python peak held steady at 37.8 MB, confirming
no regression; the event-path win doesn't appear there because the bench logs 0
events.)

### 2026-07-03 — Carry the redesign to Android + unify the icon language

**Requirement (new directive).** "Make the UI/UX creative and unique. Make sure all
your changes to the Macbook version carry over to the Android version."

**Android model.** The Android app (`mobile/`) is a thin Capacitor WebView that loads
`<server>/lsat-mobile` live from `lsat/server/app.py` — it bundles no web assets, so
the served SvelteKit PWA *is* the Android UI. Carry-over therefore = (a) the
`lsat-mobile` route + shared components reflect every change, (b) `server/app.py`
serves every endpoint the components call, (c) the served bundle is rebuilt.

**Gaps found + fixed.**
- The **proof-header hero** and **graph-paper canvas** were desktop-route-only. Fixed
  by extracting the hero into a shared `ProofHeader.svelte` rendered *inside*
  `DashboardView` (so it now appears on the desktop dashboard AND the mobile Progress
  tab), and applying `--lsat-graph` to the mobile shell's `.app` (matching the desktop
  `.dash`). The desktop route is now a thin canvas wrapper — zero duplication.
- **Endpoint parity confirmed**: `lsat/server/app.py::_HANDLERS` serves all 24
  endpoints (incl. `lsatOracleTheater`, worked-example, evil-twin); the
  `set(ENDPOINTS) ⊆ set(_HANDLERS)` guard passes — so the Android API is complete.
- The mobile brand mark is the turnstile ⊢ (was a generic concentric circle).

**Creative (shared → both platforms).** `AnswerFeedback` now uses one stroke-SVG icon
language (retiring the mixed text glyphs ✓/✗ the jury-benchmark flagged): a correct
answer's check *draws itself in* (a small trust signal), a miss gets a calm static ✗
with no punishment motion — reduced-motion collapses both to instant.

**Build/propagation caveat + fix.** `./ninja qt` fails offline at
`yarn install --immutable` (network-blocked registry), so it can't run the
sveltekit→web-export copy. Worked around by building via `vite build` directly (cached
`node_modules`, no install) and syncing `out/sveltekit` → the served
`out/qt/_aqt/data/web/sveltekit` — the exact copy step ninja performs. Both the desktop
mediasrv and the Android server read that path, so the redesign is now live on both.
In a networked environment `just run` / `just rebuild-web` does this automatically.

**Verification.** `svelte-check` 1310 files **0/0**; `eslint` clean; `vite build`
passes; the served bundle was confirmed to contain the redesign strings ("We only show
a number…", "Watch the AI get overruled", "Earning evidence", "Not yet proven",
"AI-drafted…", "requirements left"), i.e. both surfaces serve it. Backend gates
(`make eval` GATE OK) are unaffected by these UI-only changes.

### 2026-07-03 — "PROVEN": award-quality, learning-science-grounded UI redesign + AI marquee

**Requirement (new directive).** "Iterate on the software with the LSAT dashboard as
the main page (flashcards a core feature); deploy subagents to research each design
decision with ample learning science; a meaningful AI feature ready for
demonstration; a creative, unique, award-winning UI." Research fleet: a 6-agent
workflow (learning-science · award-UI craft · flashcard UX · AI-demo · Awwwards
benchmark → adversarial synthesis) produced a binding design spec; a subagent built
the AI marquee end-to-end.

**The concept — PROVEN.** One idea unifies the product: *a study instrument that
refuses to show a number, or an answer, it can't prove.* Identity is carried by
GEOMETRY (confidence-interval bands, the turnstile ⊢, a proof rail) + TEXTURE (a
hatch = "not yet proven") + NOTATION (mono for logic/numerals), never the accent hue
(which inherits Anki's arbitrary theme in-app). This fuses the existing honesty
discipline + oracle-verified AI into a visual language.

**Design system (`ts/lib/lsat/theme.scss`).** Added `--lsat-mono` (logic + numerals),
`--lsat-hatch` (abstain texture), `--lsat-rail`/`--lsat-graph` (proof gutter +
graph-paper canvas), semantic elevation tokens; reserved the gradient for
"proven/earned" only; fixed `--lsat-fg-faint` to ≥4.5:1 (was ~2.6:1, below AA).

**Dashboard main page** (`DashboardView.svelte`, `lsat-dashboard/+page.svelte`).
Re-ordered per Feedback Intervention Theory (leading with ego-scores can HARM): now
**proof-header hero** (premises ⊢ honest claim on graph paper; turnstile watermark;
retired the gradient banner + radial blobs) → **DO NEXT** primacy band
(`NextAction.svelte` — the one highest-yield action + reason; owed confident-wrong
retests rank #1 via hypercorrection) → **Oracle Proof Theater** (AI marquee) →
**Where you stand** (three scores rebuilt as `IntervalBand.svelte` confidence bands
with a point tick + CI span + a one-shot "ink-in" reveal; abstention is a hatched
"earning evidence" meter, not a broken em-dash). De-gradiented all numerals to solid
tabular mono.

**Flashcard/study experience** (`StudyItem.svelte`). The signature learning move: a
confidence × correctness **2×2 reveal** — a *sure + wrong* miss gets the
hypercorrection frame ("the highest-value fix"), a *guess + correct* gets a
"skill or luck? prove it →" nudge into an Evil Twin (never rewards luck, never
punishes a miss). Keyboard access (1-5/A-E pick, 1/2/3 confidence, Enter advances);
chosen answer stays prominent pre-reveal without leaking correctness.

**Meaningful AI feature, demo-ready (`OracleProofTheater.svelte` + backend).** A
recorded LLM draft of a chain derivation is checked **live, offline, step-by-step**
by the real decision procedure — on the planted hallucination the verdict flips to
"✗ does not follow — blocked" with the oracle's reason, then the oracle proves the
continuation. "Watch the AI get overruled." Verdicts are computed at request time by
the same `verify_worked_example`/`entails` code the tests exercise (not baked);
`theater_scenarios()` self-test **76/76 PASS** proves non-bakedness. Mounted at the
top of the dashboard (desktop + mobile Progress tab). A shared `ProvenanceBadge`
(Proven / Grounded / Not-yet-proven) now unifies the trust language across the
theater, Worked Example, and Evil Twin.

**Verification (all green).** `svelte-check` 1309 files **0 errors / 0 warnings**;
real `vite build` passes (production bundle incl. the theater); `eslint` clean;
**`make eval` GATE OK** (worked_example + evil_twin gates unaffected: 0 false-passes);
backend smoke on empty + seeded collections; the `ENDPOINTS ⊆ _HANDLERS` guard passes
with `lsatOracleTheater`. All motion is transform/opacity + `prefers-reduced-motion`
guarded; AA contrast; keyboard + aria-live throughout.

### 2026-07-02 — LSAT dashboard is the home screen + first-run content (debug)

**Requirement (new directive).** "The LSAT dashboard and flashcards are simply
broken. Replace the Anki screen with the LSAT dashboard, then deploy subagents to
debug." Deployed 3 parallel debug subagents (Rust/proto/build · dashboard frontend ·
flashcards/reviewer) + independent verification.

**Diagnosis — no code-level crash found in any layer:**
- **Build:** `cargo check --workspace` passes (52s). The isolated `cargo check -p
  anki` tokio `io-util` failure is a feature-unification artifact (a dev-dep enables
  it), NOT the real build — confirmed by the workspace check + 148 passing scheduler/
  today/points_at_stake tests. The web `vite build` also passes (emits
  `lsat-dashboard/_page.svelte.js`).
- **Rust/proto/scheduler:** proto ↔ Rust service ↔ generated Python/TS backend ↔
  `pylib/anki/scheduler/base.py` fully consistent (no stale codegen, no regen
  needed). `points_at_stake` is additive/read-only; the desktop reviewer uses the
  standard Anki queue. `stats/today.rs` had been reverted (no diff).
- **Flashcards:** the `LSAT Item` template HTML/JS, the `__LSAT_QTYPES_JSON__`
  injection, the `lsatAnswer`/`lsatClassify`/`lsatTrap` pycmd routing, grading, and
  the in-place template migration all verified correct end-to-end.
- **Backend data:** `dashboard_data.build()` + `api.next_item`/`submit_answer` work
  on BOTH an empty and a seeded collection (empty → abstaining scores + locked
  insights, which the frontend guards). `lsatDashboardData` endpoint is registered;
  the route loader + `pairing_authorized` path are correct; DashboardView + children
  guard every null/locked case.

**Concrete root-cause bug found (dashboard 403) + the experiential causes + fixes.**
The dashboard-frontend subagent SSR-rendered DashboardView + all 15 child components
across 5 data states (empty → maximal) with zero crashes — the render path is not
broken. The real defect is **serving/auth**: the LSAT dashboard was a buried
`QDialog` using the api-access `LSAT_DASHBOARD` webview kind (which injects the
bearer token), so it worked; but the correct "home screen" migration loads it into
the **MAIN** window webview, which is *deliberately excluded* from the api-access
allowlist (it also renders untrusted card JS) and therefore never sends the
`Authorization: Bearer` header. `lsat_dashboard_data` gated on `pairing_authorized()`
→ **HTTP 403** → the `+page.ts` loader throws → blank "broken" dashboard. Plus the
experiential cause: a fresh profile had **no LSAT decks** (manual seeding), so
flashcards appeared absent. Fixes:

0. **`qt/aqt/lsat_web.py::pairing_authorized`** — the bearer token is only the auth
   layer for **LAN-bound** mode (`ANKI_API_HOST=0.0.0.0`), where mediasrv's
   `handle_request` host/origin gate is bypassed for phone pairing. In normal
   **localhost** mode that gate already rejects any non-local host/origin, so a
   same-origin desktop request (incl. the MAIN-webview home screen) is already
   authenticated. Now: accept the token when present, else authorize only when NOT
   LAN-exposed. This makes the home dashboard render while keeping phone pairing
   token-locked (verified: localhost→OK w/ or w/o token; LAN→token required). NOT
   done: adding MAIN to the api-access allowlist (that would give untrusted card JS
   authenticated backend access — a security regression).

Fixes in `qt/aqt/main.py`:
1. **The LSAT dashboard is now the home screen.** New `lsatHome` main-window state
   (`_lsatHomeState` loads the `lsat-dashboard` SvelteKit page into the main
   webview); collection-load lands there instead of `deckBrowser`. Deck management
   stays one click away (toolbar "Decks" / the `d` shortcut); added `lsatHome` to
   `interactiveState()`. `Tools ▸ LSAT ▸ Dashboard` / Ctrl+Shift+L now returns to
   this home state instead of opening a redundant popup.
2. **First-run auto-seed** (`_lsat_autoseed_if_needed`): on first collection load,
   if `lsat:seeded` is unset, `lsat.seed.seed_deck` populates the starter decks
   (52 flashcards + 25 graded items) so the dashboard AND the flashcards have content
   immediately. Idempotent, guarded by the flag (never repeats, never re-adds decks a
   user removed), non-fatal on error.

**Verification.** `qt/aqt/{main,lsat_web,mediasrv}.py` py_compile; state wiring
consistent; the `pairing_authorized` decision table verified (localhost authorized
with/without token; LAN requires token); the dashboard render path SSR-tested crash-
free across 5 data states; `cargo check --workspace`, `vite build`, and
`svelte-check` (1305 files, 0/0) all pass; `dashboard_data.build` + study flow
exercised on empty + seeded collections. Net effect: opening the app lands on a
populated LSAT dashboard that authenticates and renders; decks/flashcards are one
click away (and auto-seeded on first run).

### 2026-07-02 — Spiky, defensible USPs: the "why buy this in the AI age" reposition

**Requirement (new directive).** "I need spikier points of view for most of the
features, especially the AI feature… effective and unique selling points so I can
sell for a profit. In an age where AI could create software, why would someone buy
what I made?" A 6-agent strategy workflow (a brutal VC bear case + 4 grounded POV
lenses + adversarial synthesis) stress-tested the thesis *before* editing.

**The reframe (what the bear case corrected).** "Trust-by-construction" is a seller's
virtue, not a buyer's need. The wedge is the **outcome verification makes safe**: the
*proven truth about the student's own test* — which points they leak under the clock,
which wins were luck, which misses were confident misconceptions — with AI quarantined
behind a proof-checker. The afternoon-AI-app **is** the confidently-wrong tier this
product is the inverse of ("ask an LLM to build the checker and it returns PASS").
Two corrections the bear case landed on our own code, both now fixed:
1. On the oracle slice the LLM was *decorative* (BFS already authored the proof). →
   Built **Evil Twins**, where LLM generation is genuinely load-bearing (targets +
   freshens) while the oracle still proves every answer.
2. `client.py` pinned the moving alias `claude-3-5-sonnet-latest`. → Pinned a concrete
   model, record the API-resolved id on every gated result, re-gate on change.

**Shipped (all tested to `GATE OK`):**
- **Evil Twins** (`lsat/evil_twin.py`, `eval/evil_twin.py`) — oracle-proven
  "skill or luck?" discrimination twins: a minimal edit flips the answer; the oracle
  (`quantifier.classify` / `conditional_chain.entails`) enumerates + proves every
  twin, the LLM only does logically-inert targeting + noun choice, fail-closed.
  Gate: 47 curated twins + 3,500+ fuzz flips, **0 mislabels** vs an *independent*
  oracle, malicious-drafter-safe. Reachable: Logic-tab **Skill or luck?** drill
  (`EvilTwinDrill.svelte`) + full api/server/mediasrv/client wiring.
- **Proof Receipt** on worked examples — `WorkedExampleDrill.svelte` now shows a
  per-step "✓ verified" + a provenance badge (**AI-drafted → oracle-verified** /
  **AI draft rejected → oracle-derived**) + method footer; data threaded from
  `worked_example.faded_drill`. The 30-second "can't lie" demo.
- **Blind-Review Delta = measured** — `lsat/blind_review.py` gains a paired bootstrap
  CI on the per-skill timed-vs-untimed gap (local, no `eval` dep) and only fires the
  pacing headline when the CI excludes 0 (the "points you leak" number, on the
  student's own answers).
- **Model nutrition label** — `lsat/ai/client.py` `DEFAULT_MODEL` (pinned, never
  `-latest`) + `nutrition_label()`; `eval/card_check.py` records `model_used`
  (surfaced in the report line).
- **Copy repositioned** — `Speedrun_AI_Features.md` + `README-lsat.md` lead with the
  wedge + tagline, a **Spike** one-liner per feature, a dedicated AI-flagship
  section, and **tiered assurance** (proof only where a decision procedure exists;
  grounded-gold + abstain elsewhere — the "provably correct AI" blanket claim is
  explicitly cut). `research/ai-features-for-faster-prep.md` #1 marked shipped.

**Verification.** New module self-tests: `evil_twin` 25/25, `blind_review` (paired-CI
checks) BLIND_OK, `worked_example` 46/46. `make eval` → **GATE OK** (both new hard
gates green; card_check now prints `model=…`). `ruff`/`mypy` clean on new files;
`svelte-check` 1305 files 0/0; `eslint` clean; server import guard passes. Honesty
held: no synthetic "+X points" in any pitch; every efficacy arm stays report-only.

### 2026-07-02 — AI feature SHIPPED: Oracle-Verified Faded Worked Examples (research #1)

**Requirement (new directive).** "Add an AI feature using your research. Test the
feature repeatedly until ready for production." Built research feature #1 — the
top-ranked, lowest-residual-risk AI feature from
`research/ai-features-for-faster-prep.md` — because its correctness check is a
*proof*, so the safety-critical path is fully testable to a hard gate offline.

**What it is — the "generate-with-a-proof" pattern.** For a multi-arrow
conditional-chain item, an LLM may *draft* a step-by-step derivation, but the
exact material-entailment oracle (`lsat.conditional_chain.entails`) **re-derives
every step and BLOCKS the example unless all steps verify**. A hallucinated
inference cannot pass: it fails entailment (or cites a premise that does not
license the step) and the whole example is withheld. Correctness never rests on
the LLM; with AI off the feature serves the deterministic oracle-derived proof.

**Code.**
- `lsat/worked_example.py` — `verify_worked_example` (the oracle GATE),
  `build_worked_example` (deterministic oracle-derived floor), `faded_variants` +
  `grade_fill` (backward fading), `draft_and_verify` (LLM drafts → oracle verifies
  → degrades to deterministic on `LLMUnavailable`/blocked/garbled), template
  `render_steps` narration + fail-closed `narrate`, and the served-drill surface
  `faded_drill` / `grade_move` / `worked_example_ids`.
- `eval/worked_example.py` — a **HARD gate** + `WORKED_STEP_FALSE_PASS_MAX = 0.0`
  in `eval/config.py`; registered in `eval/run.py`.
- Reachable end-to-end: `lsat/api.py` (`worked_example_drill` / `submit_worked_step`
  + `ENDPOINTS`), `lsat/server/app.py` (`_HANDLERS`, passes the import guard),
  `qt/aqt/lsat_web.py` + `qt/aqt/mediasrv.py` (desktop mediasrv routes),
  `ts/lib/lsat/client.ts` + `types.ts`, and a new `WorkedExampleDrill.svelte`
  wired into the Logic tab of `ts/routes/lsat-mobile/+page.svelte`.

**Honesty posture (per the red-team).** Ships AI-on but oracle-decided;
pre-generatable/offline; the shipping narration is **template-only** (from the
proven structure — no free prose), with the optional LLM rephrase fail-closed and
never touching correctness. The equal-time learning claim is a **report-only**
synthetic arm (disclosed `GAIN`/`COST`), not evidence — real learners settle the
magnitude, exactly as the discipline requires.

**Verification (tested repeatedly to production).**
- Module self-test: **46/46** checks (valid build round-trips; does-not-follow
  abstains; the gate blocks empty/forged/truncated/affirming-consequent/garbage
  derivations; valid AI draft verified & served; malicious/garbled/offline drafts
  all degrade to the *correct* deterministic proof; fading + oracle-graded fill;
  JSON-safe served-drill surface).
- Eval HARD gate (in `make eval`): **planted false-pass 0/20, fuzz false-pass
  0/3014 accepted, valid-walk coverage 3000/3000** (proves the gate accepts every
  genuine proof yet never blesses a non-entailed goal — cross-checked against the
  independent `entails` oracle), round-trip + does-not-follow-abstain +
  malicious-safe all True. Report arm: faded 0.572 vs worked 0.516 vs solve 0.419
  at equal 900s; faded−worked +0.056 (95% CI +0.050..+0.061).
- **`make eval` → GATE OK** (all hard gates pass with the new gate integrated).
- End-to-end server path (temp collection): drill → submit correct move → graded
  correct (reaches the goal literal, surfaces the note) → wrong move graded false
  → `skill.conditional_logic` events logged (feeds mastery/fluency).
- Lint/type: `ruff check` + `ruff format` clean; `mypy` clean on the new files;
  `svelte-check` 1304 files 0/0; `eslint` clean. Server import guard
  (`set(ENDPOINTS) ⊆ set(_HANDLERS)`) passes.
- Pre-existing (untracked, unrelated) `mypy` nits in `lsat/triage.py` +
  `lsat/growth.py` are out of scope and untouched.

### 2026-07-02 — Research: AI features for faster LSAT prep (deliverable, not shipped code)

**Requirement (new directive).** "Deploy subagents to research AI features to add to
the software. What AI features will help LSAT candidates prepare *faster*? Write up your
research after looping for an hour." Research-and-write-up task; **no product code was
changed** — the deliverable is `research/ai-features-for-faster-prep.md`.

**Method (multi-wave subagent loop).** Wave 1: broad fan-out over nine AI-feature areas,
critiqued by a four-lens panel (cognitive scientist · LSAT coach · AI/ML engineer ·
student-advocate) and ranked `prep-speed × feasibility × honesty`. Wave 2: four
code-grounded deep-dives (competitive landscape · honest speed quantification with cited
effect sizes · adversarial red-team + residual-risk ranking · build roadmap + the
load-bearing unlock). Wave 3: a completeness critic that verified the load-bearing code
claims and found real defects; all five top fixes applied.

**Findings.** Ranked top-6 AI features, all sharing one shape — **AI as a constrained
transform over authoritative artifacts, never an authority** (generate-with-a-proof /
classify-onto-closed-set / point-at-verbatim-span / tie-break-deterministic-ranking).
#1 Oracle-verified faded worked examples is safest *and* the only feature defensible on
speed (novices, formal-logic LR); #2/#6 are safe allocation aids (no borrowable effect
size); #3/#5 are the risky free-text graders → **ship AI-off by default**. Honest ceiling
is **single-digit scaled points**, every magnitude a borrowed prior awaiting an equal-time
bootstrap-CI arm.

**The one load-bearing unlock surfaced:** `eval/leakage.py::_semantic_sim` returns `None`
unconditionally — the copyright/originality gate is **lexical-only**, which disqualifies
generating original RC prose (a synonymized paraphrase evades all three lexical signals).
Wiring an offline embedder (hash-pinned MiniLM, build-time only, separately-calibrated
threshold, fail-loud when absent) is the single change that unlocks safe RC generation.
Two honesty gaps the critic caught and the doc now records: the checker's false-pass gate
floor (1/50 = 2%) **equals** its ceiling (`CHECKER_FALSE_PASS_MAX`), so it can only pass on
an observed-zero sample too small to bound the tail; and `ClaudeClient` pins the **moving
alias** `claude-3-5-sonnet-latest`, silently voiding any gated-checker guarantee on a
provider model bump (fix: dated snapshots + re-gate on bump).

**Verification.** Write-up self-consistent (composite ranking monotonic; residual-risk vs
composite axes explicitly reconciled); all load-bearing code claims verified against the
actual files (`checker.py`, `gold_set.py`, `leakage.py`, `client.py`, `config.py`). No
code/eval changes → no `make eval` delta.

### 2026-07-02 — Consolidation: fewer, prominent features + premade decks loadable

**Requirement (new directive).** "Features are subtle / hard to demonstrate — condense
to fewer, prominent features; revise the proposals (keep the research); confirm +
upgrade the premade decks." Two inventory subagents mapped the full surface + all
proposals first.

**Root cause of "subtle."** (1) The premade decks (`lsat/seed.py`) were **CLI-only —
never called from the app**, so a fresh profile had NO LSAT decks → nothing to
study, empty scores, dark panels. (2) The dashboard rendered **nine diagnostic tiles
as ghost placeholders** ("not enough evidence yet") — a wall of empty cards. (3) Six
flat LSAT items cluttered the Tools menu. (4) Two out-of-sync feature-naming systems
(`A1–D3` spec vs the `K/F1–F5/H` + rounds 2-4 debate scheme).

**Fixes.**
- **Decks now load in-app.** New `Tools ▸ LSAT ▸ Load Starter Decks` action
  (`onLsatSeedDecks`, idempotent) + the LSAT Dashboard offers to seed on first open.
  A fresh profile can now populate the four decks in one click → every feature has
  content. (`qt/aqt/main.py`.)
- **Dashboard condensed to prominence.** "How you get questions wrong" now renders
  ONLY the diagnostics you've *earned* (each present one is prominent) and folds the
  rest into a single honest "N more unlock as you study: …" strip — replacing nine
  ghost cards. Analysis engines unchanged; presentation only. (`DashboardView.svelte`,
  svelte-check 1303/0/0.)
- **Menu condensed.** The 5 flat LSAT Tools entries → one **"LSAT" submenu**
  (Dashboard / Load Starter Decks / Study on Phone up top; Study Mode / Exam Date /
  Study Plan below a separator).
- **Proposals revised to 5 headline features** (`Speedrun_AI_Features.md` rewritten
  from 12 `A1–D3` sub-features to five prominent, demonstrable headliners — decks+study,
  the drill suite, the confidence/misconception engine + Rust queue, the section
  runner + execution diagnostics, and the three honest scores — every old id + debate
  winner folded under one, all commitments/ablation/grading-coverage preserved).
  README-lsat.md + research/README.md now lead with the same five. **Research corpus
  (Speedrun_Research_Support.md, research/ memos + transcripts, docs/research) left
  intact** per the directive.
- **Decks expanded + made valuable.** The graded practice deck grew **9 → 25
  original items** covering the high-frequency LR types (weaken / strengthen /
  necessary + sufficient assumption / flaw [causal, sampling, equivocation,
  composition, nec-suf] / must-be-true / principle / parallel / method / paradox)
  + RC (main-point + structure), each with per-distractor trap labels and a spread
  of difficulties. Every new item's single correct answer was justified
  (mini-autopsy) and reviewed; the conditional/quantifier items were **machine-verified
  against the shipped `conditional_chain` / `quantifier` model-checkers**. (52
  flashcards unchanged.) All original — no LSAC copying.

**Demoability proof (the point of all this).** On a temp collection: seed → answer
the 25 practice items (timed) + an 8-item blind-review pass → the **Performance
score becomes available** and **7 of 9 diagnostics light up** (misconceptions,
traps, gap-map, calibration, choke, rush, time-leak); only fluency + fatigue remain
in the single "unlocks as you study" strip. Before this work a fresh profile showed
nothing at all.

**Verify:** `main.py` py_compile OK; `seed_deck` → 52 cards + 25 items / 4 decks;
25/25 items structurally valid (5 choices, valid key/skills/traps); ruff clean;
svelte-check 1303/0/0; eslint clean; `make eval` GATE OK (unaffected).

## Cumulative scorecard (whole run)

**Research → features:** four cited, 4-lens × 2-round debates
([`DECISION-round2`](../research/debate/DECISION-round2.md) /
[`-round3`](../research/debate/DECISION-round3.md) /
[`-round4`](../research/debate/DECISION-round4.md)) over ~90 proposals →
**14 features shipped** end-to-end, each behind a measured `eval/` arm at equal
study time with a bootstrap CI:
- *Round 2 (6):* Paired Choke-Index CI, Elaborated Contrast Card, Exam-Day
  Retrievability Targeting, Fatigue Curve, If-Then Study Plan, Conditional
  Translation Drill.
- *Round 3 (4):* Quantifier Reasoning Suite (Venn-model-checker-proved),
  Mastery-Growth Panel (CI-gated, hard gate), Rush-Error Detector (hard gate),
  Time-Leak Diagnostic.
- *Round 4 (4):* Stem-Polarity Micro-Drill, Necessary/Sufficient Discrimination,
  **Timed Section Runner + First-Instinct Ledger** (rank-1, hard gate),
  Conditional-Chain Trainer (exact-entailment grader).

**Honesty discipline held throughout:** every learning claim is a measured arm
(CI excludes 0 → ship; includes 0 → reported as unproven); diagnostics make no
learning claim; grading fails closed; two features (**RC-Judgment**, **Faded-Flaw
Ladder**) were *deferred with written reports* because they need human-calibrated
content — not shipped on AI-authored labels.

**Correctness:** ~6 adversarial-review cycles, every confirmed finding fixed —
incl. the growth difficulty-mix false-direction (HIGH), the conditional parser's
false fail-closed claim, quantifier cap-3 adequacy (now a cap-differential guard),
the chain grader's reachability-incompleteness (→ exact material entailment), and
section-runner fail-closed/no-leak. Independent higher-cap oracles back the
model-checkers.

**UI/UX:** a signature design language + a judge-panel-selected mobile **Drill
Launcher** redesign (scannable grouped picker, a11y-complete). **Slimmed** the
working tree by ~148 MB (regenerable `mobile/` artifacts).

**Final bill of health:** `make eval` **GATE OK** (9 hard gates + report arms) ·
all engine self-tests green · `SERVER_OK` (19 PWA endpoints, drift-guarded) ·
svelte-check **1303 files 0/0** · eslint + ruff clean · `cargo test -p anki`
points_at_stake 8/8. *Environment limit (unchanged):* full `just build`/`just
check` + the Rust→Python bridge rebuild need an online JS registry; mitigated with
`cargo test`, `out/pyenv`, and cached-`node_modules` svelte-check/eslint.

---

### 2026-07-02 — FINAL dead-code cleanup / repo-slimming pass

**Requirement.** The goal's explicit last step: "clean up dead code after you fully
finish improving the software, making the repository as slim as possible." Run only
after the improvement + review phases were complete.

**What (conservative — remove only the provably-dead + the regenerable).**
- **Dead code:** the whole `lsat/`+`eval/` tree is clean under `ruff --select
  F401,F811,F841` (unused imports / redefinitions / unused vars); the only hit was
  one leftover self-test assignment (`lsat/conditional.py` `p = parse_conditional(...)`
  never read) — removed. A reference scan found **no unreferenced Python module**
  (all 30+ wired via api/dashboard/eval) and **no orphaned Svelte component** (all 28
  referenced). No `*.orig/.bak/.rej/.swp/.pyc/.DS_Store` strays.
- **Slimming:** `mobile/` (the Capacitor Android PWA wrapper) held **148 MB** of
  `node_modules/` (123 MB) + generated `android/` (25 MB) — both explicitly listed
  in `mobile/.gitignore` as regenerable ("regenerate with `npx cap add android`") and
  neither git-tracked. Removed them; the source (`capacitor.config.ts`, `package.json`,
  `www/`, `resources/icon.svg`, README) is kept. `mobile/` 149 MB → **232 KB**.
- **Left intact (correctly):** the active, gitignored build caches `out/` (6.5 G),
  `target/` (2.1 G), root `node_modules/` (474 M) — regenerable but needed to
  build/run; deleting them isn't "slimming the repo," just forcing a rebuild. Also
  left the ambiguous-provenance root `package-lock.json` (small; deleting a lock file
  is a build-affecting action better surfaced than silently done).

**Verify (nothing broke):** `lsat.conditional` self-test green, `ruff` clean,
`make eval` **GATE OK**, `SERVER_OK`, svelte-check **1303 files 0/0**. The earlier
one-off (a stray 55 MB `anki.git/` bare mirror) was already removed.

### 2026-07-02 — Adversarial review of #17/#22/redesign → 3 fixes (fail-closed + a11y)

**Requirement.** Honesty discipline + "frequently debug." A read-only review of the
newest surfaces (section runner, chain drill, Drill Launcher). **Confirmed clean:**
no mid-section answer leak (server grades raw choices; only the aggregate ledger
returns), timer/double-submit safe, dwell correct, the exact chain grader correct,
reachability **sound over 200,000 trials (0 over-claims)**, all six drills mount,
focus/aria clean, recency never fabricates a performance number. Three fixes:

1. **`submit_section_attempt` wasn't actually fail-closed** — `int(dwell_ms)` was
   unguarded, so a crafted `dwell_ms: "abc"`/`[1]` raised instead of degrading →
   added a `_safe_int` coercion (verified: 5 malformed values now handled, no
   crash). Also hardened `_item_correct_letter` to catch a missing field.
2. **`drillProgress.read()` could throw on a corrupted `"null"` storage value**
   (`null[id]` → TypeError, crashing the Logic launcher render) → coerce any
   non-object to `{}` so the "never throw, degrade to New" contract holds for all
   stored values (verified in node).
3. **Per-second `aria-live` countdown** flooded the screen-reader queue → dropped
   `aria-live`, kept a static label.

Both #1/#2 were reachable only by crafted/corrupted input (server try/except +
finite-int client mean no live crash), but fixed so the fail-closed / never-throw
contracts actually hold. **Verify:** section flow no-leak intact, SERVER_OK,
svelte-check 1303/0/0, eslint clean, ruff clean.

### 2026-07-02 — UI/UX: Logic-tab "Drill Launcher" redesign + #22 Conditional-Chain drill

**Requirement.** The goal's explicit "make the software look creative and unique
(UI/UX via subagents)" + DECISION-round4 #22 (the top deferred *deterministic*
winner). The Logic tab had grown to a cramped 5-segment control; and #22 fills the
gap the single-conditional drill abstains on (≥3-arrow chains).

**Logic-tab redesign (judge-panel workflow → winner implemented).** Ran a
3-proposal design judge-panel (`lsat-logic-tab-redesign` workflow); the winner
("Drill Launcher", 8.8) replaced the cramped segmented control with a **scannable
grouped picker**: full-width cards grouped CONDITIONALS / QUANTIFIERS / QUESTION
TACTICS, each with an icon + one-line "what it trains" + an optional per-device
**recency chip** (localStorage, degrades to "New", strictly recency-worded — no
fabricated mastery number). New `ts/lib/lsat/DrillPicker.svelte` + `drillProgress.ts`;
the mobile page mounts the same five (now six) drills gated on a selected id, with
real focus management (focus → back button on open, → launching card on close),
`<nav>`/`<section>`/`<h3>` semantics, ≥44px targets, `--lsat-ring` focus, and
reduced-motion. This also makes the tab **scale** — a 6th drill is one more card,
not a narrower tab.

**#22 Conditional-Chain Trainer — `lsat/conditional_chain.py`.** Present a 3+ arrow
chain ("If A then B; if B then C; …") + a candidate inference; judge **must-follow /
does-not-follow** (transitive chaining + contrapositive vs affirming-the-consequent /
denying-the-antecedent). Structured implications rendered to prose (no fragile
parsing). **Graded by exact material entailment** (truth-table) — *complete*, unlike
a pure reachability check (which I found misses tautological-consequent + vacuous
cases: a real 29/500 discrepancy that forced the exact grader). Reachability is kept
as the human-explainable chaining intuition and **proven sound** (0 over-claims /
500 random chains). Fails closed.
- Verify: `lsat.conditional_chain` **21/21** (exact grader == curated; reachability
  sound; both verdicts covered; fail-closed on bad id/prefix/verdict). End-to-end
  API probe green (no leak, cycles, logs `skill.conditional_logic`).
- Eval `eval/conditional_chain.py` (report): drill−generic **+0.112** (95% CI
  +0.105..+0.119, finite-bank noise). Ships (CI excludes 0).
- UI: `ChainDrill.svelte` + a "Chains" card in the launcher's CONDITIONALS group.

**Verify:** 19 PWA endpoints (server guard 19==19), svelte-check **1303 files 0/0**,
eslint clean, `make eval` **GATE OK**.

### 2026-07-02 — Adversarial review of the round-4 drills → 6 findings fixed

**Requirement.** Honesty discipline + "frequently debug." A read-only adversarial
subagent (whose CPU-heavy probes were orphaned by the power interruption, then
finalized from analysis) audited `lsat/stem_polarity.py` + `lsat/assumption_discrimination.py`.
**Confirmed the gravest risk clean:** the necessary/sufficient formalization is
logically correct and never emits a wrong cell. Six lesser findings, all fixed:

1. **`_LEAST_RE` fired on "at least"** (a quantifier, not the LEAST inversion) →
   tightened to `(?<!at )\bleast\b`; added an adversarial test.
2. **The new negation pattern fired on "not only … but"** (a benign intensifier) →
   added a `(?!\s+only)` guard; test added.
3. **The self-test's entailment cross-check is a logical tautology** of the
   negation test (`P∧¬A⊨¬C ⟺ P∧C⊨A`), so it gave zero *independent* assurance →
   relabeled it a consistency check and documented that the **higher-cap oracle
   regression** is the real independent guard.
4. **An out-of-fragment quantifier crashed** (`ValueError`) instead of abstaining,
   contradicting the "fails closed outside the fragment" docstring → wrapped the
   fragment ops to abstain; added a `Statement("frobnicate", …)` fail-closed test.
5. **Cap-3 adequacy for the MOST fragment wasn't independently guarded in-repo**
   (quantifier's self-test checked at the same cap it runs at) → parameterized
   `classify(..., cap=)` and added a **cap-3-vs-cap-5 differential** over every
   curated + named verdict (incl. two-most-overlap / most-not-chain / most→some).
   Verdicts identical → cap-3 provably adequate.
6. **Eval "graded deterministically by lsat.X" oversold** what the arm exercises
   (it's a synthetic IRT sim, not routed through the real grader) → added an honest
   scope note to both eval docstrings (the grader's determinism is validated by the
   module self-test; the arm demonstrates the equal-time + CI *mechanism*).

**Verify:** quantifier **64/64** (incl. cap differential), stem_polarity **26/26**,
assumption_discrimination **24/24**, ruff clean. Both stem findings are
latent-robustness only (the drill serves index-bound curated stems, never arbitrary
input) but fixed for correctness of the public function.

### 2026-07-02 — Round-4 rank-1 shipped: Timed Section Runner + First-Instinct Ledger (#17)

**Requirement.** DECISION-round4 #17 (unanimous rank-1). Fills a real product gap:
every prior feature is per-item; none was full-section **test-day execution**.

**What.** A timed mini-section surface + the honest answer-change diagnostic.
- `lsat/answer_change.py` — the **First-Instinct Ledger**: the learner's OWN net
  wrong→right vs right→wrong answer changes with a bootstrap CI. It **refuses the
  folk "never change" rule and the population ~2:1 base rate** (applying either to
  an individual is the ecological fallacy), claims a direction only when the CI
  excludes 0, and abstains below a min-changes floor (7/7).
- `eval/answer_change.py` — **HARD gate**: on a 50/50 changer it fabricates a
  direction ≤0.06 of the time (measured 0.050); on a planted ~2:1 changer it
  recovers the direction ≥0.80 (measured 0.863 at a mature ~100-change volume) →
  ledger ON.
- `lsat/section_runner.py` + a new append-only **`LSAT SectionAttempt` notetype**
  (via `notetypes.py`; cards suspended, HLC-synced, idempotent registration, no
  proto/Rust/schema migration). Persists the per-question trajectory; reads it back
  for the ledger (7/7).
- **No-leak design (a correctness call I made):** a *timed* section must stay blind,
  so the client sends raw first/final **choices** and the **server grades** them
  into correctness on submit — verified A→B=wr, C→A=rw, unreached excluded, only the
  aggregate ledger returned.
- **Fixed two blockers a review surfaced:** `next_item` returns the same top card
  and never advances without a submit, so a section couldn't populate → added a
  batch `section_items` endpoint (distinct items, no answer); and added
  `lsat-section-runner` to mediasrv's SvelteKit page list so a hard refresh doesn't
  404.
- UI (subagent): `ts/routes/lsat-section-runner/` (LSAT-pace countdown, question
  palette, flag, answer-change + dwell capture, results = the ledger only), a
  "Start a timed section" mobile CTA, and a First-Instinct Ledger dashboard tile.

**Verify:** 17 endpoints (server guard 17==17), **SERVER_OK**, svelte-check **1300
files 0/0**, eslint clean, `make eval` **GATE OK** (answer_change hard gate passes).

### 2026-07-02 — Independent-oracle verification + hardening of the round-4 drills

**Requirement.** Honesty discipline + "frequently debug." Verified the two round-4
drills against an **independent** oracle (a battery interruption cut the review
subagent short, so I re-ran its highest-stakes checks directly).

**#5 (assumption) — no wrong cell, ever.** Built a brute-force truth-table oracle
that enumerates region-occupancy models at a **higher cardinality cap (6)** than
the shipped checker and computes necessary/sufficient from first principles. Over
the 8 curated items + ~3,100 random categorical arguments, `classify_assumption`
**never emits a cell that disagrees** — it either matches the oracle or
**conservatively abstains** (on degenerate arguments where the candidate already
contradicts or is entailed by the premises, so the negation test is ill-defined).
Baked this in as a self-test regression (independent oracle, 0 wrong cells over
254 classified random args → **23/23**) and made the abstain reason accurate
("candidate already contradicts or is entailed by the premises").

**#13 (stem-polarity) — high-precision negation.** The old `_NEGATION_RE` matched a
bare "not"/"is not" anywhere, so a stem whose *content* said "not" ("the plan will
not succeed") would false-positive as `negated`. Tightened it to reliable
task-negation phrasings only (the CANNOT-be-true family, "does not <task-verb>", a
negation inside the wh-clause); a genuinely-negated stem in another phrasing now
falls to `direct` (why the drill only serves curated stems). Added adversarial
self-tests proving content-"not" direct stems classify as `direct`, not `negated`
(**24/24**). `make eval` **GATE OK**.

### 2026-07-02 — Round-4 debate: 2 deterministic drills shipped (stem-polarity, nec/suff)

**Requirement.** A fourth four-lens debate (background workflow, 24 proposals),
ruled in `research/debate/DECISION-round4.md`. I shipped the two winners whose
correctness does **not** depend on human-calibrated content; the other two are
deferred with a report.

**#13 (rank 2) Stem-Polarity Micro-Drill — `lsat/stem_polarity.py`.** The
highest-frequency *careless* LR error: an EXCEPT/LEAST/negated stem inverts the
task and, under time pressure, the test-taker runs the prepotent (un-inverted)
task. A deterministic lexicon+regex classifier maps a stem to its polarity
(direct / EXCEPT / LEAST / negated) + the search instruction, **seeded from the
taxonomy `stem_cues`**, and **fails closed** on ambiguity (two conflicting
markers). Mechanism: automatizing the stem→task-set mapping makes the correct set
resource-independent, so it survives the fatigue moment (Monsell 2003; Shiffrin &
Schneider 1977; Logan 1988).
- Verify: `lsat.stem_polarity` **21/21** (every curated stem pinned to its polarity,
  all four polarities covered, ambiguous/empty stems abstain, grading fails closed).
  End-to-end API probe: serve→grade→event, no leak, cycles, logs `diction.except`.
- Eval `eval/stem_polarity.py` (report): drill−generic **+0.114** (95% CI
  +0.107..+0.122 — a realistic width, from a FINITE held-out bank with binomial
  noise, not the razor-thin deterministic mean the review flagged on quantifier);
  secondary **speeded +0.148** (the automatization payoff). Ships (CI excludes 0).
- UI: mobile Logic-tab "Stems" segment (the segmented control was generalized to N
  segments via a `--n` custom property); four token-guarded endpoints + standalone
  server handlers.

**#5 (rank 3) Necessary/Sufficient Discrimination Drill —
`lsat/assumption_discrimination.py`.** The most-confused LR distinction. The learner
sorts a candidate into necessary-only / sufficient-only / both / neither. The cell
is **derived, not authored**: it reuses the proven `lsat.quantifier` Venn
model-checker as an oracle — sufficient ⟺ `P+[A]` entails `C`; necessary ⟺ the LSAT
**negation test** (`P+[¬A]` makes `C` impossible) — with a gap-guard requiring the
argument to actually have a gap (`classify(P,C)==COULD_BE_EITHER`).
- Verify: `lsat.assumption_discrimination` **22/22** — every curated cell PROVEN by
  the model-checker AND cross-checked against the equivalent entailment form; all
  four cells covered; fails closed on a degenerate/incoherent argument. End-to-end
  API probe green (no leak, cycles, logs both assumption node ids).
- Eval `eval/assumption_discrimination.py` (report): four-way sort (chance 0.25)
  drill−generic **+0.102** (95% CI +0.095..+0.110). Ships (CI excludes 0).
- UI: mobile Logic-tab segment; endpoints + server handlers (guard now 15==15).

**Deferred with report (`DECISION-round4.md`):** #17 Timed Section Runner (Effort L
— new notetype + trajectory persistence; sequenced next) and #19 Faded Flaw Ladder
(needs human-authored flaw decompositions — the same content-calibration dependency
that keeps RC-Judgment off; see `docs/research/rc-judgment-staging.md`).

**Gate:** `make eval` **GATE OK** — 22 arms; both new drills report a CI excluding 0.

### 2026-07-02 — Adversarial review of the 4 round-3 features → fixed a HIGH honesty bug

**Requirement.** Honesty discipline + "frequently debug." A read-only adversarial
subagent stress-tested the round-3 backend (model-checker, growth, rush, triage).

**Headline (reassuring):** the **Venn model-checker is clean** — verdicts are
identical at cap 3/4/5/6 across all 14 curated items + 10 "most"-heavy variants
and an exhaustive 2-term sweep (888 verdicts); no false "valid" exists in scope.
The gravest risk (certifying a wrong logic rule as proven) does not occur.

**Finding 1 (HIGH, fixed).** The Mastery-Growth panel's difficulty-matching was
defeatable: a band with as few as **1** answer per window still counted, so on a
realistic ZPD easy→hard drift **with no real change** the tiny bands dominated the
count-weighted delta and fabricated "improved" — measured **10.7%** false-direction
vs the promised <5%. Worse, the HARD gate couldn't catch it (its synthetic data was
balanced single-band only). Fix: a **per-band floor** (`MIN_PER_BAND=5` in each
window, in both the point estimate and the bootstrap), a **material-effect margin**
(`MIN_DELTA=0.08` — claim a direction only when the delta is both material AND its
CI excludes 0, mirroring the rush gate), and `MIN_PER_WINDOW` 8→12 (the
proportion-difference bootstrap under-covers at 8). **Broadened `eval/growth.py`**
with a mix-drift arm so the gate now exercises the failure mode. Result:
mix-drift false-direction **0.000**, single-band **0.039**, detection **1.000**;
growth self-test **10/10** (incl. a Finding-1 regression); gate still PASS.

**Finding 3 (fixed).** Growth seeded its bootstrap with per-process `hash()` (salted
→ non-reproducible across app launches) → `zlib.crc32` (verified identical CI across
processes).

**Finding 4 (LOW, fixed).** `grade_validity`/`grade_negation` parsed only the
integer after `-`, so `grade_validity("qneg-2", …)` graded a *validity* item. Added
`_item_index` requiring the **exact `qval-`/`qneg-` prefix** → genuinely fails
closed (quantifier self-test **63/63**).

Rush, triage, the server guard, and eval gate/report classifications were all
confirmed clean. `make eval` **GATE OK**.

### 2026-07-02 — Round-3 debate: 4 new features shipped (quantifier, growth, rush, time-leak)

**Requirement.** Third four-lens learning-science debate (background workflow, 21
proposals over 8 under-served areas), ruled in `research/debate/DECISION-round3.md`.
All winners are pure Python + web + eval (no Rust/proto/schema) and obey the
honesty discipline.

**#1 (rank 1) Quantifier Reasoning Drill Suite — `lsat/quantifier.py`.** The merged
validity + negation drill for `skill.quantifier_logic`. A learner judges whether a
conclusion **must / cannot / could** follow from quantifier premises (attacking
illicit conversion, the undistributed middle, the two-`most` overlap), and picks
the exact negation of a statement (the traps: ¬all = *some-not* not *no*; ¬most =
*at most half*). **Correctness gate:** the curated verdict/negation tables are the
runtime source of truth, but a **bounded Venn-region model-checker** (`classify`,
`_is_negation`) independently *proves* every entry from first principles in the
self-test — a wrong table entry fails the suite. Grading fails **closed**.
- Verify: `lsat.quantifier` **61/61** (model-checker matches every curated verdict:
  Barbara, illicit conversion, two-most overlap, "most" doesn't chain, contradictions;
  negations proven exact complements + involutions; fail-closed on bad id/verdict).
  End-to-end API probe: serve→grade→event, no verdict/answer leak, answer slot
  rotates all 4 positions, events logged under `skill.quantifier_logic`.
- Eval `eval/quantifier.py` (report): drill−generic **+0.087** (95% CI +0.086..+0.088,
  excludes 0 → ship); secondary **speeded** edge **+0.101** > untimed (the
  automaticity payoff). Far-transfer arms ship OFF until their own CI clears.
- UI: mobile Logic-tab sub-control (Translate / Validity / Negation), reusing the
  drill surface; four token-guarded mediasrv + standalone-server endpoints.

**#2 (rank 2) Mastery-Growth Panel — `lsat/growth.py`.** The honest answer to the
forbidden "readiness/σ" number: a **self-referential**, per-skill early-vs-recent
accuracy delta (never a rank/percentile — Kluger & DeNisi). **Difficulty-matched**
(stratify by band + pool, so a difficulty-mix shift can't masquerade as progress)
and **CI-gated** (emit improved/slipped only when the bootstrap CI excludes 0, else
abstain). Routes each readout to a concrete next drill.
- Verify: `lsat.growth` **9/9** (detects true up/down with CI excluding 0;
  **false-direction rate 0.043 < 0.05** on true-no-change; abstains on
  non-overlapping bands and mix-only shifts).
- Eval `eval/growth.py` — **HARD gate**: false-direction 0.033 (≤0.05) AND detection
  0.938 (≥0.80) → **panel ON**. Wired into the dashboard (`growth` payload + a "Your
  progress" section).

**#3 (rank 3) Rush-Error Detector — `lsat/pacing.rush_errors`.** Flags a rush
pattern only when the learner's **fast** answers (under half their own careful
untimed pace) are **materially and significantly more wrong** than their non-fast
ones — an excess with a bootstrap CI excluding 0, never a raw fast-and-wrong count
(which carries the base error rate). Per-learner baseline, so a naturally
fast-and-accurate learner is never flagged. Diagnostic, non-punitive.
- Verify: `lsat.pacing` self-test extended (genuine rush pattern flags; fast misses
  that don't beat the slow rate do NOT; abstains without an untimed baseline).
- Eval `eval/rush.py` — **HARD gate**: planted-rush detection 0.870 (≥0.80);
  naturally-fast false-flag **0.013 (≤0.10) vs naive absolute-clock 0.860** → valid
  and beats naive. (Designing this exposed and fixed a real flaw: a count-based
  detector false-flagged 32% of fast-accurate learners; CI-gating the *excess* fixed it.)

**#5 (rank 5) Time-Leak Diagnostic — `lsat/triage.py`.** Reclaimable seconds = time
spent under the clock on items missed **even untimed** (a gap, not a pace problem;
a lone guess-confidence untimed miss doesn't count). Reported **with a bootstrap
CI**; strictly descriptive (time, never a promised score gain); leads with "need a
blind pass first" and returns ~0 for a learner who isn't time-pressured.
- Verify: `lsat.triage` **14/14** (real leak flagged with CI; true-leak-0 null → 0s;
  abstains without a blind pass; lone-guess misses excluded).
- Eval `eval/triage_leak.py` (report): recovers 58% of true wasted time (CI
  452–482s excludes 0), false-unwinnable **0.026 (≤0.05)**, true-leak-0 null **0.0s**.

**Also:** fixed a latent round-2 gap — the standalone `lsat/server/app.py` never
had the conditional endpoints (and would have missed the quantifier ones); added
all six handlers + an **import-time guard** (`set(ENDPOINTS) ⊆ set(_HANDLERS)`) so
the PWA server can't silently drift from the client contract again.

**Gate:** `make eval` **GATE OK** — hard gates now include `growth` + `rush`
alongside calibration/performance/score_map/choke_validity/leakage/card_check.

### 2026-07-02 — Adversarial-review fixes: conditional parser made genuinely fail-closed

**Requirement.** Honesty discipline (a false safety claim is a defect). A review of
the round-2 conditional code found the module's central promise — "hard-abstains on
anything it cannot confidently normalize" — was **false**: the greedy flat split
confidently **mis-parsed** natural conditionals (relative-clause universals "every
dog that is trained is calm", "if and only if" biconditionals, nested unless+if),
returning a wrong `sufficient → necessary` arrow. Production was protected only by
curation, not by the abstain mechanism the docstring credited.

**What.** `lsat/conditional.py`: added `_CLAUSE_AMBIGUOUS` — a captured clause that
still contains a connective (if/then/unless/and/or/iff) or a relative pronoun
(that/who/which/…) means the flat split can't be trusted → **abstain**. Corrected
the docstring to describe the real two-way guarantee. Hardened the self-test to
pin each curated sentence's **exact arrow** (not just `available`) and to assert
all 8 adversarial forms now **abstain**. Also fixed `lsat/api.py`: negative-index
injection in `submit_conditional` (`cond--1` graded a different sentence) and the
fixed per-sentence option slot (a repeat learner could memorize position → now
rotates by cycle). `lsat.conditional` **31/31**; `lsat.pacing`/api probes green.

### 2026-07-02 — Feature #19: Conditional Translation Drill engine — 6th winner

**Requirement:** DECISION-round2 #19 (trains `skill.conditional_logic`, the
taxonomy's highest-weight 0.9 cross-cutting LR primitive — today only tagged,
never drilled). Previously staged as Effort-L; I built the verifiable core.

**What.** `lsat/conditional.py`: a **deterministic** conditional-logic engine —
`parse_conditional` normalizes an English conditional (if/then, only-if, unless,
no/all/only, requires, sufficient/necessary-for) into its `sufficient → necessary`
arrow + contrapositive; `grade_conditional` grades a learner's identification.
**Fail-closed:** mis-grading would teach the *wrong* rule, so it recognizes only a
fixed phrasing table and **hard-abstains** on anything ambiguous (the caller shows
the worked answer instead of grading). The mis-teaching risk lives entirely in the
parser, which is **exhaustively unit-tested (20/20)** — incl. unless≡if-not,
only-if vs only, no/all/only, contrapositive, double-contrapositive, and abstain
cases — so it is safe.

**Eval.** `eval/conditional.py` (registered, report-only): equal-events drill vs
generic vs plain, held-out P(correct) on conditional-tagged LR items — **drill
0.767 vs generic 0.680, drill−generic +0.087 (95% CI [+0.086,+0.088]) → ship**
(larger than the exam-wide single-digit ceiling because it's the conditional
subset the drill directly targets; synthetic, explicit params). **Verified:**
parser 20/20; GATE OK; ruff clean.

**Now fully wired end-to-end (not staged):** a curated, parser-validated drill
set (`DRILL_SENTENCES`), `lsat.api.conditional_drill`/`submit_conditional` (serves
a "which clause is the sufficient condition?" tap from the non-negated subset —
exact-gradeable, no fuzzy matching — logs a `skill.conditional_logic` event),
token-guarded `lsatConditionalDrill`/`lsatSubmitConditional` mediasrv endpoints,
and a mobile **"Logic" tab** (`ts/lib/lsat/ConditionalDrill.svelte`) that reveals
the arrow + contrapositive after each tap (teaching the negated forms too). The
desktop reviewer card template remains the one staged piece. **Verified:** parser
22/22; API serve→grade→event→cycle end-to-end; endpoints 403 without the token;
svelte-check 0/0 (1290 files); eslint + ruff clean.

**All 6 round-2 winners now shipped with a measured eval arm** (5 with full UI;
#19 fully usable on mobile, desktop card template staged).

### 2026-07-02 — Feature #4: If-Then Study Plan (adherence) — 5th winner

**Requirement:** DECISION-round2 #4 (rank 2; the only winner addressing ADHERENCE
— the #1 real determinant of score gain, which no shipped feature touches).

**What.** A single implementation-intention plan ("If <cue>, then I will do N LSAT
cards") stored in config; adherence (active days / completed days / consecutive
missed / re-plan flag) is **inferred from the existing graded-event log** — no new
notetype, no new synced record, no new sync path. **Locked constraints honored:**
no streak counters, no loss-aversion, and a *neutral* re-plan nudge after ≥2 missed
days (never shaming). (`lsat/adherence.py`; **Tools → Set LSAT Study Plan…** in
`qt/aqt/main.py`; dashboard `adherence` payload.)

**Honest claim.** A behavioural adherence lift only — **no score claim** (any score
effect is just the mechanical value of extra practice, not double-counted).
`eval/adherence.py` (registered, report-only) is explicitly a **MECHANICS/plumbing
check, UNPROVEN until a live cohort**: planned-completion rate plan 0.66 vs no-plan
0.50, diff +0.159 (CI excludes 0, per an explicit implementation-intention lift
param) **with a guardrail** — accuracy-diff CI **includes 0 → no score
cannibalization**. **Verified:** adherence self-test all PASS (abstain-no-plan,
event-inferred completion, neutral lapse re-plan); GATE OK; main.py compiles; ruff
clean.

**5 of 6 round-2 winners now shipped** (#24, #13, #7, #10, #4). Only #19 Conditional
Translation Drill (Effort L, needs a reviewer card mode this offline env can't
exercise) remains a documented, staged winner.

### 2026-07-02 — Adversarial self-review of this session's code (+ fixes)

Ran 3 parallel adversarial reviewers over the code I added/changed this run. They
confirmed the bulk correct and surfaced **7 real issues, all now fixed**:

- **(perf regression, most important) HLC reconcile on the answer hot path.** The
  #22 fix (`_reconcile_hlc_baseline`) did a full `read_events` scan on **every**
  `append_event` → O(N) per answer / O(N²) per session (~250 ms/answer at 20k
  events, blowing the PRD §13 next-card budget). Fixed: reconcile only on the first
  mint per open collection, or when a sync is detected to have lowered the config
  baseline (`cfg < last-minted`); the common path is O(1). **Verified:** append
  latency now **flat ~14 ms** regardless of log size; the HLC non-regression +
  wrong-clock self-tests still pass. (`lsat/events.py`.)
- **(regression I introduced) `ruff --fix` re-broke `sync/validate.py`.** My
  import-sort auto-fix reordered `anki.cards` above `anki.collection`, re-triggering
  a namespace-package circular import (the #28 agent had deliberately ordered it).
  Fixed with `# isort: off/on` pinning + collection-first; re-running `ruff --fix`
  no longer reorders it. **Verified:** `sync/validate.py` → VALIDATION_OK (all 6
  scenarios incl. wrong-clock).
- **(honesty) choke_validity didn't test the operating floor.** It validated CI
  coverage at n≈50, but the product flagged at n=5 where percentile-bootstrap
  coverage is only ~0.82. Fixed: a *confident* flag now requires ≥
  `MIN_CONFIDENT_FLAG_ITEMS` (10) paired items (the estimate + CI still SHOW from
  n=5), and the eval validates coverage AT that floor (**0.92 ≥ 0.90**).
- **(honesty) exam_schedule eval simulated a metric-optimizing greedy, not the
  shipped heuristic.** Rewrote the deadline arm to rank by the exact shipped
  `exam_weight·(DR − projected_R)`; effect holds honestly (**+0.007**, null ties).
- **(honesty, minor) feedback eval equal-time rounding** (kcr got 1792 s vs 1800 s)
  → budget set to 1680 s (exact multiple of all arm costs); ef−kcr +0.007 holds.
  Plus a disclosure note that the null branch is reachable and CI-gated, and
  dropped an inaccurate "recency-weighted" claim from `fatigue.py`'s docstring.

**Verified:** `make eval` GATE OK; ruff check + format clean; 7 module self-tests +
`sync/validate.py` all pass.

### 2026-07-02 — Dead-code cleanup & repo slimming (final step)

Done **after** the improvement work, per the goal. Scoped to be safe (no upstream
Anki code touched, nothing that would break the build):

- **Removed `anki.git/` (55 MB)** — a stray *bare mirror of the user's own
  Speed-Run repo* (its `origin` = the same GitHub repo), untracked, referenced by
  nothing (not `origin`, not a git alternate/worktree, not the build). Verified
  the main repo has no `objects/info/alternates` first, so removal can't corrupt
  it; fully reversible (re-clonable from origin).
- **Removed all `__pycache__`** under `lsat/`, `eval/`, `sync/` (regenerable
  build artifacts).
- **Lint/format:** `ruff check --fix` removed 6 unused imports/vars + fixed
  import sorting across the new/edited modules; `ruff format` aligned 10 files;
  **`ruff check` + `ruff format --check` now pass clean** (matches `just check`'s
  Python fmt/lint step).

**Deliberately NOT done (a "too risky to auto-delete here" report):** static
dead-*module* elimination. The LSAT layer uses pervasive **lazy imports**
(`from lsat.x import y` inside functions), so a static reference scan produces
false "unused" positives (it flagged `events`/`taxonomy`/`grading` — all live —
as unreferenced). Deleting a module that is only lazily imported would break the
app, and this environment cannot run a full `just build`/app to confirm
reachability (the JS registry is offline — see the environment note). Every LSAT
module is in fact reachable from an entry point (a score model, an insight panel,
an eval arm, the AI pipeline, or a qt hook), so there is little true dead source
to remove. `mobile/node_modules` (123 MB) and the top-level `node_modules`/`out`
are regenerable build caches that **cannot be reinstalled offline**, so removing
them would break buildability here — left in place.

---

## Session scorecard (what shipped this run)

**Research → features (the debate deliverable).** Ran a 2nd 4-lens × 2-round
debate over 29 proposals ([`DECISION-round2.md`](../research/debate/DECISION-round2.md));
**5 of 6 winners shipped** end-to-end with measured `eval/` arms + UI: **#24**
Paired Choke-Index CI, **#13** Elaborated Contrast Card, **#7** Exam-Day
Retrievability Targeting (wired into the study queue via `select_zpd`), **#10**
Fatigue Curve, **#4** If-Then Study Plan (adherence, honest mechanics-only eval +
no-cannibalization guardrail). (#19 Conditional Drill: ruled winner, honestly
staged — Effort-L reviewer card mode this offline env can't exercise.)

**Improved existing features + correctness.** All **28 confirmed audit findings**
(multi-agent, adversarially verified) addressed — incl. the ablation equal-time
honesty bug, the leakage paraphrase-detection gap, PWA bearer-token auth, the
phase/session-mode wiring that makes Feature 4 reachable, honest-mastery filter,
k-fold weight leakage, sync robustness (append-only projection notes + HLC
non-regression), and the retrieval significance test (honest negative).

**Performance / engine.** `compute_memory` single-scan (543→126 ms), request-scoped
event/deck-node caches, a bench measurement-artifact fix, and the points-at-stake
Rust bulk-load (`cargo test` verified).

**UI/UX.** A distinctive, coherent design language (signature gradient, layered
shadows, type scale) anchored in `theme.scss` + shared primitives, then 4 parallel
design agents polished the mobile shell, study flow, insight panels (CI number
line, reliability diagram, 2×2 gap matrix, trap leaderboard, spectrum, fatigue
curve) and the desktop dashboard — all svelte-check 0/0 + eslint clean, both
light/dark, `prefers-reduced-motion` respected.

**Verification.** `make eval` GATE OK (6 hard gates + 6 report arms) · `make
ablation` +0.019 (honest) · all module self-tests pass · `cargo test -p anki`
points_at_stake 8/8 + today · svelte-check 0/0 (1289 files) · eslint + ruff clean.
**Environment limit:** full `just build`/`just check` and the Rust→Python bridge
rebuild are blocked by an offline JS registry, so the compiled-backend bench can't
reflect the Rust edit and TS wasn't built via `just` — mitigated with
`cargo test`, `out/pyenv` Python, and cached-`node_modules` svelte-check/eslint.

### 2026-07-02 — Feature #10: Fatigue Curve (time-on-task decay)

**Requirement:** DECISION-round2 #10 (new ground — no shipped signal captures
session position; F4's Choke Index measures per-item *pressure*, orthogonal).

**What.** `lsat/fatigue.py`: **no schema migration** — sessions are inferred from
the append-only event log's existing HLC wall timestamps (a >20-min gap starts a
new session); within each session, answers are binned by cumulative
minutes-on-task and reported as recency-weighted accuracy + median RT per bin with
an OLS "accuracy lost / 30 min" slope. Timed-only; abstains below floors (≥20
timed answers across ≥3 sessions). Wired: dashboard `fatigue` insight +
`FatigueCurve.svelte` panel in DashboardView.

**Honest claim.** It MEASURES a decrement; the diagnostic doesn't itself raise
scores. `eval/fatigue.py` (registered, report-only) checks the predictive claim:
does a fatigue-aware model beat position-blind on held-out within-session items?
**fatigue-aware AUC 0.651 vs blind 0.628, dAUC +0.024 (95% CI [+0.005,+0.041] ≥
0.02 threshold) → signal real.** **Verified:** fatigue self-test all PASS (session
inference, decay curve, RT rise, abstain floors); GATE OK; svelte-check 0/0.

**Feature scorecard:** 4 of 6 round-2 winners shipped with measured eval arms +
UI (#24, #13, #7, #10). The remaining two — #4 If-Then adherence (its claimed
benefit is explicitly UNPROVEN without a live cohort — a mechanics-only eval per
the ruling) and #19 Conditional Translation Drill (Effort L, needs a reviewer card
mode this offline environment can't exercise) — are documented ruled winners with
build specs in DECISION-round2, appropriately staged rather than shipped
half-wired. See the wrap-up report for the rationale.

### 2026-07-02 — UI/UX pass: a coherent, distinctive design language

**Requirement:** "make the software look creative and unique" (product/UX, PRD §8/§9).

**Anchor (me):** elevated the shared design system so polish propagates everywhere —
`theme.scss` now carries a distinctive identity (deep indigo→violet **signature
gradient** `--lsat-hero`, layered shadows/glow, a type scale, focus ring, motion
easing) while KEEPING Anki-var layering (desktop still matches Anki light/dark) and
all token names (nothing breaks); `Card.svelte` (gradient accent strip + hover
lift), `Bar.svelte` (gradient sheen fill), `ScoreCard.svelte` (display-scale,
tabular, gradient headline).

**4 parallel subagents**, each owning distinct files, verifying svelte-check 0/0 +
eslint, keeping every prop/data-flow unchanged (visual-only):
- **Mobile shell + study flow:** gradient app-mark header, a sliding segmented phase
  control, animated tab indicator; choice/confidence/trap interactions with
  status-coded feedback; the **ContrastCard** signature moment (credited │ "vs" pivot
  │ trap, icons, staggered rise-in).
- **Insight panels A:** ChokeMeter as a **CI number-line** (estimate dot + 95% band
  over a 0 reference), CalibrationDial reliability gauge, GapMap 2×2.
- **Insight panels B:** TrapBars ranked "leaderboard", FluencyBadges progression
  ladder, MisconceptionPanel proportional spectrum + re-test ledger, InsightCard
  calm ghost-chart empty state.
- **Desktop dashboard:** signature-gradient hero header + honest tagline, three-up
  score band, gradient section ticks, polished coverage panel + per-topic table.

**Also (me):** rendered the #7 **exam runway** strip in DashboardView (shared, so it
shows on desktop + the mobile Progress tab). All motion respects
`prefers-reduced-motion`; both light + dark work via tokens.

**Verified:** svelte-check **0 errors / 0 warnings (1288 files)**; eslint exit 0 on
all LSAT `.svelte`/`.ts`; dashboard payload JSON-safe end-to-end; Python eval GATE
OK and 8/8 module self-tests still pass (UI touched no Python).

### 2026-07-02 — Feature #7: Exam-Day Retrievability Targeting

**Requirement:** DECISION-round2 #7 (8.0, the only exam-DATE-aware winner). The
shipped queue/ZPD are blind to *when* the test is; this reallocates the same
review minutes toward being retrievable ON test day.

**What.** `lsat/exam_schedule.py`: a shared `exam_date` config; a deadline-adjusted
desired-retention ramp (floor 0.80 far out → 0.94 in the final ~3 weeks); an FSRS
power-forgetting-curve projection of each card's **exam-day** retrievability; and a
**consolidation queue** ranking cards whose projected exam-day R is below target by
`exam_weight·(target − projected_R)`, with a hard daily cap, flagging cards not due
again before the exam. **Abstains** (degrades to the normal queue) with no exam
date or thin FSRS state. Wired: dashboard payload `exam_schedule` summary
(`lsat/dashboard_data.py`, cheap — returns before scanning when no date) + a
**Tools → Set LSAT Exam Date…** action (`qt/aqt/main.py`).

**Honest claim.** A scheduling *reallocation*, ~single-digit points at most; can be
net-zero for a daily studier. `eval/exam_schedule.py` (registered, report-only):
equal-review-count sim — **deadline-aware 0.869 vs fixed-DR 0.863 weighted exam-day
retrievability, delta +0.006 (95% CI [+0.005,+0.006])**; **daily-studier null delta
+0.000** (ties, as predicted). **Verified:** exam_schedule self-test all PASS (DR
ramp, forgetting curve, abstains); dashboard payload carries it; GATE OK.

### 2026-07-02 — Feature #13 desktop parity

Rendered the Elaborated Contrast Card on the **desktop** reviewer too (the
`pycmd("lsatAnswer",…)` callback already returns the grade result with
`contrast`): added a `#lsat-contrast` two-column block + `showContrast()` + CSS to
the `LSAT Item` template. Now both desktop and mobile show the why-credited /
why-trap contrast on a miss. **Verified:** template builds, contains the block +
LR chips; import OK.

### 2026-07-02 — Audit fixes batch 5 (missing eval arms + sync robustness) — COMPLETE

All 28 confirmed audit findings are now addressed. This batch (delegated, reviewed):

- **#8 (HIGH) missing DECISION-mandated eval arms.** Added `eval/blind_review.py`
  (routing-validity: recovers the true pressure-vs-knowledge cause **0.93** of the
  time, 95% CI [0.91,0.95]; honest-mastery: dropping lucky timed wins improves
  held-out Brier **+0.0117** [0.009,0.014]) and a **`+zpd` arm** in the ablation
  interleaving secondary (**+0.022** [0.021,0.023]); B3 unchanged (+0.019). Also
  registered the new **`eval/feedback.py`** (Feature #13's 3-arm) in `eval/run.py`.
  All report-only; **GATE OK** holds.
- **#20/#21/#22 (MED) sync robustness.** (a) Readiness projections converted from a
  single clobber-prone config list to **append-only, id-keyed `LSAT Projection`
  notes** that set-union merge like the event log — the honesty-contract track
  record now survives multi-device sync. (b) `_reconcile_hlc_baseline` raises the
  HLC baseline to the max over the append-only event log before minting, so a
  config-LWW sync can **never regress** the baseline (preserving the wrong-clock
  guarantee). (c) Docs corrected: both logs are append-only set-union; no
  production record uses LWW; `resolve_lww` relabeled as the reusable primitive.
  (`lsat/models/projections.py`, `lsat/events.py`, `sync/README.md`,
  `README-lsat.md`.) **Verified:** projection-survival + HLC-non-regression
  self-tests pass (13 checks); GATE OK; blind_review/selection self-tests OK.

**Full-system checkpoint:** `make eval` GATE OK (6 gates + 5 report arms); 7/7
module self-tests pass; `cargo test -p anki` today+points_at_stake pass;
svelte-check 0/0 (1288 files); bench dashboard 150ms p50.

### 2026-07-02 — Feature #13: Elaborated Contrast Card (upgrades Feature 2)

**Requirement:** DECISION-round2 #13 (8.0, unanimous ship). Upgrades the shipped
Feature 2 one-tap why-wrong (KCR + a single trap tip) into true **elaborated
feedback**.

**What.** On a miss, a deterministic two-column contrast: LEFT a "why the credited
answer wins" clause keyed to the item's question type; RIGHT the trap family of the
letter the student picked + a one-line "minimal edit" (what would make that trap
correct) + the fixable-habit tip. **AI-off** (a fixed catalog, no model call at
feedback time), **gold-set-gated** (`validate_contrast_catalog` refuses a clause
that references a non-taxonomy node), and it **abstains** when nothing is
documented. (`lsat/contrast.py`; wired into `lsat/grading.py::grade_answer` →
`contrast` field on a miss; rendered by new `ts/lib/lsat/ContrastCard.svelte` in
`StudyItem.svelte`; `ts/lib/lsat/types.ts` `AnswerContrast`.)

**Honest claim.** ≤ a small (~single-digit) held-out gain over KCR at equal study
TIME, only if the eval CI excludes 0. New `eval/feedback.py` 3-arm equal-*time*
ablation (KR / KCR≈shipped-F2 / EF-contrast; EF costs more seconds so does fewer
items — penalized honestly): **ef 0.807 vs kcr 0.800 vs kr 0.788, ef−kcr +0.007
(95% CI [+0.007,+0.007]) → ship recommended.**

**Verified.** `lsat.contrast` self-test all PASS (catalog gold-set clean; all 26
LR+RC types have a clause; abstains when nothing documented); `grade_answer`
returns the contrast on a miss / `None` on a hit; svelte-check 0 errors/0 warnings;
`eval/feedback.py` runs. (Registration in `eval/run.py` pending — added after the
concurrent eval-arms edit settles.)

### 2026-07-02 — Audit fixes batch 4 (perf + honest baseline)

- **#17 (MED, perf) primitive_coverage scanned all LSAT notes twice per build.**
  Added a per-build `deck_nodes_cache` (contextvar, collection-keyed, mirrors
  `events_cache`) opened by the dashboard `build()`. **Verified:** cache correct
  (54 nodes cached==uncached); a full build now does **1 deck-note scan instead
  of 2**; GATE OK. (`lsat/primitives.py`, `lsat/dashboard_data.py`.)
- **#15 (MED, honesty) beat-the-baseline had no significance test.** The
  embedding-vs-BM25 "win" was a single-point precision@k comparison. Fix:
  per-query reciprocal rank (informative when a query has one relevant doc) +
  `bootstrap_ci` on the paired per-query differences; `embedding_wins = (ci_low >
  0)`. **Honest verdict:** MRR 0.9238 vs 0.9162, mean diff 0.0076, **95% CI [0.0,
  0.0222] — does NOT exclude 0 → `embedding_wins = False`** (not statistically
  distinguishable on this set; a real semantic embedder would be needed to win).
  (`lsat/retrieval.py`, `eval/baselines.py`.) **Verified:** retrieval self-test
  OK; baselines report-only; GATE OK.

### 2026-07-02 — Audit fixes batch 3 (make Feature 4 reachable + mobile hardening)

- **#5/#7 (HIGH) session-mode was never set → Feature 4 (and #24) were dark.**
  `set_session_phase()` had no caller, so every desktop answer logged
  `phase="timed"` and no blind/relaxed event ever existed — the Blind-Review Gap
  Map, Choke Index, and honest-mastery filter could never receive data. Fix:
  - **Desktop:** a **Tools → LSAT Study Mode** radio submenu (Timed / Blind
    Review / Relaxed) that calls `set_session_phase` with a confirming tooltip.
    (`qt/aqt/main.py`.)
  - **Mobile:** a Timed/Blind/Relaxed segmented toggle in the study tab that
    drives `StudyItem`'s `phase` prop (already plumbed to `submitAnswer`), with an
    "untimed pass — doesn't inflate mastery" hint. (`ts/routes/lsat-mobile/+page.svelte`.)
  **Verified:** `main.py` compiles; `set_session_phase` import works; svelte-check
  + eslint clean.
- **#16 (MED) mobile double-log.** `grade()` had no re-entrancy guard, so a
  double confidence-tap during the network round-trip could log two events. Fix:
  guard on `state === "confidence"` and move to a transient `"grading"` state
  before the await (unmounts the tap; blocks re-entry). (`StudyItem.svelte`.)
- **Same-class as #9 on mobile:** the mobile classify chips also hardcoded 10 of
  17 LR types — expanded to all 17 (matches the taxonomy + the desktop notetype
  fix). (`StudyItem.svelte`.)
- **#26 (LOW) type mismatch:** `ReadinessScore.confidence` was `[number, string]`
  but the server sends `[level_string, reason_string]` → corrected to
  `[string, string]`. (`ts/lib/lsat/types.ts`.) **Verified:** svelte-check 0
  errors/0 warnings (1287 files); eslint clean.

### 2026-07-02 — Audit fixes batch 2 (security + AI safety + correctness)

- **#4 (HIGH, security) PWA endpoints exposed unauthenticated on the LAN.**
  `_have_api_access` returns True whenever `ANKI_API_HOST=0.0.0.0` — the *only*
  mode phone pairing works in — so the documented "per-session bearer token" was
  never enforced and the whole backend was reachable on the LAN. Fix: every LSAT
  endpoint (`next_item`/`submit_answer`/`submit_trap`/`submit_classify` +
  `lsatDashboardData`) now independently requires `Authorization: Bearer <token>`
  via `pairing_authorized()`, returning 403 otherwise, regardless of
  `ANKI_API_HOST`. Desktop webview and mobile PWA both already send the token, so
  it's transparent. (`qt/aqt/lsat_web.py`, `qt/aqt/mediasrv.py`,
  `qt/aqt/lsat_mobile.py` docstring.) **Verified:** Flask test-context — valid
  token → authorized, wrong/missing → rejected; `aqt.lsat_web` imports clean.
- **#12/#13/#25 (MED, AI safety).** `ClaudeClient.complete` now converts
  `anthropic.APIError` (rate-limit/network/timeout/status) → `LLMUnavailable` so a
  live batch degrades instead of crashing; the checker prompt wraps the candidate
  card in a `<candidate_card>` untrusted-data delimiter (+ offline regex updated)
  so injected text in `source_quote`/`front`/`back` can't reach the judge as
  instructions; the generator now drops cards whose `skill_tags` are empty or not
  in the taxonomy. (`lsat/ai/{client,prompts,generator}.py`.) **Verified:**
  card_check gate PASS, GATE OK; misconception self-test OK; stubbed live-error
  paths surface as `LLMUnavailable`.
- **#9 (HIGH) A2 classify chips.** The identification-first classify stage
  hardcoded 10 of 17 LR question-type chips, so 7 types (incl. `lr.paradox`) were
  unidentifiable. Fix: chips are now generated from the taxonomy's LR question
  types at notetype-build time. (`lsat/notetypes.py`.) **Verified:** template
  contains all 17 LR node ids; `make taxonomy` OK.
- **#23 (LOW) stray `[LSAT]` prefix in shared `studied_today()`** removed (shipped
  to every Anki user's stats, bypassing Fluent). Reverted in
  `rslib/src/stats/today.rs` and the hard-coded expectation in
  `rslib/src/scheduler/service/mod.rs`. **Verified:** `cargo test -p anki today`
  6/6 pass.
- **#24 (LOW) k-fold calibration leaked global weights.** Coefficients are now
  refit per training fold (not just ability), so the held-out ECE the readiness
  gate consumes is fully held-out. (`lsat/models/performance.py`.) **Verified:**
  ECE unchanged 0.0198, calibration+performance gates PASS.

### 2026-07-01 — Audit fixes batch 1 (eval honesty + honest-mastery)

- **#2 (HIGH) ablation not equal-study-time.** The `full` arm spent a *variable*
  misconception budget (~10.5 events) while other arms deducted a fixed 12, giving
  `full` ~1.5 extra ability-building generic-study events → a budget-artifact
  effect even when the feature is inert. Fix: every arm now spends exactly
  `ERROR_REVIEW_BUDGET` (12) on its error-review phase, so generic study is equal.
  **Verified:** with `MISCONCEPTION_SEVERITY=(0,0)` the arms now tie exactly
  (`feature_effect +0.0000`, CI `[0,0]`, claim not supported); the real effect
  dropped `+0.022 → +0.019` (the removed `+0.003` was pure artifact).
  (`eval/ablation.py`.)
- **#3/#14 (HIGH) leakage gate couldn't catch paraphrases + weak self-test.** The
  "embedding cosine" was a token-exact tf-idf cosine (no stemming) that collapses
  on reworded near-copies — the exact LSAT risk — and the self-test only planted a
  verbatim copy. Fix: added a **character-n-gram (shingle) Jaccard** near-copy
  signal (`LEAK_FUZZY_MAX=0.45`), a pluggable `_semantic_sim` hook (documented that
  a full synonym rewrite needs a real embedder), honest relabeling, and a rigorous
  `detector_self_test` (verbatim → caught; morphological reword → caught **by the
  shingle path** with cosine 0.48 < 0.90; unrelated → not flagged). **Verified:**
  real gold set still 0 flags; `make eval` GATE OK. (`eval/leakage.py`,
  `eval/config.py`.)
- **#10 (MED) honest-mastery filter was dead code.** `lucky_timed_items` (a timed
  win refuted by an untimed miss) was computed but never consumed, so lucky guesses
  still counted as mastery. Fix: `fold_recent_performance(honest_mastery=True)` now
  drops lucky timed wins (pure `lucky_timed_items_from_events`, lazy-imported, no
  extra read inside the events cache). No-op until a blind pass exists → degrades
  cleanly. **Verified:** regression shows honest 0.50 vs naive 0.667 with a lucky
  win present. (`lsat/events.py`, `lsat/blind_review.py`.)
- **#11 (MED) trap fingerprint double-counted across phases.** `_fold_trap_misses`
  ignored `phase`, so an item missed timed then again in a blind pass counted
  twice. Fix: timed-only filter (matches the honest-mastery convention).
  (`lsat/error_patterns.py`.) **Verified:** trap self-test still passes.

### 2026-07-01 — Research debate (round 2): 6 winning features selected

Ran a 4-lens × 2-round design debate over **29 researched proposals** (workflow;
real citations). Binding ruling in
[`research/debate/DECISION-round2.md`](../research/debate/DECISION-round2.md).
Winners, in build order: **#24 Paired Choke-Index CI** (ship ✓ below), **#4
If-Then Study Plan** (adherence), **#13+#14 Elaborated Contrast Card**, **#7
Exam-Day Retrievability Targeting**, **#10 Fatigue Curve**, **#19 Conditional
Translation Drill**. All Python/web, no Rust; each ships with a measured `eval/`
arm at equal study time.

### 2026-07-01 — Feature #24: Paired within-item Choke Index + bootstrap CI (F4 fix)

**Requirement:** DECISION-round2 #24 (highest-scoring winner, 9.0 unanimous);
refines shipped Feature 4 (`lsat/pacing.py`).

**Problem.** The shipped `choke_index` = untimed-accuracy − timed-accuracy over
**different item pools**, so an item-difficulty mismatch between the timed and
untimed sets reads as a spurious "choke," with no uncertainty estimate.

**Fix.** Added `paired_choke_index` — pairs events by `item_id` that have BOTH a
timed and an untimed answer, per-item delta ∈ {−1,0,+1}, **bootstrap 95% CI** per
skill + overall (reusing `eval.metrics.bootstrap_ci`); raises a choke flag **only
when CI lower bound > 0**, else abstains. Old aggregate retained as a labelled
low-confidence `fallback`. Wired into the dashboard `choke` insight.

**Verification.** New `eval/choke_validity.py` gate (registered in `eval/run.py`,
thresholds in `eval/config.py`): on synthetic learners with known ground-truth
pressure penalty, **paired CI coverage 0.95** (≥0.90) and **paired false-positive
rate 2.7%** vs **unpaired 99.7%** under difficulty-mismatched pools — a clean
demonstration the confound is fixed. `make eval` GATE OK; pacing self-tests pass.

### 2026-07-01 — Perf #3: points-at-stake bulk-load (Rust engine change; PRD §13)

**Requirement:** PRD §13 (latency), §7 (the Rust engine change). Independently
confirmed by the audit's #1 finding.

**Problem.** `points_at_stake_queue` issued `get_card` + full `get_note` **per due
card** (~100k SQL round-trips on the 50k deck; `get_note` also hydrates all
fields though only `tags` is used) → p50 238ms / p95 663ms.

**Fix.** Bulk-load: `all_cards_for_search(search)` (one query for all due cards) +
`get_note_tags_by_id_list(&note_ids)` (one query for all tags); hoisted
`FSRS::new` out of the per-card path. (`rslib/src/scheduler/points_at_stake.rs`.)

**Verification.** `cargo test -p anki points_at_stake` → **8/8 pass** (all
existing unit tests + the hypothesis/edge tests). Algorithmically 2×N SQL → 2
queries. End-to-end bench of the compiled backend is blocked by the offline JS
registry (see the environment note below); correctness is proven by the Rust
tests.

### 2026-07-01 — Audit: 28 confirmed findings (multi-agent, adversarially verified)

Ran an 11-dimension code audit (workflow), each finding adversarially verified:
**28 confirmed / 6 refuted**. The 2 refuted perf findings were the compute_memory
and FSRS-per-card issues I had **already fixed** — independent validation. Fix
plan (this log tracks each as it lands): HIGH — ablation equal-time (#2), leakage
paraphrase detection (#3/#14), PWA bearer-token auth (#4), phase/session-mode
wiring that unblocks Feature 4 + #24 (#5/#7), classify chips from taxonomy (#9),
missing eval arms (#8); MEDIUM — honest-mastery wiring (#10), trap phase filter
(#11), AI degradation + injection (#12/#13), mobile double-log guard (#16),
primitive_coverage memoization (#17), sync robustness (#20/#21/#22); LOW —
`[LSAT]` prefix revert (#23), k-fold weight leakage (#24), generator tag
enforcement (#25), types mismatch (#26), transfer badge (#27), validate 10+10
(#28).

### Environment note — offline JS registry blocks full `just build` / `just check`

`just build`/`just check` fail at `yarn install --immutable`
(`@sveltejs/kit@^2.60.1: No candidates found` — the registry is unreachable in
this sandbox). Consequence: I cannot rebuild the Rust→Python bridge (so the
compiled-backend bench can't reflect Rust edits) or run the full TS build/lint via
`just`. **Mitigations used:** Rust verified with `cargo test -p anki`; Python
verified with `out/pyenv` against the pre-built backend (`make eval`/`bench`/
`ablation` + module self-tests); TS verified with the cached `node_modules`
(526 pkgs) via direct tooling where possible. Full clean-machine build + TS lint
remain a CI/online step.

### 2026-07-01 — Perf #1: `compute_memory` single-scan (PRD §13 dashboard budget)

**Problem.** `compute_memory` (the dashboard's dominant cost) ran one
`find_cards("tag:X")` search **per taxonomy node** (~36 nodes), each re-scanning
the notes table. Profiling on the 50k deck: `find_cards` = **486 ms**, vs
retrievability 45 ms + revlog 17 ms.

**Fix.** Replaced the 36 per-node tag searches with **one joined scan** that
returns each LSAT-tagged card's tags *and* its FSRS retrievability together
(`cards ⋈ notes`, filtered by an `lsat::` `LIKE` pre-filter), then buckets recall
per node in Python — replicating Anki's hierarchical `tag:` matching via
`_tag_ancestors` (a card tagged `lsat::flaw::causal::x` still counts toward
`lsat::flaw::causal`). Revlog counts collapse to one grouped query.
(`lsat/models/memory.py`.)

**Verification.** Differential test vs the old per-node logic → **exact MATCH**
on both the seeded deck and the 50k synth deck (n_cards, memory %, n_reviews
identical per topic). Isolated speed: **543 ms → 126 ms (4.3×)**. `make eval`
gate still green.

### 2026-07-01 — Perf #2: request-scoped event-read cache (real-user dashboards)

**Problem.** A single dashboard build reads the graded-event log ~10× (memory,
performance, readiness, and 7 insight panels), each a full `find_notes` +
per-note `get_note` scan. Harmless on the bench (0 events) but O(10·N) for a
real student with hundreds/thousands of graded answers.

**Fix.** Added `events_cache(col)` — a `contextvars`-scoped, collection-keyed
read cache. Inside the window `read_events` returns one shared parse; `build()`
wraps its whole assembly in it. Safe because no event *note* is written during a
build (`append_projection` writes config, not a note). Reentrant; isolated per
async task/thread. Zero signature changes elsewhere. (`lsat/events.py`,
`lsat/dashboard_data.py`.)

**Verification.** All read_events-based self-tests pass (selection, calibration,
blind_review, error_patterns). Collapses ~10 scans → 1 per build.

### 2026-07-01 — Bug: `make bench` latency measured under `tracemalloc` (PRD §12.4/§13)

**Problem.** `main()` called `tracemalloc.start()` **before** the latency
measurement and stopped it after — so every hot-path latency was measured with
per-allocation tracing active. This inflates allocation-heavy paths ~5×
(dashboard_build **156 ms → 794 ms** under tracing), making a *passing* latency
falsely report as a **failure** of the §13 dashboard-refresh target.

**Fix.** Measure latency with tracing **off** (representative of production);
capture peak Python allocation in a separate traced `_memory_pass` afterward;
peak RSS (a process high-water mark) is unaffected. (`lsat/bench.py`.)

**Verification.** `make bench` now reports honest latency — dashboard_build
**151 ms p50 / 176 ms p95** (< 500 ms refresh target ✓, < 1 s first-load ✓).
Crash test still 0 corruption; memory ceilings still captured (239 MB RSS).
