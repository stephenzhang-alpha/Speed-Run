# Desktop installer — build & clean-machine verification

Anki's installer is **Briefcase-based** (`qt/installer/`, with `mac-template/`,
`linux-template/`, `windows-template/`). This guide documents how to build the
packaged app and the checklist to **verify it on a clean machine**.

> Scope note: the build steps below are runnable in a dev environment. The
> **"install on a clean machine and launch"** verification is a human/CI action
> — it requires a fresh machine (or VM) with **no developer tools, no Python, no
> Rust, no `BUILD_ROOT`** — which cannot be provisioned from the agent sandbox.
> It has **not** been run here; the checklist below is what to execute there.

## 1. Build the artifacts (dev machine)

```bash
export BUILD_ROOT=/Users/stephenzhang/.anki-lsat-build   # space-free build dir
just wheels                       # build the anki/aqt wheels
# then package with Briefcase against qt/installer/<platform>-template/
#   briefcase create  <platform>
#   briefcase build   <platform>
#   briefcase package <platform>   # -> .dmg (mac) / .msi (win) / .deb|AppImage (linux)
```

(Run the Briefcase steps from the installer tooling in `qt/installer`; on macOS
the output is a `.dmg`. Signing/notarization is required for a *distributable*
mac build but not for a local clean-VM smoke test.)

## 2. Clean-machine verification checklist

Use a **fresh** OS install / VM snapshot with none of the build prerequisites.
Copy only the built installer artifact onto it.

- [ ] **Installs** from the artifact with no missing-dependency errors (no system
      Python/Qt/Rust required — Briefcase bundles them).
- [ ] **Launches** to the Anki main window; no console/DLL/dylib errors.
- [ ] **Profile:** creates a new profile; the collection opens.
- [ ] **Core review loop:** add a Basic note, study it, grade it — a `revlog` row
      is written; the review loop works with **AI off** (default).
- [ ] **LSAT deck:** seed the sample deck (or import), confirm `LSAT Card` /
      `LSAT Item` / `LSAT PerformanceEvent` notetypes exist.
- [ ] **LSAT dashboard:** Tools → LSAT Dashboard (or Ctrl+Shift+L) opens and
      renders; with no graded data it shows the **honest abstaining** state
      (Memory/Performance/Readiness "not enough evidence yet").
- [ ] **Graded item:** review an `LSAT Item`, click a multiple-choice answer,
      confirm the inline correct/incorrect highlight and that a
      `PerformanceEvent` is recorded.
- [ ] **Sync (optional):** point Preferences → Syncing at a self-hosted server
      (`sync/README.md`) and confirm a round-trip.
- [ ] **Shortcut/menu:** the LSAT Dashboard menu item + `Ctrl+Shift+L` work.
- [ ] **Uninstall** cleanly removes the app.
- [ ] Record the OS + version and attach a screenshot of the running dashboard.

## 3. What is verified elsewhere in-repo (no clean machine needed)

These give confidence the packaged app's LSAT layer is sound even before the
manual install test:

- `SKIP_RUN=1 ./run` (or importing `aqt`) confirms the app imports with the LSAT
  additions wired (dashboard dialog, menu/shortcut, `pycmd` handler, webview
  API-access kind).
- The LSAT dashboard data path is verified end-to-end (server-side build + a
  live webview render check) — see the dashboard work.
- `make eval`, `make bench`, `make ablation`, and `python sync/validate.py` all
  run green and are reproducible.

## 4. CI hook (recommended)

Run the packaging on a clean CI runner (GitHub Actions matrix: macOS/Windows/
Linux), then a headless launch smoke test, so "verified on a clean machine" is
reproducible on every release rather than a one-off manual check.
