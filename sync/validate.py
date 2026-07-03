# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Stand up the built-in sync server and validate desktop<->desktop sync (7b).

Runs the fork's own sync server on localhost, points two client collections at
it, and proves the challenge-7b scenarios end to end:

  * device-id is per-device (a synced device_id would break HLC uniqueness),
  * 10+10 no-loss / no-double-count (native revlog AND the custom event log),
  * same-card conflict (both revlog rows preserved; observed current-state winner),
  * wrong-clock (HLC keeps ordering correct; a bad clock cannot win the LWW),
  * interrupted/retried sync (idempotent: re-sync duplicates nothing).

Run:  out/pyenv/bin/python sync/validate.py
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from typing import Literal

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(REPO, "pylib"), os.path.join(REPO, "out", "pylib"), REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Import Collection first: anki is a namespace package split across pylib
# (source) and out/pylib (generated), and importing anki.cards before
# anki.collection triggers a hooks_gen<->cards circular import. Loading
# collection first fully initialises anki.cards before hooks_gen reads it.
# `isort: off/on` pins this deliberate order so import-sorting cannot reorder it
# back to alphabetical (cards before collection) and re-break the import.
# isort: off
from anki.collection import Collection  # noqa: E402
from anki.cards import CardId  # noqa: E402

# isort: on

USER, PASSWORD = "user", "pass"
_REQ = {
    0: "NO_CHANGES",
    1: "NORMAL_SYNC",
    2: "FULL_SYNC",
    3: "FULL_DOWNLOAD",
    4: "FULL_UPLOAD",
}


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _start_server(base: str, port: int) -> subprocess.Popen:
    env = {
        **os.environ,
        "SYNC_USER1": f"{USER}:{PASSWORD}",
        "SYNC_HOST": "127.0.0.1",
        "SYNC_PORT": str(port),
        "SYNC_BASE": base,
        "PYTHONPATH": os.pathsep.join(
            [os.path.join(REPO, "pylib"), os.path.join(REPO, "out", "pylib")]
        ),
    }
    return subprocess.Popen(
        [sys.executable, "-m", "anki.syncserver"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _wait_ready(port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _sync(col: Collection, port: int) -> str:
    auth = col.sync_login(USER, PASSWORD, f"http://127.0.0.1:{port}/")
    out = col.sync_collection(auth, False)
    required = out.required
    if required in (out.FULL_UPLOAD, out.FULL_SYNC):
        col.close_for_full_sync()
        col.full_upload_or_download(auth=auth, server_usn=None, upload=True)
        col.reopen(after_full_sync=True)
    elif required == out.FULL_DOWNLOAD:
        col.close_for_full_sync()
        col.full_upload_or_download(auth=auth, server_usn=None, upload=False)
        col.reopen(after_full_sync=True)
    return _REQ.get(required, str(required))


def _revlog_ids(col: Collection) -> list[int]:
    return col.db.list("select id from revlog")


def _event_guids(col: Collection, note_ids: list[int]) -> list[str]:
    """The note guids for the given event notes -- the guid is the identity the
    append-only, set-union note merge keys on, so distinct guids == no double."""
    if not note_ids:
        return []
    ph = ",".join("?" * len(note_ids))
    return col.db.list(f"select guid from notes where id in ({ph})", *note_ids)


def _seed_basic(col: Collection, n: int) -> None:
    nt = col.models.by_name("Basic")
    assert nt is not None
    did = col.decks.id("Default")
    for i in range(n):
        note = col.new_note(nt)
        note["Front"] = f"Q{i}"
        note["Back"] = f"A{i}"
        col.add_note(note, did)


def _review(col: Collection, cids: list[int], ease: Literal[1, 2, 3, 4] = 3) -> None:
    for cid in cids:
        card = col.get_card(CardId(cid))
        card.start_timer()  # answerCard reads card.time_taken()
        col.sched.answerCard(card, ease)
        # Anki keys revlog rows by millisecond id; space reviews so ids stay
        # unique across both devices (a human's reviews are seconds apart).
        time.sleep(0.003)


# -- scenarios ----------------------------------------------------------------


def scenario_device_ids(a: Collection, b: Collection) -> tuple[str, bool, str]:
    from lsat.events import device_id

    da, db = device_id(a), device_id(b)
    ok = bool(da) and bool(db) and da != db
    return ("device-id per-device", ok, f"A={da} B={db} distinct={da != db}")


def scenario_10_10(
    a: Collection, b: Collection, port: int, cards: list[int]
) -> tuple[str, bool, str]:
    _review(a, cards[:10])
    _review(b, cards[10:20])
    _sync(a, port)
    _sync(b, port)
    _sync(a, port)
    ra, rb = _revlog_ids(a), _revlog_ids(b)
    sa, sb = set(ra), set(rb)
    ok = len(ra) == len(sa) and len(rb) == len(sb) and len(sa) == 20 and sa == sb
    return (
        "10+10 no-loss/no-double",
        ok,
        f"A={len(ra)} distinctA={len(sa)} B={len(rb)} equal={sa == sb}",
    )


def scenario_same_card(
    a: Collection, b: Collection, port: int, card: int
) -> tuple[str, bool, str]:
    _review(a, [card])
    _review(b, [card])
    _sync(a, port)
    _sync(b, port)
    _sync(a, port)
    ra, rb = _revlog_ids(a), _revlog_ids(b)
    rows_a = a.db.list("select id from revlog where cid=?", card)
    rows_b = b.db.list("select id from revlog where cid=?", card)
    state_a = a.db.first("select reps, ivl, due from cards where id=?", card)
    state_b = b.db.first("select reps, ivl, due from cards where id=?", card)
    ok = (
        len(ra) == len(set(ra))
        and set(ra) == set(rb)
        and rows_a == rows_b
        and len(rows_a) >= 2
        and state_a == state_b
    )
    return (
        "same-card conflict",
        ok,
        f"revlog_for_card A={len(rows_a)} B={len(rows_b)} "
        f"winner_state reps/ivl/due={state_a} converged={state_a == state_b}",
    )


def scenario_event_log(
    a: Collection, b: Collection, port: int
) -> tuple[str, bool, str]:
    from lsat.events import append_event, read_events

    # The event-log twin of scenario_10_10: 10 DISTINCT events on A + 10 DISTINCT
    # events on B (20 total). Each append gets its own item_id and its own HLC
    # (the per-device counter + device_id keep HLCs unique even if two wall clocks
    # coincide), and each event note carries a fresh random guid. After the
    # append-only, guid-keyed set-union merge every one of the 20 must survive on
    # BOTH devices with nothing lost and nothing double-counted. Space the appends
    # so no two notes share a creation millisecond across devices (same rationale
    # as _review's revlog spacing).
    expected = {f"ev-a-{i}" for i in range(10)} | {f"ev-b-{i}" for i in range(10)}
    for i in range(10):
        append_event(
            a,
            item_id=f"ev-a-{i}",
            skill_tags=["lr.weaken"],
            correct=(i % 2 == 0),
            response_ms=5000 + i,
        )
        time.sleep(0.003)
        append_event(
            b,
            item_id=f"ev-b-{i}",
            skill_tags=["lr.strengthen"],
            correct=(i % 2 == 1),
            response_ms=8000 + i,
        )
        time.sleep(0.003)
    _sync(a, port)
    _sync(b, port)
    _sync(a, port)
    ea, eb = read_events(a), read_events(b)
    ids_a, ids_b = {e.item_id for e in ea}, {e.item_id for e in eb}
    ha, hb = {e.hlc for e in ea}, {e.hlc for e in eb}
    ga = _event_guids(a, [e.note_id for e in ea])
    gb = _event_guids(b, [e.note_id for e in eb])
    ok = (
        len(ea) == 20
        and len(eb) == 20
        and ids_a == expected
        and ids_b == expected
        and len(ha) == 20
        and ha == hb
        and len(set(ga)) == 20
        and set(ga) == set(gb)
    )
    return (
        "10+10 event-log no-loss/no-double",
        ok,
        f"A_events={len(ea)} B_events={len(eb)} distinct_ids={len(ids_a)} "
        f"distinct_guids={len(set(ga))} no_loss={ids_a == expected == ids_b} "
        f"hlcs_equal={ha == hb}",
    )


def scenario_wrong_clock(
    a: Collection, b: Collection, port: int
) -> tuple[str, bool, str]:
    from lsat.events import _hlc_key, append_event, read_events, resolve_lww

    now = int(time.time() * 1000)
    append_event(
        a,
        item_id="wc-a",
        skill_tags=["lr.weaken"],
        correct=True,
        response_ms=5000,
        now_ms=now,
    )
    _sync(a, port)
    _sync(b, port)  # B inherits A's HLC baseline via synced config
    bad = now - 10 * 86_400_000  # B's wall clock is 10 days in the past
    append_event(
        b,
        item_id="wc-b",
        skill_tags=["lr.weaken"],
        correct=False,
        response_ms=5000,
        now_ms=bad,
    )
    _sync(b, port)
    _sync(a, port)
    events = {e.item_id: e for e in read_events(a)}
    a_ev, b_ev = events["wc-a"], events["wc-b"]
    ka, kb = _hlc_key(a_ev.hlc), _hlc_key(b_ev.hlc)
    lifted = kb[0] > bad  # B's HLC wall lifted above its bad clock via max()
    monotonic = kb > ka  # B (logically later) has the greater HLC despite bad clock
    winner = resolve_lww(
        [{"hlc": a_ev.hlc, "device_id": "A"}, {"hlc": b_ev.hlc, "device_id": "B"}]
    )
    picks_b = winner is not None and winner["hlc"] == b_ev.hlc
    ok = lifted and monotonic and picks_b
    return (
        "wrong-clock (HLC LWW)",
        ok,
        f"A_hlc={a_ev.hlc} B_hlc={b_ev.hlc} B_wall_lifted={lifted} "
        f"lww_picks_B={picks_b}",
    )


def scenario_retry(a: Collection, port: int) -> tuple[str, bool, str]:
    from lsat.events import read_events

    before = set(_revlog_ids(a))
    events_before = len(read_events(a))
    r1 = _sync(a, port)
    r2 = _sync(a, port)  # re-send: a retried/interrupted sync must be idempotent
    after = set(_revlog_ids(a))
    events_after = len(read_events(a))
    ok = before == after and events_before == events_after
    return (
        "interrupted/retry idempotent",
        ok,
        f"revlog_stable={before == after} events {events_before}->{events_after} "
        f"resync={r1}/{r2}",
    )


def main() -> int:
    import tempfile

    base = tempfile.mkdtemp(prefix="syncbase-")
    dir_a = tempfile.mkdtemp(prefix="clientA-")
    dir_b = tempfile.mkdtemp(prefix="clientB-")
    port = _free_port()
    server = _start_server(base, port)
    results: list[tuple[str, bool, str]] = []
    try:
        if not _wait_ready(port, 30.0):
            out = server.stdout.read() if server.stdout else ""
            print(f"SERVER FAILED TO START on :{port}\n{out}")
            return 1
        print(f"sync server up on 127.0.0.1:{port} (base={base})")

        a = Collection(os.path.join(dir_a, "collection.anki2"))
        b = Collection(os.path.join(dir_b, "collection.anki2"))
        try:
            from lsat.events import device_id
            from lsat.notetypes import ensure_notetypes

            # Seed 20 cards + LSAT notetypes + A's device id BEFORE the first
            # sync, so no mid-test schema change forces a full sync, and so B
            # inherits A's synced config (to exercise the device-id case).
            _seed_basic(a, 20)
            ensure_notetypes(a)
            device_id(a)
            print("A initial:", _sync(a, port))  # FULL_UPLOAD
            print("B initial:", _sync(b, port))  # FULL_DOWNLOAD
            cards = a.db.list("select id from cards order by id")
            assert len(cards) == 20, f"expected 20 cards, got {len(cards)}"

            results.append(scenario_device_ids(a, b))
            results.append(scenario_10_10(a, b, port, cards))
            results.append(scenario_same_card(a, b, port, cards[0]))
            results.append(scenario_event_log(a, b, port))
            results.append(scenario_wrong_clock(a, b, port))
            results.append(scenario_retry(a, port))
        finally:
            a.close()
            b.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    print()
    all_ok = True
    for name, ok, detail in results:
        all_ok = all_ok and ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print("\nVALIDATION_OK" if all_ok else "\nVALIDATION_FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
