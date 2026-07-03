---
name: anki-build
description: "Use this skill whenever building, running, testing, or packaging Anki from source — i.e. anytime you touch the forked Anki repo's build. Triggers include: running `./run`, `./ninja`, build failures, 'build from source', ninja/n2 errors, missing build.ninja, Rust toolchain mismatches, getting a Rust or proto change to show up in the running app, building wheels or an installer, setting up an editor/IDE for the repo, or producing the clean-build / clean-machine-install recordings the project requires. Read this BEFORE running build commands or diagnosing why a change isn't showing up."
---

# Building & running Anki from source

Anki's build is the riskiest part of day one. The build orchestrator is a Rust runner that drives **n2/ninja**; most outputs land in `out/`. Python, Node, and `protoc` are downloaded automatically by the build. Get `./run` working and one tiny Rust change showing in the app **before** anything else.

## Prerequisites (all platforms)

- **Rustup** — https://rustup.rs/. The version pinned in `rust-toolchain.toml` is downloaded automatically. If you remove that file to use a distro Rust, newer Rust usually *builds* but may fail tests; older Rust may not build at all. (Anki has had releases that don't build on a too-new Rust, so prefer the pinned version.)
- **N2 or Ninja.** N2 gives better status output: `tools/install-n2` (on Windows `bash tools\install-n2`; if WSL conflicts with MSYS2 bash, run `C:\msys64\usr\bin\bash.exe tools/install-n2`). Or install Ninja 1.10+ from your distro/Homebrew, or the 1.11.1 release binary on PATH.
- **(Optional) `just`** — `brew install just` or `uv tool install just`. Anki is experimenting with `just` as the official command runner; it may become the source of truth later.
- **Python 3.9+** (3.9 recommended; 3.10+ has had less testing). You don't have to install Node or protoc — the build fetches them. You *can* override with `PYTHON_BINARY`, `NODE_BINARY`, `YARN_BINARY`, `PROTOC_BINARY`.
- **Repo path:** no spaces, and keep it short on Windows.

Platform-specific requirements live in `docs/windows.md`, `docs/mac.md`, `docs/linux.md`. On modern Ubuntu/Debian in particular:
- `sudo apt remove python3-protobuf` (it conflicts with the build).
- If using system Qt (6.2+) instead of the downloaded PyQt: `sudo apt install python3-pyqt6.qt{quick,webengine} python3-venv pyqt6-dev-tools`, then before any `./run`:
  ```bash
  export PYTHONPATH=/usr/lib/python3/dist-packages
  export PYTHON_BINARY=/usr/bin/python3
  ```
- On startup you may need extra xcb libraries (e.g. `libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxkbfile1`). See https://docs.ankiweb.net/platform/linux/missing-libraries.html.

## Run it

From the top of the repo:
```bash
./run            # .\run on Windows
```
This **builds Anki and runs it in place**. The first build is slow (downloads + compiles many deps), then Anki launches automatically. `./run` auto-enables `ANKIDEV` (extra logging; automatic backups disabled — so only use it on a throwaway profile). Load a specific profile with `-p "<profile>"`.

## Tests & checks (needed for the Wednesday proof and the Rust change)

```bash
./ninja check                 # all tests/checks (tools\ninja check on Windows)
./ninja check:svelte:editor   # a single check, by name
./ninja check:svelte          # a group of checks
```
Rust tests can also be run directly with `cargo test` from `rslib` while iterating (but `./ninja check` is the source of truth and also runs Python/TS checks). See the `anki-protobuf-backend` skill for where backend tests live.

## Formatting & lint

```bash
./ninja format        # fix formatting
./ninja fix           # fix ruff / eslint / copyright-header issues
cargo clippy --fix    # fix clippy issues
```

## Optimized builds

`./run` is non-optimized (fast compile, slower Anki). For an optimized run:
```bash
./tools/runopt
# or: RELEASE=1 ./run   (RELEASE=2 optimizes further, builds much slower)
```

## Packaging (the Sunday deliverable)

```bash
tools/build            # builds Python wheels -> out/wheels
tools/build-installer  # builds an installer -> out/installer/dist (e.g. MSI on Windows)
```
For the brief's "installs and runs on a clean device" proof, build the installer and verify it on a fresh VM/container.

## Clean builds, caches, offline

- Most build files are in `out/` (plus `node_modules` on Windows). Delete `out/` for a clean build or to free space.
- Dependency caches live in `~/.rustup`, `~/.cargo`, and `~/.cache/{yarn,pip}` (Yarn cache under `%LOCALAPPDATA%\Yarn` on Windows).
- Fully offline build: set `OFFLINE_BUILD=1` (the build then skips network-accessing tools).

## Useful runtime env vars

- `ANKIDEV` — extra stdout logging; disables auto-backups (auto-set by `./run`).
- `TRACESQL` — print every SQL statement as it executes (handy for the sync/integrity work).
- `LOGTERM` — also print warnings/errors that normally go to the collection log.
- `ANKI_PROFILE_CODE` — write Python profiling data on exit.

## Editor / IDE setup

```bash
mkdir .vscode && cd .vscode && ln -sf ../.vscode.dist/* .
```
Then open the repo root in VS Code and install the recommended extensions. The Python venv built by the project is at `out/pyenv` (select it via "Python: Select Interpreter"). **Code completion depends on generated files, so run `./run` or `tools/build` before relying on completion.** If you invoke Rust outside the build (plain `cargo`, or rust-analyzer), its output goes to `target/`, separate from `out/`.

## Troubleshooting

- **`ninja not installed` / `build.ninja` missing** → N2/Ninja isn't on PATH; run `tools/install-n2` (see the WSL/MSYS2 note above).
- **Rust config / `configure` failure** → usually a toolchain mismatch; restore `rust-toolchain.toml` and let Rustup install the pinned version.
- **Build fails fetching deps** → confirm network (or set `OFFLINE_BUILD=1` with prefetched caches); check the `apt-get install` step in `.github/workflows/` (the `setup-anki` composite action) for the authoritative buildtime/runtime dependency list.

## Definition of done (maps to the brief's Wednesday milestone)

- `./run` produces a working, in-place build on a clean machine (record it).
- A tiny Rust change in `rslib` is visibly reflected in the running desktop app.
- `./ninja check` passes.
- The same engine builds for the phone (AnkiDroid wraps this Rust backend) — see the project README.
