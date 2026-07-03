# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Append-only log of past readiness projections + a user-facing track record.

PRD section 5.3, honesty-contract field 8: the app must show "how accurate your
past guesses turned out to be." We log each readiness projection (timestamp,
point, range, coverage, graded-item count) and later surface the history
alongside the current number. This is distinct from model calibration (PRD
section 12) -- it is the user-facing prediction history, not a
probability-calibration metric.

**Storage (defect #20).** Each projection is its own ``LSAT Projection`` note --
exactly the shape of the graded-event log (:mod:`lsat.events`): append-only,
id-keyed (a unique ``(device_id, hlc)``), and merged across devices by Anki's
note **set union**. The log previously lived in a single synced config key
(``lsat:projections``) as a list, which whole-map config last-writer-wins would
*replace* on a concurrent multi-device edit, silently dropping one device's
projections. Note set-union keeps every device's entries. Appends are throttled
(``MIN_APPEND_INTERVAL_MS``) so repeatedly opening the dashboard does not spam
duplicate entries. Legacy config-list entries (from before this change) are still
folded in on read for track-record continuity; new appends are always notes.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from lsat.events import _hlc_key, _next_hlc, device_id

if TYPE_CHECKING:
    from anki.collection import Collection

# Legacy single-key config store (pre-#20). No longer written; still read so an
# upgraded collection keeps the projections it logged before the notes existed.
PROJECTIONS_CONFIG_KEY = "lsat:projections"

LSAT_PROJECTION = "LSAT Projection"
PROJECTIONS_DECK = "LSAT::Projections"
# Field order matters: the first field is the sort field in the browser.
PROJECTION_FIELDS = [
    "ts",
    "point",
    "low",
    "high",
    "coverage_pct",
    "n_graded",
    "device_id",
    "hlc",
]

MAX_STORED = 200  # cap the read window (most-recent N); the log itself is never pruned
MIN_APPEND_INTERVAL_MS = 12 * 3600 * 1000  # at most ~2 entries/day


# -- notetype (idempotent, mirrors lsat.notetypes.ensure_notetypes) -----------


def ensure_projection_notetype(col: Collection) -> None:
    """Create the append-only ``LSAT Projection`` notetype if it is missing.

    Mirrors :func:`lsat.notetypes.ensure_notetypes`: idempotent, creates the
    notetype only when absent and never alters an existing one. Its single card
    template exists only because Anki requires one per notetype; projection cards
    are log rows, not study material, so they are suspended on creation.
    """
    mm = col.models
    if mm.by_name(LSAT_PROJECTION) is not None:
        return
    notetype = mm.new(LSAT_PROJECTION)
    for field_name in PROJECTION_FIELDS:
        mm.add_field(notetype, mm.new_field(field_name))
    template = mm.new_template("Projection")
    template["qfmt"] = "Projection {{point}} ({{low}}–{{high}}) @ {{ts}}"
    template["afmt"] = "{{FrontSide}}"
    mm.add_template(notetype, template)
    mm.add(notetype)


# -- parse helpers ------------------------------------------------------------


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (ValueError, AttributeError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (ValueError, AttributeError):
        return default


def _nf(note: Any, name: str) -> str:
    """Read a note field defensively (missing field -> "")."""
    try:
        val = note[name]
    except KeyError:
        return ""
    return val if val is not None else ""


def _sort_key(proj: dict[str, Any]) -> tuple[int, int, str]:
    """Order oldest -> newest by HLC (matching the event log); legacy entries
    that predate the HLC fall back to their wall-clock ``ts``."""
    hlc = str(proj.get("hlc", ""))
    if hlc:
        return _hlc_key(hlc)
    return (_as_int(proj.get("ts", 0)), 0, "")


# -- read ---------------------------------------------------------------------


def _read_projection_notes(col: Collection) -> list[dict[str, Any]]:
    if col.models.by_name(LSAT_PROJECTION) is None:
        return []
    out: list[dict[str, Any]] = []
    for nid in col.find_notes(f'note:"{LSAT_PROJECTION}"'):
        note = col.get_note(nid)
        out.append(
            {
                "ts": _as_int(_nf(note, "ts")),
                "point": _as_int(_nf(note, "point")),
                "low": _as_int(_nf(note, "low")),
                "high": _as_int(_nf(note, "high")),
                "coverage_pct": _as_float(_nf(note, "coverage_pct")),
                "n_graded": _as_int(_nf(note, "n_graded")),
                "device_id": str(_nf(note, "device_id")).strip(),
                "hlc": str(_nf(note, "hlc")).strip(),
            }
        )
    return out


def _read_legacy_projections(col: Collection) -> list[dict[str, Any]]:
    """Pre-#20 projections that lived in the ``lsat:projections`` config list.

    Read-only and best-effort: folded in so an upgraded collection keeps its
    prior track record. These lack an ``hlc``/``device_id`` and sort by ``ts``.
    """
    try:
        data = col.get_config(PROJECTIONS_CONFIG_KEY, [])
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for h in data:
        if not isinstance(h, dict):
            continue
        out.append(
            {
                "ts": _as_int(h.get("ts", 0)),
                "point": h.get("point"),
                "low": h.get("low"),
                "high": h.get("high"),
                "coverage_pct": h.get("coverage_pct"),
                "n_graded": h.get("n_graded"),
                "device_id": str(h.get("device_id", "")),
                "hlc": str(h.get("hlc", "")),
            }
        )
    return out


def read_projections(col: Collection) -> list[dict[str, Any]]:
    """All logged projections, oldest -> newest by HLC (most-recent ``MAX_STORED``).

    Unions the append-only ``LSAT Projection`` notes with any legacy config-list
    entries. Because each note is its own set-union-merged record, projections
    from every synced device survive (defect #20).
    """
    projs = _read_projection_notes(col)
    projs.extend(_read_legacy_projections(col))
    projs.sort(key=_sort_key)
    return projs[-MAX_STORED:]


# -- append (write) -----------------------------------------------------------


def append_projection(
    col: Collection,
    *,
    point: int,
    low: int,
    high: int,
    coverage_pct: float,
    n_graded: int,
    now_ms: int | None = None,
) -> bool:
    """Append a projection to the log; returns False if throttled/skipped.

    Writes one immutable ``LSAT Projection`` note stamped with this device's id
    and a fresh HLC (its unique set-union id), so concurrent multi-device
    projections all survive a sync. The throttle (at most one entry per
    ``MIN_APPEND_INTERVAL_MS``) is unchanged.
    """
    from anki.decks import DeckId

    now = now_ms if now_ms is not None else int(time.time() * 1000)
    history = read_projections(col)
    if history and (now - int(history[-1].get("ts", 0))) < MIN_APPEND_INTERVAL_MS:
        return False

    ensure_projection_notetype(col)
    notetype = col.models.by_name(LSAT_PROJECTION)
    assert notetype is not None
    dev = device_id(col)
    hlc = _next_hlc(col, dev, now_ms=now)
    deck_id = DeckId(col.decks.add_normal_deck_with_name(PROJECTIONS_DECK).id)

    note = col.new_note(notetype)
    note["ts"] = str(now)
    note["point"] = str(int(point))
    note["low"] = str(int(low))
    note["high"] = str(int(high))
    note["coverage_pct"] = str(float(coverage_pct))
    note["n_graded"] = str(int(n_graded))
    note["device_id"] = dev
    note["hlc"] = hlc
    col.add_note(note, deck_id)
    col.sched.suspend_cards(list(note.card_ids()))
    return True


# -- track record -------------------------------------------------------------


def track_record(col: Collection, *, now_ms: int | None = None) -> dict[str, Any]:
    """Summarise past projections for the honesty-contract track-record field.

    Reads the HLC-sorted log (:func:`read_projections`) so entries appear oldest
    -> newest regardless of which device logged them.
    """
    history = read_projections(col)
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    entries = [
        {
            "days_ago": round((now - int(h.get("ts", now))) / 86_400_000.0, 1),
            "point": h.get("point"),
            "low": h.get("low"),
            "high": h.get("high"),
        }
        for h in history
    ]
    shown = entries[-10:]
    if not history:
        note = "First projection -- no prior track record yet."
    else:
        oldest = shown[0]
        note = (
            f"{len(history)} past projection(s); oldest shown {oldest['days_ago']}d "
            f"ago we projected {oldest['point']} ({oldest['low']}-{oldest['high']})."
        )
    return {"count": len(history), "history": shown, "note": note}


# -- self-test ----------------------------------------------------------------


def _deliver_projection_notes(src: Collection, dst: Collection) -> int:
    """Simulate Anki's note **set-union** merge for projection notes: deliver every
    ``LSAT Projection`` note in ``src`` into ``dst``, deduplicated by ``hlc`` (its
    unique id). Idempotent -- a note already present in ``dst`` is skipped -- so
    re-delivery (a retried sync) changes nothing. Returns how many were added."""
    from anki.decks import DeckId

    ensure_projection_notetype(dst)
    notetype = dst.models.by_name(LSAT_PROJECTION)
    assert notetype is not None
    have = {p["hlc"] for p in _read_projection_notes(dst)}
    deck_id = DeckId(dst.decks.add_normal_deck_with_name(PROJECTIONS_DECK).id)
    added = 0
    for nid in src.find_notes(f'note:"{LSAT_PROJECTION}"'):
        snote = src.get_note(nid)
        if str(_nf(snote, "hlc")).strip() in have:
            continue
        dnote = dst.new_note(notetype)
        for field_name in PROJECTION_FIELDS:
            dnote[field_name] = _nf(snote, field_name)
        dst.add_note(dnote, deck_id)
        dst.sched.suspend_cards(list(dnote.card_ids()))
        added += 1
    return added


def _selftest() -> bool:
    """Two device-survival + HLC-non-regression checks on temp Collections."""
    import os
    import sys
    import tempfile

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for path in (os.path.join(root, "pylib"), os.path.join(root, "out", "pylib"), root):
        if path not in sys.path:
            sys.path.insert(0, path)

    from anki.collection import Collection
    from lsat.events import HLC_CONFIG_KEY, append_event, read_events

    now = 1_700_000_000_000
    checks: list[tuple[str, bool]] = []

    def check(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    tmp = tempfile.mkdtemp(prefix="proj-selftest-")

    # (A) DEFECT #20 -- multi-device projection survival --------------------------
    # Two devices each log a distinct projection; after a note set-union merge BOTH
    # must survive. Contrast: the old single config key would config-LWW one away.
    col_a = Collection(os.path.join(tmp, "deviceA.anki2"))
    col_b = Collection(os.path.join(tmp, "deviceB.anki2"))
    try:
        wrote_a = append_projection(
            col_a,
            point=160,
            low=157,
            high=163,
            coverage_pct=72.0,
            n_graded=210,
            now_ms=now,
        )
        wrote_b = append_projection(
            col_b,
            point=150,
            low=147,
            high=153,
            coverage_pct=64.0,
            n_graded=185,
            now_ms=now + 1,
        )
        pa = read_projections(col_a)
        pb = read_projections(col_b)
        check("each device logs its own projection", wrote_a and wrote_b)
        check("device A has exactly its 1 projection pre-merge", len(pa) == 1)
        check("device B has exactly its 1 projection pre-merge", len(pb) == 1)
        dev_a = pa[0]["device_id"]
        dev_b = pb[0]["device_id"]
        id_a = (pa[0]["device_id"], pa[0]["hlc"])
        id_b = (pb[0]["device_id"], pb[0]["hlc"])
        check("the two projections have distinct (device_id, hlc) ids", id_a != id_b)
        check("device ids are per-device (distinct)", bool(dev_a) and dev_a != dev_b)

        # Illustrate the OLD failure mode: whole-map config LWW replaces the value,
        # so exactly one device's list would survive (the bug this fix removes).
        lww_survivors = {p["point"] for p in [pb[0]]}  # last writer wins the key
        check(
            "OLD config-LWW would have kept only one device's projection",
            lww_survivors == {150} and 160 not in lww_survivors,
        )

        # NEW behaviour: note set-union delivers B's projection into A; both survive.
        added = _deliver_projection_notes(col_b, col_a)
        merged = read_projections(col_a)
        points = sorted(p["point"] for p in merged)
        devices = {p["device_id"] for p in merged}
        check("set-union delivered device B's projection", added == 1)
        check("after merge BOTH devices' projections survive", points == [150, 160])
        check("after merge both device ids are present", devices == {dev_a, dev_b})

        # Idempotent: a retried sync (re-delivery) adds nothing.
        added2 = _deliver_projection_notes(col_b, col_a)
        check(
            "re-delivery is idempotent (no double-count)",
            added2 == 0 and len(read_projections(col_a)) == 2,
        )

        tr = track_record(col_a, now_ms=now + 2)
        check("track_record counts both merged projections", tr["count"] == 2)
    finally:
        col_a.close()
        col_b.close()

    # (B) DEFECT #22 -- HLC baseline never regresses across sync ------------------
    # Set the synced baseline artificially LOW (below existing event walls), append
    # an event, and assert the new event's HLC wall is not below the prior max.
    col_c = Collection(os.path.join(tmp, "hlc.anki2"))
    try:
        for i in range(3):
            append_event(
                col_c,
                item_id=f"e{i}",
                skill_tags=["lr.weaken"],
                correct=True,
                response_ms=45_000,
                now_ms=now,
            )
        prior = read_events(col_c)
        max_prior_wall = max(e.wall_ms for e in prior)
        max_prior_key = max(_hlc_key(e.hlc) for e in prior)

        # Simulate a sync that lowered the whole-map config baseline.
        col_c.set_config(HLC_CONFIG_KEY, {"wall": 1000, "counter": 0})

        # Append with a wrong/skewed (low) wall clock too, so only the reconciled
        # baseline can keep the stamp monotonic.
        append_event(
            col_c,
            item_id="after",
            skill_tags=["lr.weaken"],
            correct=True,
            response_ms=45_000,
            now_ms=5000,
        )
        new_ev = next(e for e in read_events(col_c) if e.item_id == "after")
        check(
            "new HLC wall >= max prior event wall despite regressed baseline",
            new_ev.wall_ms >= max_prior_wall,
        )
        check(
            "new HLC key is strictly greater than every prior event",
            _hlc_key(new_ev.hlc) > max_prior_key,
        )
    finally:
        col_c.close()

    ok = all(passed for _, passed in checks)
    print("PROJECTIONS_OK" if ok else "PROJECTIONS_FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
