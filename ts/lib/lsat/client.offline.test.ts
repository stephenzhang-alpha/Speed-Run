// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
// @vitest-environment jsdom

// Proves the "offline review + reconnect sync" contract for the LSAT PWA client:
// a graded answer submitted while offline (or on a connectivity failure) is saved
// to a durable local queue and replayed to the server on reconnect; prefetched
// items are served offline; and a real HTTP error is surfaced rather than queued.

import { beforeEach, describe, expect, test, vi } from "vitest";

import * as client from "./client";

function setOnline(v: boolean): void {
    Object.defineProperty(navigator, "onLine", { configurable: true, get: () => v });
}

/** A minimal fetch stand-in: no dependency on the global Response. */
function okJson(body: unknown) {
    return {
        ok: true,
        status: 200,
        json: async () => body,
        text: async () => JSON.stringify(body),
    };
}
function httpError(status: number) {
    return { ok: false, status, json: async () => ({}), text: async () => "server error" };
}
/** A 200 response whose BODY carries a server-side grading exception -- both
 * transports return exceptions this way (parity with the desktop pycmd bridge). */
function errorBody(msg: string) {
    return { ok: true, status: 200, json: async () => ({ error: msg }), text: async () => msg };
}

beforeEach(() => {
    localStorage.clear();
    setOnline(true);
});

describe("offline review + reconnect sync", () => {
    test("a graded answer submitted offline is queued, not sent over the network", async () => {
        setOnline(false);
        const fetchMock = vi.fn();
        globalThis.fetch = fetchMock as unknown as typeof fetch;

        const res = await client.submitAnswer("42", "C", "sure", 1000, "timed", "1");

        expect(res.queued).toBe(true);
        expect(fetchMock).not.toHaveBeenCalled();
        expect(client.pendingCount()).toBe(1);
    });

    test("flushQueue replays the queued answer to the server on reconnect", async () => {
        // 1) offline: queue an answer (no network)
        setOnline(false);
        globalThis.fetch = vi.fn() as unknown as typeof fetch;
        await client.submitAnswer("42", "C", "sure", 1000, "timed", "1");
        expect(client.pendingCount()).toBe(1);

        // 2) reconnect: the server is reachable and grades the replayed answer
        setOnline(true);
        const fetchMock = vi.fn(async () =>
            okJson({ graded: true, correct: true, correct_letter: "C", has_traps: false })
        );
        globalThis.fetch = fetchMock as unknown as typeof fetch;

        const out = await client.flushQueue();

        expect(out).toEqual({ synced: 1, pending: 0 });
        expect(client.pendingCount()).toBe(0);
        // it POSTed the queued payload to the right endpoint
        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
        expect(String(url)).toContain("/_anki/lsatSubmitAnswer");
        const body = JSON.parse(new TextDecoder().decode(init.body as Uint8Array));
        expect(body).toMatchObject({ item_id: "42", chosen: "C", confidence: "sure" });
    });

    test("a lost ack requeues under the SAME idempotency id the online attempt sent", async () => {
        // The committed-but-lost-ack case: the server records the event, then the ack
        // is lost, so the client re-queues. If the online attempt and the re-queue used
        // DIFFERENT ids, the reconnect replay would look unseen and the server would
        // log a SECOND event. The id must be stamped BEFORE the online post so both
        // carry it and the server dedups the replay.
        setOnline(true);
        let sentBody: { _idempotency?: string } | null = null;
        globalThis.fetch = vi.fn(async (_url: unknown, init: { body: Uint8Array }) => {
            sentBody = JSON.parse(new TextDecoder().decode(init.body));
            throw new TypeError("Failed to fetch"); // server committed, ack lost
        }) as unknown as typeof fetch;

        const res = await client.submitAnswer("77", "D", "sure", 900);
        expect(res.queued).toBe(true);

        // the online POST carried a stable idempotency id...
        const onlineId = sentBody!._idempotency;
        expect(typeof onlineId).toBe("string");
        expect(onlineId).toBeTruthy();
        // ...and the requeued row carries the SAME id (payload + row id), so a replay
        // of a submission the server already committed is deduped, not double-logged.
        const queued = JSON.parse(localStorage.getItem("lsat-offline-queue") || "[]");
        expect(queued).toHaveLength(1);
        expect(queued[0].payload._idempotency).toBe(onlineId);
        expect(queued[0].id).toBe(onlineId);
    });

    test("a connectivity failure while nominally online also queues (fetch TypeError)", async () => {
        setOnline(true);
        globalThis.fetch = vi.fn(async () => {
            throw new TypeError("Failed to fetch");
        }) as unknown as typeof fetch;

        const res = await client.submitAnswer("7", "A", "guess", 500);

        expect(res.queued).toBe(true);
        expect(client.pendingCount()).toBe(1);
    });

    test("a PERMANENT 4xx is surfaced, never silently queued (the server rejected it)", async () => {
        setOnline(true);
        // 422 = the server rejected the submission; nothing was committed, so retrying
        // is pointless -> surface it, do not queue.
        globalThis.fetch = vi.fn(async () => httpError(422)) as unknown as typeof fetch;

        await expect(client.submitAnswer("7", "A", "guess", 500)).rejects.toThrow();
        expect(client.pendingCount()).toBe(0);
    });

    test("a TRANSIENT 5xx on an online submit is queued, not lost", async () => {
        setOnline(true);
        // 503 (deploy / overload): the graded answer must be saved durably, not thrown
        // away. Safe against append-only -- the queued replay carries the same
        // idempotency id, so a committed-but-lost submission is deduped server-side.
        globalThis.fetch = vi.fn(async () => httpError(503)) as unknown as typeof fetch;

        const res = await client.submitAnswer("7", "A", "guess", 500);

        expect(res.queued).toBe(true);
        expect(client.pendingCount()).toBe(1);
    });

    test("a 200 response with a server-error BODY is treated as transient, not a false success", async () => {
        setOnline(true);
        // Both transports return a server exception as HTTP 200 + {error}. If this were
        // taken as success the graded answer would be dropped with nothing logged.
        globalThis.fetch = vi.fn(async () => errorBody("boom")) as unknown as typeof fetch;

        const res = await client.submitAnswer("7", "A", "guess", 500);

        expect(res.queued).toBe(true);
        expect(client.pendingCount()).toBe(1);
    });

    test("prefetchItems caches items and nextItem serves them offline, in order", async () => {
        setOnline(true);
        globalThis.fetch = vi.fn(async () =>
            okJson({
                items: [
                    { item_id: "1", stem: "S1", choices: [], skill_tags: [] },
                    { item_id: "2", stem: "S2", choices: [], skill_tags: [] },
                ],
                n: 2,
            })
        ) as unknown as typeof fetch;

        expect(await client.prefetchItems(2)).toBe(2);

        setOnline(false);
        const first = await client.nextItem();
        expect(first).toMatchObject({ item_id: "1", offline: true, done: false });
        const second = await client.nextItem();
        expect(second.item_id).toBe("2");
        const exhausted = await client.nextItem();
        expect(exhausted.done).toBe(true);
    });

    test("the queue survives a page reload (persisted in localStorage)", async () => {
        setOnline(false);
        globalThis.fetch = vi.fn() as unknown as typeof fetch;
        await client.submitAnswer("99", "B", "likely", 800);
        // a fresh read (simulating a reload) still sees the queued item
        expect(client.pendingCount()).toBe(1);
        expect(localStorage.getItem("lsat-offline-queue")).toContain("lsatSubmitAnswer");
    });

    test("a partial sync requeues the un-synced rows in FIFO order, then resumes", async () => {
        // queue three answers offline
        setOnline(false);
        globalThis.fetch = vi.fn() as unknown as typeof fetch;
        await client.submitAnswer("a", "A", "sure", 100);
        await client.submitAnswer("b", "B", "likely", 100);
        await client.submitAnswer("c", "C", "guess", 100);
        expect(client.pendingCount()).toBe(3);

        // reconnect, but the connection drops again after the FIRST replay succeeds
        setOnline(true);
        let calls = 0;
        globalThis.fetch = vi.fn(async () => {
            calls += 1;
            if (calls === 1) {
                return okJson({ graded: true, correct: true, correct_letter: "A", has_traps: false });
            }
            throw new TypeError("Failed to fetch");
        }) as unknown as typeof fetch;

        const partial = await client.flushQueue();
        expect(partial).toEqual({ synced: 1, pending: 2 });
        expect(client.pendingCount()).toBe(2);
        // the two un-synced rows are kept, in their original order (no drop, no reorder)
        const queued = JSON.parse(localStorage.getItem("lsat-offline-queue") || "[]");
        expect(queued.map((r: { payload: { item_id: string } }) => r.payload.item_id)).toEqual(["b", "c"]);

        // connection restored fully: the resume drains the rest
        globalThis.fetch = vi.fn(async () =>
            okJson({ graded: true, correct: false, correct_letter: "X", has_traps: false })
        ) as unknown as typeof fetch;
        const rest = await client.flushQueue();
        expect(rest).toEqual({ synced: 2, pending: 0 });
        expect(client.pendingCount()).toBe(0);
    });

    test("flushQueue drops a poison 4xx row but KEEPS transient failures (FIFO)", async () => {
        // queue [a, b, c] offline
        setOnline(false);
        globalThis.fetch = vi.fn() as unknown as typeof fetch;
        await client.submitAnswer("a", "A", "sure", 100);
        await client.submitAnswer("b", "B", "likely", 100);
        await client.submitAnswer("c", "C", "guess", 100);
        expect(client.pendingCount()).toBe(3);

        // reconnect: row a is a poison 422 (drop + keep draining); row b hits a 503
        // (transient -> keep, stop). Row a must be discarded, b and c must remain.
        setOnline(true);
        let calls = 0;
        globalThis.fetch = vi.fn(async () => {
            calls += 1;
            if (calls === 1) {
                return httpError(422); // row a: permanent -> dropped
            }
            return httpError(503); // row b: transient -> kept, drain stops
        }) as unknown as typeof fetch;

        const out = await client.flushQueue();
        // a synced=0 (a dropped as poison, not synced), b kept, c kept
        expect(out.synced).toBe(0);
        expect(client.pendingCount()).toBe(2);
        const queued = JSON.parse(localStorage.getItem("lsat-offline-queue") || "[]");
        expect(queued.map((r: { payload: { item_id: string } }) => r.payload.item_id)).toEqual(["b", "c"]);
    });

    test("a server-error BODY during replay keeps the row (never a fabricated sync)", async () => {
        setOnline(false);
        globalThis.fetch = vi.fn() as unknown as typeof fetch;
        await client.submitAnswer("z", "A", "sure", 100);
        expect(client.pendingCount()).toBe(1);

        // reconnect: the server returns 200 + {error} (an exception, e.g. a transient
        // lock). The row must NOT be counted as synced or dropped.
        setOnline(true);
        globalThis.fetch = vi.fn(async () => errorBody("locked")) as unknown as typeof fetch;
        const out = await client.flushQueue();
        expect(out).toEqual({ synced: 0, pending: 1 });
        expect(client.pendingCount()).toBe(1);
    });

    test("concurrent flushQueue calls share ONE flush -- no double-POST (append-only)", async () => {
        setOnline(false);
        globalThis.fetch = vi.fn() as unknown as typeof fetch;
        await client.submitAnswer("solo", "A", "sure", 100);
        expect(client.pendingCount()).toBe(1);

        // reconnect. A radio-flap fires two overlapping flushes before the first POST
        // resolves; the in-flight lock must make them share one flush so the single
        // queued row is POSTed exactly once (a second flush over the un-cleared
        // snapshot would re-POST it -> duplicate append-only event).
        setOnline(true);
        let posts = 0;
        let release: (() => void) | undefined;
        const gate = new Promise<void>((r) => (release = r));
        globalThis.fetch = vi.fn(async () => {
            posts += 1;
            await gate; // hold the first POST in-flight while we fire the second call
            return okJson({ graded: true, correct: true, correct_letter: "A", has_traps: false });
        }) as unknown as typeof fetch;

        const p1 = client.flushQueue();
        const p2 = client.flushQueue(); // must return the SAME in-flight promise
        expect(p2).toBe(p1);
        release!();
        const [r1, r2] = await Promise.all([p1, p2]);

        expect(posts).toBe(1); // POSTed exactly once despite two flush calls
        expect(r1).toEqual(r2);
        expect(client.pendingCount()).toBe(0);
    });
});
