"""Estruturas de dados do Diário Estoico — Content Builder."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Quote:
    """Citação atribuída a um filósofo."""

    text: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"text": self.text, "source": self.source}


@dataclass
class Segment:
    """Segmento curto do texto da reflexão."""

    id: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "text": self.text}


@dataclass
class Lesson:
    """Uma lição diária do diário estoico."""

    id: int
    date: str
    title: str
    quote: Quote
    text: str
    segments: list[Segment] = field(default_factory=list)
    # Metadados internos (não vão para o JSON final)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serializa apenas os campos públicos do lesson.json."""
        return {
            "id": self.id,
            "date": self.date,
            "title": self.title,
            "quote": self.quote.to_dict(),
            "text": self.text,
            "segments": [s.to_dict() for s in self.segments],
        }


@dataclass
class ValidationIssue:
    """Problema encontrado na validação."""

    level: str  # "error" | "warning"
    lesson_id: int | None
    message: str


@dataclass
class ParseReport:
    """Relatório consolidado do processamento."""

    input_file: str
    lessons_found: int = 0
    first_date: str = ""
    last_date: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    valid_lessons: int = 0
    problem_lessons: int = 0
    duplicate_dates: list[str] = field(default_factory=list)
    missing_dates: list[str] = field(default_factory=list)
    sequence_issues: list[str] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    def error_count(self) -> int:
        return len(self.errors) + sum(
            1 for i in self.issues if i.level == "error"
        )

    def warning_count(self) -> int:
        return len(self.warnings) + sum(
            1 for i in self.issues if i.level == "warning"
        )
