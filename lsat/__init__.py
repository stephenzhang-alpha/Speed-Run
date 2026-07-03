# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Anki for LSAT: domain logic that rides on top of the Anki engine.

This package holds the LSAT-specific layer kept deliberately separate from the
upstream Anki tree so future rebases stay easy:

- ``taxonomy`` -- loads ``lsat-taxonomy.yaml`` (the single source of truth for the
  coverage map, readiness composition, and the points-at-stake review queue).

Later phases add the three score models (memory/performance/readiness), the AI
card pipeline, the graded-performance event log, and the dashboard data builder.

Import the loader explicitly, e.g. ``from lsat.taxonomy import load_taxonomy``.
"""
