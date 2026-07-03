# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Loader + helpers for the LSAT skill taxonomy.

``lsat-taxonomy.yaml`` at the repo root is the single source of truth for:

1. the coverage map ("% of the exam covered"),
2. the readiness score composition (per-question-type weights), and
3. the points-at-stake review queue (the Rust engine change).

The weights are modeled estimates, not official LSAC data (see the YAML header).
This module parses that file into typed objects and exposes the lookups the rest
of the app needs, plus the node-id <-> Anki-tag mapping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

# Repo root is the parent of this package directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TAXONOMY_PATH = REPO_ROOT / "lsat-taxonomy.yaml"

# Taxonomy node ids use dots (``lr.weaken``); Anki uses ``::``-delimited
# hierarchical tags. Everything lives under a single ``lsat`` namespace so a deck
# of LSAT cards never collides with a user's other tags and rolls up for free
# (``tag:lsat::lr::*`` matches every LR child).
TAG_NAMESPACE = "lsat"
TAG_SEP = "::"

KIND_QUESTION_TYPE = "question_type"

# Answer-choice trap families (the ``skill.trap.*`` leaves). The
# Distractor-Reasoning Engine attributes a wrong pick to one of these, and the
# "which trap is (C)?" tap offers them as options. Ordered for stable display.
TRAP_FAMILIES = [
    "out_of_scope",
    "extreme_language",
    "reversal",
    "half_right",
    "irrelevant_comparison",
]
TRAP_FAMILY_LABELS = {
    "out_of_scope": "Out of scope",
    "extreme_language": "Extreme / absolute language",
    "reversal": "Reversal (sufficient/necessary or causal)",
    "half_right": "Half-right / partially supported",
    "irrelevant_comparison": "Irrelevant comparison",
}


def trap_family_to_node_id(family: str) -> str:
    """``extreme_language`` -> ``skill.trap.extreme_language``."""
    return f"skill.trap.{family}"


# Reasoning-primitive families (SPOV 1 / docs/Speedrun_AI_Features.md A1). Every
# LSAT Card drills exactly one of these; coverage and analytics slice by them.
PRIMITIVE_DICTION = "diction"
PRIMITIVE_LOGIC = "logic"
PRIMITIVE_QTYPE = "qtype"

# Diction primitives are study-only (never scored); their queue weight.
DICTION_STUDY_WEIGHT = 0.3


def primitive_type_of_node(node_id: str) -> str:
    """Classify a taxonomy node id into its primitive family.

    ``diction.*`` -> diction; ``flaw.*`` and the formal-logic cross-cutting
    skills -> logic; question types (``lr.*``/``rc.*``) and everything else
    (traps, argument-part skills, structures) -> qtype, since they concern
    recognizing and attacking question/argument forms.
    """
    if node_id.startswith("diction."):
        return PRIMITIVE_DICTION
    if node_id.startswith("flaw.") or node_id in (
        "skill.conditional_logic",
        "skill.quantifier_logic",
    ):
        return PRIMITIVE_LOGIC
    return PRIMITIVE_QTYPE


def node_id_to_tag(node_id: str) -> str:
    """``lr.weaken`` -> ``lsat::lr::weaken``."""
    return TAG_SEP.join([TAG_NAMESPACE, *node_id.split(".")])


def tag_to_node_id(tag: str) -> str:
    """Inverse of :func:`node_id_to_tag`; tolerant of a missing namespace."""
    parts = [p for p in tag.split(TAG_SEP) if p]
    if parts and parts[0] == TAG_NAMESPACE:
        parts = parts[1:]
    return ".".join(parts)


@dataclass(frozen=True)
class Scoring:
    scale: tuple[int, int]
    scored_sections: list[str]
    scored_questions_estimate: int
    measurement_band_points: int
    equating: bool


@dataclass(frozen=True)
class Section:
    id: str
    name: str
    exam_weight: float
    scored_questions_estimate: int


@dataclass(frozen=True)
class Topic:
    """A scored question type (the coverage denominator + readiness composition)."""

    id: str
    section: str
    kind: str
    name: str
    within_section_weight: float
    exam_weight: float
    stem_cues: list[str] = field(default_factory=list)
    subtypes_ref: str | None = None

    @property
    def tag(self) -> str:
        return node_id_to_tag(self.id)

    @property
    def is_question_type(self) -> bool:
        return self.kind == KIND_QUESTION_TYPE


@dataclass(frozen=True)
class CrossCuttingSkill:
    """Conditional logic, pacing, trap patterns, etc.

    These carry ``study_weight`` (used by the queue/mastery only) and do NOT
    participate in score composition, to avoid double-counting.
    """

    id: str
    name: str
    study_weight: float
    appears_in: list[str] = field(default_factory=list)
    note: str | None = None

    @property
    def tag(self) -> str:
        return node_id_to_tag(self.id)


@dataclass(frozen=True)
class Structure:
    """An argument-structure schema (``struct.causal``, ``struct.conditional``...).

    Structures are surface-independent reasoning skeletons. The Transfer Meter
    reports whether a student is right on a schema across *new surface topics*
    (transferred) vs only on ones they have drilled (memorized).
    """

    id: str
    name: str
    appears_in: list[str] = field(default_factory=list)

    @property
    def tag(self) -> str:
        return node_id_to_tag(self.id)


@dataclass(frozen=True)
class Coverage:
    basis: str
    min_graded_items_to_count: int


@dataclass(frozen=True)
class ReadinessGiveUp:
    min_graded_performance_items: int
    min_lr_question_type_coverage: float
    require_each_rc_question_type: bool
    min_timed_items: int
    max_heldout_calibration_ece: float
    # D3: abstain on high measured student overconfidence / thin deck coverage
    # of the primitive taxonomy. Defaults keep older YAMLs loading.
    max_student_overconfidence: float = 0.15
    min_primitive_coverage: float = 0.50


@dataclass(frozen=True)
class GiveUp:
    readiness: ReadinessGiveUp
    memory_min_reviews_per_topic_for_display: int


@dataclass(frozen=True)
class ReadinessConfig:
    min_range_points: int
    required_display_fields: list[str]
    # D2: extra half-width points per unit of measured student overconfidence
    # (readiness_uncertainty.widen_points_per_overconfidence in the YAML).
    widen_points_per_overconfidence: float = 20.0


@dataclass(frozen=True)
class QueueConfig:
    formula: str
    weight_of_tag: str
    mastery_definition: str
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Taxonomy:
    exam: str
    format_as_of: str
    scoring: Scoring
    sections: list[Section]
    topics: list[Topic]
    cross_cutting: list[CrossCuttingSkill]
    flaw_catalog: list[str]
    coverage: Coverage
    give_up: GiveUp
    readiness: ReadinessConfig
    queue: QueueConfig
    structures: list[Structure] = field(default_factory=list)
    diction: list[str] = field(default_factory=list)

    # -- lookups ---------------------------------------------------------------

    def section_by_id(self, section_id: str) -> Section:
        for s in self.sections:
            if s.id == section_id:
                return s
        raise KeyError(f"unknown section: {section_id!r}")

    def topic_by_id(self, node_id: str) -> Topic:
        for t in self.topics:
            if t.id == node_id:
                return t
        raise KeyError(f"unknown topic: {node_id!r}")

    @property
    def question_types(self) -> list[Topic]:
        return [t for t in self.topics if t.is_question_type]

    def question_types_for(self, section_id: str) -> list[Topic]:
        return [t for t in self.question_types if t.section == section_id]

    @property
    def coverage_node_ids(self) -> list[str]:
        """The coverage denominator: the scored question-type leaves."""
        return [t.id for t in self.question_types]

    @property
    def coverage_tags(self) -> list[str]:
        return [t.tag for t in self.question_types]

    def weight_of_node(self, node_id: str) -> float:
        """``exam_weight`` for a question type, else ``study_weight``.

        Flaw-catalog subtypes share the ``lr.flaw`` question-type weight (they are
        subskills under Flaw, not separate scored types).
        """
        topics = {t.id: t for t in self.topics}
        if node_id in topics:
            return topics[node_id].exam_weight
        if node_id in set(self.flaw_catalog):
            return topics["lr.flaw"].exam_weight if "lr.flaw" in topics else 0.0
        for c in self.cross_cutting:
            if c.id == node_id:
                return c.study_weight
        if node_id in set(self.diction):
            return DICTION_STUDY_WEIGHT
        return 0.0

    def weight_of_tag(self, tag: str) -> float:
        return self.weight_of_node(tag_to_node_id(tag))

    def validate(self) -> list[str]:
        """Return human-readable warnings (does not raise).

        Cheap sanity checks so a mis-edited YAML is caught early rather than
        silently skewing the coverage map or readiness composition.
        """
        warnings: list[str] = []
        qt_sum = sum(t.exam_weight for t in self.question_types)
        if abs(qt_sum - 1.0) > 0.05:
            warnings.append(
                f"scored question_type exam_weights sum to {qt_sum:.3f}; expected ~1.0"
            )
        section_ids = {s.id for s in self.sections}
        for t in self.topics:
            if t.section not in section_ids:
                warnings.append(
                    f"topic {t.id!r} references unknown section {t.section!r}"
                )
        return warnings


def _scoring_from(data: dict[str, Any]) -> Scoring:
    s = data["scoring"]
    scale = tuple(int(x) for x in s["scale"])
    return Scoring(
        scale=(scale[0], scale[1]),
        scored_sections=list(s["scored_sections"]),
        scored_questions_estimate=int(s["scored_questions_estimate"]),
        measurement_band_points=int(s["measurement_band_points"]),
        equating=bool(s["equating"]),
    )


def _give_up_from(data: dict[str, Any]) -> GiveUp:
    g = data["give_up"]
    r = g["readiness"]
    return GiveUp(
        readiness=ReadinessGiveUp(
            min_graded_performance_items=int(r["min_graded_performance_items"]),
            min_lr_question_type_coverage=float(r["min_lr_question_type_coverage"]),
            require_each_rc_question_type=bool(r["require_each_rc_question_type"]),
            min_timed_items=int(r["min_timed_items"]),
            max_heldout_calibration_ece=float(r["max_heldout_calibration_ece"]),
            max_student_overconfidence=float(r.get("max_student_overconfidence", 0.15)),
            min_primitive_coverage=float(r.get("min_primitive_coverage", 0.50)),
        ),
        memory_min_reviews_per_topic_for_display=int(
            g["memory"]["min_reviews_per_topic_for_display"]
        ),
    )


def load_taxonomy(path: str | Path | None = None) -> Taxonomy:
    """Parse the taxonomy YAML into a :class:`Taxonomy`."""
    path = Path(path) if path is not None else DEFAULT_TAXONOMY_PATH
    with open(path, encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh)

    sections = [
        Section(
            id=s["id"],
            name=s["name"],
            exam_weight=float(s["exam_weight"]),
            scored_questions_estimate=int(s["scored_questions_estimate"]),
        )
        for s in data["sections"]
    ]

    topics = [
        Topic(
            id=t["id"],
            section=t["section"],
            kind=t["kind"],
            name=t["name"],
            within_section_weight=float(t["within_section_weight"]),
            exam_weight=float(t["exam_weight"]),
            stem_cues=list(t.get("stem_cues", [])),
            subtypes_ref=t.get("subtypes_ref"),
        )
        for t in data["topics"]
    ]

    cross_cutting = [
        CrossCuttingSkill(
            id=c["id"],
            name=c["name"],
            study_weight=float(c["study_weight"]),
            appears_in=list(c.get("appears_in", [])),
            note=c.get("note"),
        )
        for c in data.get("cross_cutting", [])
    ]

    flaw_catalog = [f["id"] for f in data.get("flaw_catalog", [])]

    diction = [d["id"] for d in data.get("diction", [])]

    structures = [
        Structure(
            id=s["id"],
            name=s["name"],
            appears_in=list(s.get("appears_in", [])),
        )
        for s in data.get("structures", [])
    ]

    cov = data["coverage"]
    coverage = Coverage(
        basis=cov["basis"],
        min_graded_items_to_count=int(cov["min_graded_items_to_count"]),
    )

    rd = data["readiness"]
    ru = data.get("readiness_uncertainty", {})
    readiness = ReadinessConfig(
        min_range_points=int(rd["min_range_points"]),
        required_display_fields=list(rd["required_display_fields"]),
        widen_points_per_overconfidence=float(
            ru.get("widen_points_per_overconfidence", 20.0)
        ),
    )

    q = data["queue"]
    queue = QueueConfig(
        formula=q["formula"],
        weight_of_tag=q["weight_of_tag"],
        mastery_definition=q["mastery_definition"],
        notes=list(q.get("notes", [])),
    )

    return Taxonomy(
        exam=data["exam"],
        format_as_of=str(data["format_as_of"]),
        scoring=_scoring_from(data),
        sections=sections,
        topics=topics,
        cross_cutting=cross_cutting,
        flaw_catalog=flaw_catalog,
        coverage=coverage,
        give_up=_give_up_from(data),
        readiness=readiness,
        queue=queue,
        structures=structures,
        diction=diction,
    )


def _main() -> None:
    tax = load_taxonomy()
    print(f"exam: {tax.exam} (format as of {tax.format_as_of})")
    print(
        f"scale: {tax.scoring.scale}, scored questions ~{tax.scoring.scored_questions_estimate}"
    )
    print(f"sections: {', '.join(f'{s.id}={s.exam_weight}' for s in tax.sections)}")
    print(f"scored question types: {len(tax.question_types)}")
    print(
        f"  LR: {len(tax.question_types_for('lr'))}, RC: {len(tax.question_types_for('rc'))}"
    )
    print(
        f"cross-cutting skills: {len(tax.cross_cutting)}, flaw catalog: {len(tax.flaw_catalog)}"
    )
    print("example tag mappings:")
    for node_id in ("lr.weaken", "flaw.causal", "skill.conditional_logic"):
        tag = node_id_to_tag(node_id)
        print(f"  {node_id:24} -> {tag:34} weight={tax.weight_of_node(node_id):.3f}")
    warnings = tax.validate()
    if warnings:
        print("VALIDATION WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("validation: OK")


if __name__ == "__main__":
    _main()
