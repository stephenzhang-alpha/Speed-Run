# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Local score models for Anki for LSAT: memory, performance, readiness.

These run locally (no network) so the app gives all three scores with AI off.
``memory`` is the first and simplest -- it reads Anki's FSRS recall and reports
an honest per-topic memory % with a range and a give-up rule.
"""
