"""
Deterministic rule-based scorer.
Pure function: (detected_answers, answer_key) → ScoreResult.
No ML, no approximation — same inputs always produce same outputs.
"""
from dataclasses import dataclass, field
from typing import Dict

SECTIONS = {
    "intelligence": range(1, 11),
    "science": range(11, 21),
    "social": range(21, 31),
    "math": range(31, 41),
}


@dataclass
class QuestionResult:
    q_no: int
    correct_answer: str
    marked_answer: str   # "", "MULTI", or "A"/"B"/"C"/"D"
    is_correct: bool
    points: int          # 1 or 0


@dataclass
class ScoreResult:
    per_question: Dict[int, QuestionResult]
    sections: Dict[str, int]   # intelligence, science, social, math, total


def score_sheet(
    detected: Dict[int, str],   # {q_no: answer}
    answer_key: Dict[str, str], # {"q1": "A", ...}
) -> ScoreResult:
    """
    Score a sheet against the answer key.
    detected[q] may be "", "MULTI", or "A"/"B"/"C"/"D".
    Only an exact single-option match scores 1 point.
    """
    per_question: Dict[int, QuestionResult] = {}

    for q in range(1, 41):
        key_str = f"q{q}"
        correct = answer_key.get(key_str, "")
        marked = detected.get(q, "")

        is_correct = (
            marked != ""
            and marked != "MULTI"
            and marked == correct
        )

        per_question[q] = QuestionResult(
            q_no=q,
            correct_answer=correct,
            marked_answer=marked,
            is_correct=is_correct,
            points=1 if is_correct else 0,
        )

    sections: Dict[str, int] = {}
    for section_name, q_range in SECTIONS.items():
        sections[section_name] = sum(per_question[q].points for q in q_range)
    sections["total"] = sum(sections.values())

    return ScoreResult(per_question=per_question, sections=sections)
