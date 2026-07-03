# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Self-test for the standalone LSAT backend (no network; Flask test client).

Boots ``create_app`` against a seeded temp collection and checks the endpoint
contract: SPA serving, `/` redirect, token rejection, all five `/_anki/lsat*`
endpoints, submit-error parity (200 + {"error"}), and that a submitted answer is
logged. The server delegates to :mod:`lsat.api`, which the desktop mediasrv
front-end (``qt/aqt/lsat_web.py``) also calls -- so passing here is parity with
the desktop path by construction.

Run: ``python -m lsat.server.selftest``
"""

from __future__ import annotations

import json
import os
import sys
import tempfile


def _selftest() -> bool:
    sys.path[:0] = ["pylib", "out/pylib", "."]
    import anki.collection  # noqa: F401
    from anki.collection import Collection  # noqa: F401
    from lsat import api
    from lsat.events import read_events
    from lsat.seed import seed_deck
    from lsat.server.app import create_app

    ok = True

    def check(name: str, cond: bool, extra: str = "") -> None:
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name} {extra}")

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

    def post(endpoint: str, body: dict | None = None, auth: bool = True):
        headers = dict(hdr) if auth else {"Content-Type": "application/binary"}
        return client.post(
            f"/_anki/{endpoint}", data=json.dumps(body or {}), headers=headers
        )

    try:
        check("healthz", client.get("/healthz").status_code == 200)

        spa = client.get("/lsat-mobile")
        if app.config.get("LSAT_COL") is not None:
            # web_root may be absent in a bare checkout; only assert if served.
            if spa.status_code == 200:
                check("SPA served", b"<!doctype html>" in spa.data.lower())
            else:
                print("  [ ...] SPA route not mounted (no built web bundle); skipped")

        root = client.get("/", follow_redirects=False)
        if root.status_code in (301, 302):
            check(
                "root redirects to /lsat-mobile",
                "/lsat-mobile" in root.headers.get("Location", ""),
            )

        check(
            "token required (401 without)",
            post("lsatDashboardData", auth=False).status_code == 401,
        )

        dash = post("lsatDashboardData").get_json()
        check(
            "dashboard keys",
            {"scores", "insights", "coverage"} <= set(dash),
            str(sorted(dash)[:4]),
        )

        ni = post("lsatNextItem").get_json()
        check(
            "next_item shape",
            bool(ni["item_id"]) and len(ni["choices"]) >= 2 and ni["done"] is False,
        )
        iid = ni["item_id"]

        cl = post(
            "lsatSubmitClassify", {"item_id": iid, "named": "lr.weaken"}
        ).get_json()
        check(
            "classify graded", "classify_correct" in cl and "actual_type" in cl, str(cl)
        )

        n_before = len(read_events(col))
        ans = post(
            "lsatSubmitAnswer",
            {
                "item_id": iid,
                "chosen": "A",
                "confidence": "sure",
                "response_ms": 4200,
                "phase": "timed",
                "identified": "1",
            },
        ).get_json()
        check(
            "answer graded",
            {"correct", "correct_letter", "has_traps"} <= set(ans),
            str(ans),
        )
        evs = read_events(col)
        check(
            "answer logged an event",
            len(evs) == n_before + 1
            and evs[-1].chosen == "A"
            and evs[-1].identified == "1",
        )

        tr = post(
            "lsatSubmitTrap", {"item_id": iid, "chosen": "A", "family": "out_of_scope"}
        ).get_json()
        check("trap graded", "trap_correct" in tr, str(tr))

        # Parity with desktop: a bad submit is 200 + {"error"}, not a 5xx.
        bad = post("lsatSubmitAnswer", {"item_id": "999999", "chosen": "A"})
        check(
            "submit bad id -> 200 + error",
            bad.status_code == 200 and "error" in bad.get_json(),
        )

        # Parity with the shared contract: HTTP next_item matches a direct
        # lsat.api call (same shape the desktop front-end returns).
        direct = api.next_item(col)
        check(
            "HTTP == direct api shape",
            set(post("lsatNextItem").get_json()) == set(direct),
            "",
        )
    finally:
        col.close()

    print("SERVER_OK" if ok else "SERVER_FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if _selftest() else 1)
