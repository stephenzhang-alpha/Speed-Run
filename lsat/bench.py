# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""One-command benchmark (``make bench`` -> ``python -m lsat.bench``).

Synthesizes a 50,000-card deck, then reports **p50 / p95 / worst-case** latency
for each hot-path action, a **20x crash test** (kill a writer mid-write, reopen,
integrity-check -> expect zero corruption), and the **memory ceilings** (peak
RSS + peak Python allocation). PRD sections 12.4 / 13.

Reproducible + offline. The crash writer runs as a subprocess
(``python -m lsat.bench --crash-writer <path>``) that is SIGKILLed mid-write.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
import tracemalloc
from typing import Callable

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_REPO, "pylib"), os.path.join(_REPO, "out", "pylib"), _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DECK_SIZE = 50_000
LR_TAGS = [
    "lsat::lr::weaken",
    "lsat::lr::strengthen",
    "lsat::lr::flaw",
    "lsat::lr::assumption_necessary",
    "lsat::lr::inference_must_be_true",
    "lsat::lr::principle",
    "lsat::lr::paradox",
    "lsat::lr::parallel",
]


def _field_checksum(text: str) -> int:
    return int(hashlib.sha1(text.encode("utf-8")).hexdigest()[:8], 16)


def _synthesize_deck(col, n: int = DECK_SIZE) -> list[int]:
    """Bulk-insert n notes + cards (fast raw SQL). Returns the card ids."""
    from anki.utils import int_time

    mid = col.models.by_name("Basic")["id"]
    did = col.decks.id("Bench")
    now = int_time()
    base = now * 1000
    note_rows = []
    card_rows = []
    for i in range(n):
        nid = base + i
        cid = base + n + i
        fld0 = f"Q{i}"
        flds = f"{fld0}\x1fA{i}"
        tags = f" {LR_TAGS[i % len(LR_TAGS)]} "  # Anki stores tags space-padded
        note_rows.append(
            (
                nid,
                f"g{i:07d}",
                mid,
                now,
                0,
                tags,
                flds,
                fld0,
                _field_checksum(fld0),
                0,
                "",
            )
        )
        # review card, due today, no FSRS state (recall treated as 0)
        card_rows.append(
            (cid, nid, did, 0, now, 0, 2, 2, 0, 1, 2500, 0, 0, 0, 0, 0, 0, "")
        )
    col.db.executemany(
        "insert into notes (id,guid,mid,mod,usn,tags,flds,sfld,csum,flags,data) "
        "values (?,?,?,?,?,?,?,?,?,?,?)",
        note_rows,
    )
    col.db.executemany(
        "insert into cards (id,nid,did,ord,mod,usn,type,queue,due,ivl,factor,"
        "reps,lapses,left,odue,odid,flags,data) values (?,?,?,?,?,?,?,?,?,?,?,?,"
        "?,?,?,?,?,?)",
        card_rows,
    )
    # DBProxy has no explicit commit; the backend persists on col.close().
    return [base + n + i for i in range(n)]


def _timeit(fn: Callable[[], object], iters: int) -> list[float]:
    times = []
    for _ in range(iters):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000.0)  # ms
    return times


def _pctl(times: list[float], q: float) -> float:
    s = sorted(times)
    idx = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[idx]


def _memory_mb() -> float:
    import resource

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports bytes; Linux reports kilobytes.
    return rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024


# -- crash test ---------------------------------------------------------------


def _crash_writer(path: str) -> None:
    """Subprocess: open the collection and write continuously until SIGKILLed."""
    from anki.collection import Collection

    col = Collection(path)
    cid = col.db.scalar("select id from cards limit 1")
    # Signal we are open and about to write so the parent kills us mid-write,
    # not during (slower, variable) interpreter/collection startup.
    with open(path + ".writing", "w") as fh:
        fh.write("1")
    i = 0
    while True:
        col.db.execute("update cards set mod=? where id=?", int(time.time()) + i, cid)
        i += 1


def _crash_test(path: str, n: int = 20) -> dict[str, object]:
    from anki.collection import Collection

    corruptions = 0
    marker = path + ".writing"
    for k in range(n):
        if os.path.exists(marker):
            os.remove(marker)
        proc = subprocess.Popen(
            [sys.executable, "-m", "lsat.bench", "--crash-writer", path],
            cwd=_REPO,
            env={
                **os.environ,
                "PYTHONPATH": os.pathsep.join(
                    [os.path.join(_REPO, "pylib"), os.path.join(_REPO, "out", "pylib")]
                ),
            },
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Wait until the writer is open + writing, then kill it mid-write.
        deadline = time.time() + 15.0
        while (
            not os.path.exists(marker)
            and proc.poll() is None
            and time.time() < deadline
        ):
            time.sleep(0.02)
        time.sleep(0.08 + 0.02 * (k % 5))  # a little way into the write loop
        proc.kill()  # SIGKILL -- abrupt crash, no cleanup
        proc.wait(timeout=10)
        try:
            col = Collection(path)
            ok = col.db.scalar("pragma integrity_check") == "ok"
            n_cards = col.db.scalar("select count() from cards")
            col.close()
            if not ok or n_cards != DECK_SIZE:
                corruptions += 1
        except Exception:
            corruptions += 1
    return {"trials": n, "corruptions": corruptions}


# -- main ---------------------------------------------------------------------


def _memory_pass(col, card_ids: list[int]) -> None:
    """Exercise each hot-path action once, for peak-allocation measurement.

    Run under tracemalloc AFTER the latency pass so the (per-allocation) tracing
    overhead never contaminates the reported latencies -- tracemalloc can inflate
    an allocation-heavy path (e.g. the dashboard fold over 50k cards) several-fold,
    which would misreport a sub-target latency as a failure."""
    from lsat.dashboard_data import build as dashboard_build

    mid_card = card_ids[len(card_ids) // 2]
    col.find_cards("deck:Bench is:due")
    col.get_card(mid_card)
    col.sched.points_at_stake_queue([(t, 0.1, 0.0) for t in LR_TAGS], limit=50)
    dashboard_build(col)


def _bench_actions(col, card_ids: list[int]) -> dict[str, list[float]]:
    from lsat.dashboard_data import build as dashboard_build

    mid_card = card_ids[len(card_ids) // 2]
    results = {
        "search_deck (find due cards)": _timeit(
            lambda: col.find_cards("deck:Bench is:due"), 20
        ),
        "get_card (button press / next card)": _timeit(
            lambda: col.get_card(mid_card), 200
        ),
        "points_at_stake_queue (limit 50)": _timeit(
            lambda: col.sched.points_at_stake_queue(
                [(t, 0.1, 0.0) for t in LR_TAGS], limit=50
            ),
            10,
        ),
        "dashboard_build (first load / refresh)": _timeit(
            lambda: dashboard_build(col), 10
        ),
    }
    return results


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) == 2 and argv[0] == "--crash-writer":
        _crash_writer(argv[1])
        return 0

    import tempfile

    from anki.collection import Collection

    path = os.path.join(tempfile.mkdtemp(prefix="bench-"), "collection.anki2")
    col = Collection(path)
    print(f"Anki for LSAT -- benchmark (synthesizing {DECK_SIZE:,}-card deck)")
    t0 = time.perf_counter()
    card_ids = _synthesize_deck(col, DECK_SIZE)
    print(
        f"  synth done in {time.perf_counter() - t0:.1f}s "
        f"({col.db.scalar('select count() from cards'):,} cards)\n"
    )

    # Latency is measured with tracing OFF so the numbers reflect production
    # (tracemalloc adds per-allocation overhead that inflates allocation-heavy
    # paths); the memory ceiling is captured in a separate traced pass below.
    actions = _bench_actions(col, card_ids)
    print("hot-path latency (ms) on the 50k deck:")
    print(f"  {'action':40} {'p50':>9} {'p95':>9} {'worst':>9}")
    for name, times in actions.items():
        print(
            f"  {name:40} {_pctl(times, 0.5):9.2f} {_pctl(times, 0.95):9.2f} "
            f"{max(times):9.2f}"
        )

    # Peak Python allocation: one representative pass of every action, traced.
    tracemalloc.start()
    _memory_pass(col, card_ids)
    peak_py = tracemalloc.get_traced_memory()[1] / (1024 * 1024)
    tracemalloc.stop()
    peak_rss = _memory_mb()  # process high-water mark over the whole run
    col.close()

    print("\ncrash test (20x kill-mid-write -> reopen -> integrity_check):")
    crash = _crash_test(path, 20)
    print(f"  {crash['trials']} trials, {crash['corruptions']} corruption(s)")

    print("\nmemory ceilings:")
    print(f"  peak RSS            : {peak_rss:7.1f} MB")
    print(f"  peak Python alloc   : {peak_py:7.1f} MB (tracemalloc)")

    ok = crash["corruptions"] == 0
    print("\nBENCH_OK" if ok else "\nBENCH_FAIL (corruption detected)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
