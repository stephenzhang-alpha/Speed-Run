---
name: lsat-desktop-android-parity
description: "Use this skill whenever adding, renaming, or removing an LSAT feature that has a mobile-PWA endpoint, so the desktop (MacBook) and Android versions stay in sync. Triggers: adding a new lsat* HTTP endpoint or drill, editing lsat/api.py ENDPOINTS, editing qt/aqt/lsat_web.py / qt/aqt/mediasrv.py post_handler_list / lsat/server/app.py _HANDLERS / ts/lib/lsat/client.ts, wiring a new Svelte drill or dashboard panel, or the test qt/tests/test_lsat_parity.py failing. Read this BEFORE touching any of those files. Pairs with lsat-protobuf-backend (Rust) and the build skill."
---

# Keeping the desktop (MacBook) and Android versions in sync

The LSAT app ships as **two front-ends over one shared brain**. A change is only
"done" when it lands in **both** versions — this skill is the checklist that makes
that automatic instead of a thing you remember.

## The two versions and what they share

|                | **Desktop (MacBook)**                                       | **Android**                                                        |
| -------------- | ----------------------------------------------------------- | ------------------------------------------------------------------ |
| Native shell   | PyQt app (`qt/aqt/`)                                        | Capacitor WebView (`mobile/`) → `LSAT_SERVER_URL/lsat-mobile`      |
| UI shown       | `lsat-dashboard` route + native Qt reviewer                 | `lsat-mobile` route (Study/Progress/Logic) + `lsat-section-runner` |
| Transport      | mediasrv: `qt/aqt/lsat_web.py` + `mediasrv.py` (in-process) | HTTP → `lsat/server/app.py` (Flask)                                |
| Business logic | `lsat/` Python (in-process)                                 | `lsat/` Python (via `lsat/server`)                                 |

**Shared by construction — a change here appears in BOTH versions automatically, no
extra wiring:**

- **`lsat/`** — all grading, models, drills, dashboard data, ZPD selection, events.
  A phone answer produces the _identical_ append-only `PerformanceEvent` a desktop
  answer does, because both call `lsat.grading`.
- **`lsat/api.py`** — the framework-agnostic endpoint handlers. One implementation,
  called by both transports.
- **`ts/lib/lsat/`** — every Svelte component + `theme.scss` design tokens. The
  desktop dashboard and the mobile Progress tab both render `DashboardView.svelte`.
- **`rslib/.../points_at_stake.rs`** — the one Rust engine change, compiled into both.

So most changes need **no parity work at all**. The one surface that is
hand-maintained in several files, and can therefore silently drift, is the **HTTP
endpoint contract**.

## The endpoint contract lives in 5 files — keep them identical

When you add / rename / remove an `lsat*` PWA endpoint, touch **all five**, in this
order:

1. **`lsat/api.py`** — write the handler function `foo(col, *, ...) -> dict`, and add
   its camelCase name (`"lsatFoo"`) to the **`ENDPOINTS`** tuple (the single source of
   truth).
2. **`lsat/server/app.py`** — add `"lsatFoo": lambda col, body: api.foo(col, ...)` to
   `_HANDLERS` (the **Android** transport). _Guarded:_ the module asserts
   `set(ENDPOINTS) == set(_HANDLERS)` at import, so a mismatch here fails fast.
3. **`qt/aqt/lsat_web.py`** — add a thin adapter `def foo(): ... return json.dumps(
   api.foo(aqt.mw.col, ...)).encode()` (with `pairing_authorized()` + `_ensure_lsat_on_path()`).
4. **`qt/aqt/mediasrv.py`** — add a `def lsat_foo() -> Response | bytes: from aqt.lsat_web
   import foo; return foo()` wrapper AND register `lsat_foo` in **`post_handler_list`**
   (the **desktop** transport). The route name is `stringcase.camelcase(fn.__name__)`,
   so `lsat_foo` → `lsatFoo` — it must match the `ENDPOINTS` name exactly.
5. **`ts/lib/lsat/client.ts`** — add `export function foo(...) { return post<Result>(
   "lsatFoo", {...}); }` and the request/response types in `ts/lib/lsat/types.ts`.

Then wire the UI in the shared component (`ts/lib/lsat/*.svelte`) and mount it in the
route(s) that should expose it (`ts/routes/lsat-mobile/+page.svelte` for the Android
Study/Logic tabs; `ts/routes/lsat-dashboard/+page.svelte` if it belongs on the desktop
home).

### The automated guard

`qt/tests/test_lsat_parity.py` (runs in `just check` / `just test-py`) asserts that
**all four endpoint sets are identical**:

```
lsat.api.ENDPOINTS  ==  lsat/server/app.py _HANDLERS
                    ==  qt/aqt/mediasrv.py post_handlers (lsat*)
                    ==  ts/lib/lsat/client.ts  "lsatFoo" call sites
```

If you forget one of the five files, the test tells you exactly which layer drifted
and in which direction (e.g. "missing on desktop: ['lsatFoo'] — a paired phone would
404"). `lsat/server/app.py` additionally self-guards at import. There is no import-time
guard inside `mediasrv.py` because the top-level `lsat` package is not on `sys.path`
when mediasrv is imported in the bundled app — the test is the desktop guard.

## Gotchas

- **`lsatDashboardData` has one code path on purpose.** `qt/aqt/lsat_dashboard.py::
  dashboard_json` delegates to `lsat.api.dashboard`, the same handler the server serves.
  Don't reintroduce a second `lsat.dashboard_data.build` call — keep them on one path.
- **Desktop shows `lsat-dashboard` (home) + the native reviewer + the `lsat-mobile`
  route in a window.** The Logic drills / Section Runner / Oracle Theater live in the
  `lsat-mobile` route; on the desktop they open via **Tools ▸ LSAT ▸ Practice (Drills
  & Sections)** (`qt/aqt/lsat_mobile.py::LsatPracticeDialog`, registered as
  `"LSATPractice"` in `aqt/__init__.py`), which loads that route in an
  `AnkiWebView(kind=AnkiWebViewKind.LSAT_MOBILE)`. That kind is in the api-access
  tuple in `qt/aqt/webview.py::_profileForPage`, so its `/_anki/lsat*` POSTs carry the
  bearer and aren't rejected as "Unexpected API access". **If you add another desktop
  window that loads an `lsat-*` route, use an api-access-granted kind** — otherwise its
  API calls 403. Only load first-party PWA routes at that trust level, never card JS.
- **Build/run needs `BUILD_ROOT`.** This checkout's path contains a space, so export
  `BUILD_ROOT=/Users/…/.anki-lsat-build` (the space-free dir the `out` symlink points
  at) before `just run` / `just test-py` / `just check`, or the `./ninja` wrapper
  splits the path.
- **`.proto` / Rust changes** need a full `just check` to regenerate; see
  `SKILL-protobuf-backend.md`.
