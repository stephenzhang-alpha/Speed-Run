// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// HTTP client for the LSAT mobile PWA. The desktop reviewer captures answers
// through the Qt-only `pycmd` bridge; on a phone there is no pycmd, so the PWA
// talks to the same mediasrv endpoints over HTTP. Requests use the
// "application/binary" content-type mediasrv requires, and carry a pairing
// token (handed to the phone via the desktop's "Study on your phone" dialog,
// in the URL hash) as the Bearer credential.

import type {
    AnswerResult,
    AssumptionDrill,
    AssumptionResult,
    ChainDrill,
    ChainResult,
    ClassifyResult,
    ConditionalDrillData,
    ConditionalResult,
    Dashboard,
    EvilTwinDrill,
    EvilTwinResult,
    LiveScenarioResult,
    OracleTheater,
    OracleTheaterMove,
    ProveStepResult,
    QuantifierNegationDrill,
    QuantifierNegationResult,
    QuantifierValidityDrill,
    QuantifierValidityResult,
    QuantifierVerdict,
    SectionAttemptResult,
    SectionItems,
    SectionQuestionAttempt,
    StemPolarityDrill,
    StemPolarityResult,
    StudyItemData,
    TrapResult,
    WorkedExampleDrill,
    WorkedStepResult,
} from "./types";

const TOKEN_KEY = "lsat-pair-token";
const API_BASE_KEY = "lsat-api-base";

/** The origin the `/_anki/*` API lives on. Empty (default) = same-origin, which is
 * how the PWA is served today (desktop mediasrv or lsat/server serve BOTH the shell
 * and the API). When the Android app bundles the shell LOCALLY (so it loads offline
 * instead of being a network-dependent WebView), the shell is served from the app,
 * not the server, so it needs an absolute base to reach the remote server; that is
 * baked in via a `#api=<origin>` fragment (captured by initToken) or the Capacitor
 * config. Trailing slash trimmed so `${apiBase()}/_anki/...` is always well-formed. */
function apiBase(): string {
    try {
        return (window.localStorage.getItem(API_BASE_KEY) ?? "").replace(/\/+$/, "");
    } catch {
        return "";
    }
}

/** Capture a `#token=...` (or `?token=...`) pairing token into localStorage on
 * first load, then strip it from the visible URL. Returns the active token. */
export function initToken(): string {
    if (typeof window === "undefined") {
        return "";
    }
    const fromHash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const fromQuery = new URLSearchParams(window.location.search);
    // A locally-bundled shell also carries the API origin (`#api=<origin>`); persist
    // it so `post()` can reach the remote server (same-origin PWA omits it -> "").
    const api = fromHash.get("api") ?? fromQuery.get("api");
    if (api) {
        try {
            window.localStorage.setItem(API_BASE_KEY, api);
        } catch {
            /* private mode: same-origin fallback */
        }
    }
    const incoming = fromHash.get("token") ?? fromQuery.get("token");
    if (incoming) {
        try {
            window.localStorage.setItem(TOKEN_KEY, incoming);
        } catch {
            /* private mode: fall through to in-memory use */
        }
        // Remove the secret from the address bar / history.
        history.replaceState(null, "", window.location.pathname);
        return incoming;
    }
    return token(); // hoisted below; same stored-token read + private-mode fallback
}

function token(): string {
    try {
        return window.localStorage.getItem(TOKEN_KEY) ?? "";
    } catch {
        return "";
    }
}

async function post<T>(path: string, payload: unknown = {}): Promise<T> {
    const headers: Record<string, string> = { "Content-Type": "application/binary" };
    const tok = token();
    if (tok) {
        headers["Authorization"] = `Bearer ${tok}`;
    }
    const resp = await fetch(`${apiBase()}/_anki/${path}`, {
        method: "POST",
        headers,
        body: new TextEncoder().encode(JSON.stringify(payload)),
    });
    if (!resp.ok) {
        // Carry the status so the offline replay can tell a transient failure (5xx /
        // 408 / 429 / auth) it should RETRY from a permanent 4xx it should drop.
        const err = new Error(`${resp.status}: ${await resp.text()}`) as Error & {
            status?: number;
        };
        err.status = resp.status;
        throw err;
    }
    const data = (await resp.json()) as T & { error?: unknown };
    // Both transports return a server-side grading EXCEPTION as HTTP 200 with an
    // {"error": "..."} body (parity with the desktop pycmd bridge, which has no HTTP
    // status). Treat that as a transient failure (synthetic 500), NOT a success:
    // otherwise the offline replay (doFlush) would count an un-logged submission as
    // "synced" and DROP it from the durable queue -- silent data loss + a fabricated
    // sync. Legitimate abstain / validation results use `graded:false` / `ok:false`
    // (never an `error` key), so they are unaffected and stay terminal.
    if (data && typeof data === "object" && typeof data.error === "string" && data.error) {
        const err = new Error(data.error) as Error & { status?: number };
        err.status = 500;
        throw err;
    }
    return data as T;
}

/** Should a failed POST be RETRIED (queued / kept) vs. surfaced-and-dropped? A
 * connectivity failure (fetch TypeError) or a transient status (5xx / 408 / 429 /
 * auth) is retryable; a permanent 4xx (400/404/422 ...) can never succeed. Shared by
 * postDurable (queue-on-failure) and doFlush (keep-vs-drop) so the two can never
 * drift into an asymmetry that silently discards a graded answer. */
function isTransientError(e: unknown): boolean {
    if (e instanceof TypeError) {
        return true; // connectivity failure -- offline
    }
    const status = (e as { status?: number }).status;
    if (typeof status !== "number") {
        return false;
    }
    return status >= 500 || status === 408 || status === 429 || status === 401
        || status === 403;
}

// ---------------------------------------------------------------------------
// Offline review + reconnect sync
//
// A phone drops signal mid-session. The no-answer-leak invariant means the client
// never holds the correct answer, so grading is ALWAYS server-side; "offline review"
// therefore means: (a) prefetch a batch of items to study, (b) durably QUEUE each
// graded submission in localStorage when offline / on a connectivity failure, and
// (c) replay the queue to the server on reconnect (the `online` event), where it is
// graded and appended to the same append-only PerformanceEvent log. Feedback for a
// queued answer arrives on reconnect. This makes the Android app usable without a
// live connection instead of being a purely network-dependent WebView.
// ---------------------------------------------------------------------------

const QUEUE_KEY = "lsat-offline-queue";
const ITEM_CACHE_KEY = "lsat-item-cache";

export interface QueuedSubmit {
    id: string;
    path: string;
    payload: unknown;
    ts: number;
}

function readJson<T>(key: string, fallback: T): T {
    try {
        const raw = window.localStorage.getItem(key);
        return raw ? (JSON.parse(raw) as T) : fallback;
    } catch {
        return fallback;
    }
}
/** Persist a value; returns false if it could NOT be written (private mode / quota),
 * so callers never report a false "saved" on a storage failure. */
function writeJson(key: string, value: unknown): boolean {
    try {
        window.localStorage.setItem(key, JSON.stringify(value));
        return true;
    } catch {
        return false;
    }
}

function isOffline(): boolean {
    return typeof navigator !== "undefined" && navigator.onLine === false;
}

let _idCounter = 0;
function newId(): string {
    try {
        if (typeof crypto !== "undefined" && crypto.randomUUID) {
            return crypto.randomUUID();
        }
    } catch {
        /* fall through */
    }
    return `q-${Date.now()}-${_idCounter++}`;
}

function dropById(list: QueuedSubmit[], id: string): QueuedSubmit[] {
    return list.filter((x) => x.id !== id);
}

/** Count of graded submissions waiting to sync. Drives the "N queued" UI. */
export function pendingCount(): number {
    return readJson<QueuedSubmit[]>(QUEUE_KEY, []).length;
}

/** Return `payload` carrying a stable `_idempotency` id, minting one only if absent.
 * Stamped ONCE up front in `postDurable` so the SAME id rides both the online attempt
 * and any offline / lost-ack re-queue: a submission the server committed but whose ack
 * was lost is then recognized on replay and NOT logged twice (server dedup, see
 * `lsat.events.idempotent_lookup`). Idempotent -- re-stamping keeps the first id. */
function withIdempotency(payload: unknown): unknown {
    if (!payload || typeof payload !== "object") {
        return payload;
    }
    const obj = payload as Record<string, unknown>;
    if (typeof obj._idempotency === "string" && obj._idempotency) {
        return obj;
    }
    return { ...obj, _idempotency: newId() };
}

/** Append an already-idempotency-stamped submission to the durable queue; returns
 * false if it couldn't persist. Reuses the payload's `_idempotency` as the queue-row
 * id so the row and its server-dedup key stay consistent (and a lost-ack re-queue
 * keeps the SAME id the online attempt already sent). */
function enqueue(path: string, payload: unknown): boolean {
    const stamped = withIdempotency(payload);
    const stampedId = stamped && typeof stamped === "object"
        ? (stamped as Record<string, unknown>)._idempotency
        : undefined;
    const id = typeof stampedId === "string" && stampedId ? stampedId : newId();
    const q = readJson<QueuedSubmit[]>(QUEUE_KEY, []);
    q.push({ id, path, payload: stamped, ts: Date.now() });
    return writeJson(QUEUE_KEY, q);
}

/** A mutating POST (grades + logs a PerformanceEvent). Offline or on a connectivity
 * failure it is queued durably and reported as {queued:true}; online it posts
 * normally. A real HTTP error (4xx/5xx) is surfaced, never silently queued. The
 * idempotency id is stamped BEFORE the online attempt so a committed-but-lost ack
 * replays under the same id and the server dedups it (no duplicate event). */
async function postDurable<T>(
    path: string,
    payload: unknown,
): Promise<T & { queued?: boolean }> {
    const stamped = withIdempotency(payload);
    if (isOffline()) {
        if (!enqueue(path, stamped)) {
            // storage full / private mode: DON'T report a false "saved offline".
            throw new Error("Offline, and couldn't save on this device (storage full).");
        }
        return { queued: true } as T & { queued?: boolean };
    }
    try {
        return (await post<T>(path, stamped)) as T & { queued?: boolean };
    } catch (e) {
        // Queue ANY transient failure (connectivity TypeError, 5xx, 408, 429, auth --
        // including a server exception surfaced as 200+{error} above), not just a
        // TypeError: a graded answer must not be discarded because the server was
        // briefly unreachable. This is safe against append-only because the payload
        // was idempotency-stamped BEFORE the online attempt, so if the server had
        // already committed it, the queued replay carries the SAME id and is deduped
        // server-side. A permanent 4xx (the server REJECTED it -> nothing committed)
        // is surfaced so the caller can react; retrying it is pointless.
        if (isTransientError(e) && enqueue(path, stamped)) {
            return { queued: true } as T & { queued?: boolean };
        }
        throw e;
    }
}

let _flushing: Promise<{ synced: number; pending: number }> | null = null;

/** Replay every queued submission to the server, in order. Serialized with an
 * in-flight lock: a concurrent call (e.g. a reconnect radio-flap firing `online`
 * twice, or an init flush overlapping the listener) returns the in-flight promise
 * rather than starting a SECOND flush over the same un-cleared snapshot -- which
 * would re-POST every item and duplicate append-only events. Safe to call repeatedly. */
export function flushQueue(): Promise<{ synced: number; pending: number }> {
    if (_flushing) {
        return _flushing;
    }
    _flushing = doFlush().finally(() => {
        _flushing = null;
    });
    return _flushing;
}

async function doFlush(): Promise<{ synced: number; pending: number }> {
    if (isOffline()) {
        return { synced: 0, pending: pendingCount() };
    }
    const q = readJson<QueuedSubmit[]>(QUEUE_KEY, []);
    if (!q.length) {
        return { synced: 0, pending: 0 };
    }
    let synced = 0;
    for (const item of q) {
        try {
            await post(item.path, item.payload);
            synced++;
            // Dequeue-after-ack: drop THIS item from the persisted queue immediately
            // (re-read so items enqueued mid-flush survive), so an OS-kill / reload
            // between POSTs can't re-POST an already-recorded item (duplicate event).
            writeJson(QUEUE_KEY, dropById(readJson<QueuedSubmit[]>(QUEUE_KEY, []), item.id));
        } catch (e) {
            if (!isTransientError(e)) {
                // a poison row (permanent 4xx: 400/404/422 ...) that can never succeed
                // -> drop it so it can't wedge the queue, and keep draining the rest.
                // eslint-disable-next-line no-console
                console.warn(`lsat: dropping un-replayable queued ${item.path}`, e);
                writeJson(
                    QUEUE_KEY,
                    dropById(readJson<QueuedSubmit[]>(QUEUE_KEY, []), item.id),
                );
                continue;
            }
            // transient (offline / 5xx / 429 / 408 / auth / server-exception body) ->
            // keep it queued and stop; the rest stay in FIFO order and retry on the
            // next flush (no data loss, no fabricated "synced").
            break;
        }
    }
    return { synced, pending: pendingCount() };
}

let _syncInit = false;
let _onSyncChange: (() => void) | undefined;
/** Register the reconnect-sync listener (idempotent) and flush any backlog now.
 * `onChange` fires after each flush so the UI can refresh its pending count. The
 * callback is stored in a module var and REFRESHED on every call, so after a page
 * component remounts (new route -> back) the persistent listener notifies the LIVE
 * instance -- not the destroyed one (which left the banner stuck on "syncing"). */
export function initOfflineSync(onChange?: () => void): void {
    if (typeof window === "undefined") {
        return;
    }
    _onSyncChange = onChange; // always point at the latest (live) component's callback
    if (_syncInit) {
        return;
    }
    _syncInit = true;
    const run = () => {
        void flushQueue().then(() => _onSyncChange?.());
    };
    window.addEventListener("online", run);
    if (!isOffline()) {
        run(); // clear a backlog left over from a previous (offline) session
    }
}

/** Cache a batch of items (no correct answers -- same no-leak payload as
 * sectionItems) so review works offline. Call while online. Returns the count. */
export async function prefetchItems(n = 10): Promise<number> {
    try {
        const batch = await sectionItems(n);
        const items = batch.items ?? [];
        writeJson(ITEM_CACHE_KEY, items);
        return items.length;
    } catch {
        return readJson<StudyItemData[]>(ITEM_CACHE_KEY, []).length;
    }
}

export function getDashboard(): Promise<Dashboard> {
    return post<Dashboard>("lsatDashboardData");
}

export function nextItem(): Promise<StudyItemData> {
    if (isOffline()) {
        // Serve the next prefetched item so review continues without a connection.
        const cached = readJson<StudyItemData[]>(ITEM_CACHE_KEY, []);
        const it = cached.shift();
        writeJson(ITEM_CACHE_KEY, cached);
        if (it) {
            return Promise.resolve({ ...it, done: false, offline: true });
        }
        return Promise.resolve({
            item_id: "",
            stem: "",
            choices: [],
            skill_tags: [],
            done: true,
            offline: true,
        });
    }
    return post<StudyItemData>("lsatNextItem");
}

export function submitAnswer(
    itemId: string,
    chosen: string,
    confidence: string,
    responseMs: number,
    phase = "timed",
    identified = "",
): Promise<AnswerResult> {
    return postDurable<AnswerResult>("lsatSubmitAnswer", {
        item_id: itemId,
        chosen,
        confidence,
        response_ms: Math.max(0, Math.round(responseMs)),
        phase,
        identified,
    });
}

export function submitClassify(itemId: string, named: string): Promise<ClassifyResult> {
    return post<ClassifyResult>("lsatSubmitClassify", { item_id: itemId, named });
}

// Timed Section Runner (r4 #17): POST the whole per-question trajectory (raw
// first/final choices, never correctness) and get back the refreshed ledger. The
// server grades and persists it -- correctness never crosses the wire mid-section.
export function submitSectionAttempt(
    trajectory: SectionQuestionAttempt[],
): Promise<SectionAttemptResult & { queued?: boolean }> {
    // Durable: a whole timed section is minutes of work; a mid-submit signal drop
    // must queue it (payload is raw first/final choices only -> no leak) and sync
    // on reconnect, not throw and lose the trajectory.
    return postDurable<SectionAttemptResult>("lsatSubmitSectionAttempt", { trajectory });
}

export function chainDrill(): Promise<ChainDrill> {
    return post<ChainDrill>("lsatChainDrill");
}

export function submitChain(
    itemId: string,
    chosen: string,
    responseMs: number,
): Promise<ChainResult> {
    return post<ChainResult>("lsatSubmitChain", {
        item_id: itemId,
        chosen,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}

// Oracle-Verified Faded Worked Example (research feature #1): fetch a partially
// worked chain derivation whose final step is blanked, then submit the chosen
// move. Every step is oracle-verified server-side, so a hallucinated step is
// never served; the correct move is withheld until submit.
export function workedExampleDrill(): Promise<WorkedExampleDrill> {
    return post<WorkedExampleDrill>("lsatWorkedExampleDrill");
}

export function submitWorkedStep(
    itemId: string,
    moveId: string,
    responseMs: number,
): Promise<WorkedStepResult> {
    return post<WorkedStepResult>("lsatSubmitWorkedStep", {
        item_id: itemId,
        move_id: moveId,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}

// Oracle-proven "Skill or Luck?" evil twin: a minimally-edited variant whose
// answer flips. The oracle proves every twin server-side; grading re-derives the
// verdict from the decision procedure via the stateless twin_key.
export function evilTwinDrill(): Promise<EvilTwinDrill> {
    return post<EvilTwinDrill>("lsatEvilTwinDrill");
}

export function submitEvilTwin(
    twinKey: string,
    chosen: string,
    responseMs: number,
): Promise<EvilTwinResult> {
    return post<EvilTwinResult>("lsatSubmitEvilTwin", {
        twin_key: twinKey,
        chosen,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}

// A batch of DISTINCT items for a timed section (stem + choices, never the answer).
// next_item returns only the single top card and doesn't advance until an answer
// is logged, so a section -- which must not submit answers mid-run -- uses this.
export function sectionItems(n = 10): Promise<SectionItems> {
    return post<SectionItems>("lsatSectionItems", { n });
}

export function submitTrap(
    itemId: string,
    chosen: string,
    family: string,
): Promise<TrapResult> {
    return post<TrapResult>("lsatSubmitTrap", { item_id: itemId, chosen, family });
}

export function conditionalDrill(): Promise<ConditionalDrillData> {
    return post<ConditionalDrillData>("lsatConditionalDrill");
}

export function submitConditional(
    itemId: string,
    sufficient: string,
    necessary: string,
    responseMs: number,
): Promise<ConditionalResult> {
    return post<ConditionalResult>("lsatSubmitConditional", {
        item_id: itemId,
        sufficient,
        necessary,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}

export function quantifierValidityDrill(): Promise<QuantifierValidityDrill> {
    return post<QuantifierValidityDrill>("lsatQuantifierValidityDrill");
}

export function submitQuantifierValidity(
    itemId: string,
    chosen: QuantifierVerdict,
    responseMs: number,
): Promise<QuantifierValidityResult> {
    return post<QuantifierValidityResult>("lsatSubmitQuantifierValidity", {
        item_id: itemId,
        chosen,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}

export function quantifierNegationDrill(): Promise<QuantifierNegationDrill> {
    return post<QuantifierNegationDrill>("lsatQuantifierNegationDrill");
}

export function submitQuantifierNegation(
    itemId: string,
    chosen: string,
    responseMs: number,
): Promise<QuantifierNegationResult> {
    return post<QuantifierNegationResult>("lsatSubmitQuantifierNegation", {
        item_id: itemId,
        chosen,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}

export function stemPolarityDrill(): Promise<StemPolarityDrill> {
    return post<StemPolarityDrill>("lsatStemPolarityDrill");
}

export function submitStemPolarity(
    itemId: string,
    chosen: string,
    responseMs: number,
): Promise<StemPolarityResult> {
    return post<StemPolarityResult>("lsatSubmitStemPolarity", {
        item_id: itemId,
        chosen,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}

export function assumptionDrill(): Promise<AssumptionDrill> {
    return post<AssumptionDrill>("lsatAssumptionDrill");
}

// Oracle Proof Theater (marquee AI demo): fetch the recorded model drafts whose
// every step is checked LIVE by the material-entailment oracle server-side, so
// the planted hallucination is blocked with the oracle's reason and the provable
// continuation is substituted. Read-only; no submit counterpart.
export function oracleTheater(): Promise<OracleTheater> {
    return post<OracleTheater>("lsatOracleTheater");
}

// Interactive "Prove It": submit a learner-built ordered move list for a theater
// scenario; the oracle returns per-step verdicts (+ a concrete counterexample
// "world" on an entailment failure) and whether the goal was proved. Read-only,
// no LLM -- the same decision procedure the recorded theater and the tests use.
export function proveStep(
    scenarioId: string,
    moves: Pick<OracleTheaterMove, "premise_index" | "contrapositive">[],
): Promise<ProveStepResult> {
    return post<ProveStepResult>("lsatProveStep", {
        scenario_id: scenarioId,
        moves,
    });
}

// "Draft it live": ask the real model (when a key is present) to draft the moves
// for a theater scenario, replayed through the SAME oracle; degrades to the
// recorded scenario when AI is off/unavailable/garbled.
export function oracleDraftLive(scenarioId: string): Promise<LiveScenarioResult> {
    return post<LiveScenarioResult>("lsatOracleDraftLive", {
        scenario_id: scenarioId,
    });
}

export function submitAssumption(
    itemId: string,
    chosen: string,
    responseMs: number,
): Promise<AssumptionResult> {
    return post<AssumptionResult>("lsatSubmitAssumption", {
        item_id: itemId,
        chosen,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}
