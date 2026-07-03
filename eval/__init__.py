# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Reproducible held-out evaluation + leakage harness for Anki for LSAT.

Earns "Score accuracy and honest uncertainty" and "Fair tests others can
re-run": one command (``make eval``) must reproduce every number, plot, and
report, and exit non-zero if any gate fails. See ``SKILL-lsat-eval.md`` and
PRD section 12. Thresholds are pre-declared in :mod:`eval.config` and committed
before looking at results.
"""
