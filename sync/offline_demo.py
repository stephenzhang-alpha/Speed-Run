# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""End-to-end **offline review + reconnect sync** demonstration -- the phone-sync
"recording", as a reproducible transcript.

Boots the standalone ``lsat/server`` (the backend the Android app talks to) against a
seeded temp collection and drives the EXACT flow the client performs
(``ts/lib/lsat/client.ts``):

1. **ONLINE** -- prefetch a batch of items to study (no correct answers in the payload).
2. **OFFLINE** -- review items; each graded answer is *queued locally* and the server
   is never contacted (proven: the server's append-only ``PerformanceEvent`` count does
   not move).
3. **RECONNECT** -- the queue is replayed; the server grades each answer and appends it
   to the same log (proven: the event count rises by exactly the queued count).
4. **LOST-ACK REPLAY** -- the same submissions (carrying the client's stable
   ``_idempotency`` id) are re-POSTed, simulating a lost ack; the server dedups them so
   the append-only count does NOT move (exactly-once under at-least-once replay).

It also asserts the **no-answer-leak** invariant directly: the prefetch payload contains
no correct-answer field.

Run: ``python -m sync.offline_demo`` (or ``out/pyenv/bin/python -m sync.offline_demo``).
Exits non-zero if the invariants don't hold, so it doubles as a check.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile


def main() -> int:
    sys.path[:0] = ["pylib", "out/pylib", "."]
    from anki.collection import Collection
    from lsat.events import read_events
    from lsat.seed import seed_deck
    from lsat.server.app import create_app

    def rule(title: str) -> None:
        print(f"\n=== {title} ===")

    # --- boot the standalone server against a fresh seeded collection ---
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "collection.anki2")
    seed = Collection(path)
    try:
        seed_deck(seed)
    finally:
        seed.close()

    app = create_app(path, token="tok")
    col = app.config["LSAT_COL"]
    client = app.test_client()
    hdr = {"Authorization": "Bearer tok", "Content-Type": "application/binary"}

    def post(endpoint: str, body: dict | None = None):
        return client.post(
            f"/_anki/{endpoint}", data=json.dumps(body or {}), headers=hdr
        )

    n0 = len(read_events(col))
    print(f"[server]  baseline append-only PerformanceEvents: {n0}")

    # 1) ONLINE: prefetch items to review offline (client.prefetchItems -> lsatSectionItems)
    rule("ONLINE  -- prefetch a batch of items to review offline")
    resp = post("lsatSectionItems", {"n": 5})
    items = (resp.get_json() or {}).get("items", [])
    print(
        f"[client]  prefetched {len(items)} items into the local cache "
        f"(payload carries NO correct answer -> no leak)"
    )
    k = min(3, len(items))
    if k == 0:
        print("[demo]    FAIL: no items to prefetch")
        return 1

    # no-answer-leak (hard invariant #1): the prefetch payload must not carry the
    # correct answer anywhere -- assert it, don't just claim it.
    leak_keys = {"correct", "correct_letter", "answer", "answer_letter", "is_correct"}

    def has_leak(obj: object) -> bool:
        if isinstance(obj, dict):
            return bool(leak_keys & set(obj.keys())) or any(
                has_leak(v) for v in obj.values()
            )
        if isinstance(obj, list):
            return any(has_leak(v) for v in obj)
        return False

    ok_noleak = not any(has_leak(it) for it in items)
    print(
        "[client]  no-leak check on prefetch payload: "
        + (
            "OK: no correct-answer field present"
            if ok_noleak
            else "FAIL: an answer field leaked to the client!"
        )
    )

    # 2) OFFLINE: review k items; each answer is QUEUED locally, server never contacted.
    # Each queued payload carries a stable `_idempotency` id, exactly as the real client
    # (ts/lib/lsat/client.ts) stamps it, so the lost-ack replay below can be deduped.
    rule("OFFLINE -- review answers are QUEUED on the device; the server is never contacted")
    queue: list[dict] = []
    for i, it in enumerate(items[:k]):
        chosen = it["choices"][0]["letter"] if it.get("choices") else "A"
        queue.append(
            {
                "endpoint": "lsatSubmitAnswer",
                "payload": {
                    "item_id": it["item_id"],
                    "chosen": chosen,
                    "confidence": "likely",
                    "response_ms": 4200,
                    "phase": "timed",
                    "_idempotency": f"demo-{i}-{it['item_id']}",
                },
            }
        )
        print(
            f"[client]  OFFLINE answered item {it['item_id']} (chose {chosen}) "
            f"-> saved to queue ({len(queue)} pending); no network call"
        )
    n1 = len(read_events(col))
    ok_offline = n1 == n0
    print(
        f"[server]  PerformanceEvents during offline: {n1} (expected {n0}) -> "
        f"{'OK: nothing logged while offline' if ok_offline else 'FAIL: server changed offline!'}"
    )

    # 3) RECONNECT: flush the queue -> each answer POSTed, graded, append-only logged
    rule("RECONNECT -- flush the queue; the server grades + append-only-logs each answer")
    synced = 0
    for q in list(queue):
        r = post(q["endpoint"], q["payload"])
        body = r.get_json() or {}
        graded_ok = r.status_code == 200 and body.get("graded") is not False and "error" not in body
        if graded_ok:
            synced += 1
            print(
                f"[client]  synced {q['payload']['item_id']} -> "
                f"graded correct={body.get('correct')} (server logged it)"
            )
        else:
            print(f"[client]  FAILED to sync {q['payload']['item_id']}: {body}")
    n2 = len(read_events(col))
    ok_sync = synced == k and n2 == n0 + k

    # 4) LOST-ACK REPLAY: the ack was lost, so the client re-POSTs the SAME queued
    #    submissions (same _idempotency id). The server must DEDUP -> the append-only
    #    event count must NOT grow (exactly-once under at-least-once replay).
    rule("LOST-ACK REPLAY -- re-POST the same submissions; the server must dedup (no new events)")
    for q in list(queue):
        post(q["endpoint"], q["payload"])
    n3 = len(read_events(col))
    ok_dedup = n3 == n2
    print(
        f"[server]  PerformanceEvents after duplicate replay: {n3} (expected {n2}) -> "
        + (
            "OK: deduped, exactly-once held"
            if ok_dedup
            else "FAIL: a replay double-logged an event!"
        )
    )

    rule("RESULT")
    passed = ok_offline and ok_sync and ok_noleak and ok_dedup
    print(
        f"[server]  PerformanceEvents after reconnect: {n2} (expected {n0 + k}); "
        f"synced {synced}/{k}"
    )
    print(
        ("DEMO OK" if passed else "DEMO FAILED")
        + f": offline review queued {k} answer(s) with the server untouched; "
        + f"reconnect synced {synced} -> {n2 - n0} new append-only event(s); "
        + f"duplicate replay added {n3 - n2} (deduped); no-leak={'ok' if ok_noleak else 'FAIL'}."
    )
    col.close()
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
