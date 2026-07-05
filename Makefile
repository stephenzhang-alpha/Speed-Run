# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
#
# Anki for LSAT -- convenience targets for the reproducible eval + benchmark.
# The brief asks for `make bench` and `make eval` specifically; the rest of the
# build still goes through `just` / `./ninja` (see CLAUDE.md).
#
# PYTHON defaults to the project's built environment (out/pyenv), which has the
# pyyaml dependency. Override with any interpreter that has pyyaml installed,
# e.g. PYTHON=/path/to/venv/bin/python (a bare system python3 will NOT work
# unless pyyaml is installed there).

PYTHON ?= out/pyenv/bin/python

.PHONY: help eval ablation bench taxonomy sync-demo

help:
	@echo "Anki for LSAT targets:"
	@echo "  make eval       Run the held-out eval + leakage gate (python -m eval.run)"
	@echo "  make ablation   Run the pre-registered B3 misconception-queue ablation (python -m eval.ablation)"
	@echo "  make bench      Run the 50k-deck hot-path benchmark (python -m lsat.bench)"
	@echo "  make sync-demo  Show offline review + reconnect sync end-to-end (python -m sync.offline_demo)"
	@echo "  make taxonomy   Print a summary of lsat-taxonomy.yaml (smoke test)"
	@echo ""
	@echo "Override the interpreter with PYTHON=... (must have pyyaml installed)"

eval:
	$(PYTHON) -m eval.run

ablation:
	$(PYTHON) -m eval.ablation

bench:
	$(PYTHON) -m lsat.bench

sync-demo:
	$(PYTHON) -m sync.offline_demo

taxonomy:
	$(PYTHON) -m lsat.taxonomy
