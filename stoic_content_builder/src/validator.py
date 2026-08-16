"""Validação das lições processadas."""

from __future__ import annotations

import re
from collections import Counter

from .models import Lesson, ParseReport, ValidationIssue
from .parser import (
    DAYS_IN_MONTH_LEAP,
    MONTHS,
    NARRATION_TRANSITION,
    date_to_day_of_year,
    format_date_display,
    reflection_blocks,
    title_for_narration,
)


def _normalize_content(text: str) -> str:
    """Normaliza espaços/quebras para comparação de conteúdo."""
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def validate_lesson(lesson: Lesson) -> list[ValidationIssue]:
    """Valida campos obrigatórios e o roteiro narrativo em segments."""
    issues: list[ValidationIssue] = []
    lid = lesson.id

    if lesson.id < 1 or lesson.id > 366:
        issues.append(
            ValidationIssue("error", lid, f"ID fora do intervalo 1–366: {lesson.id}")
        )

    if not lesson.date or not lesson.date.strip():
        issues.append(ValidationIssue("error", lid, "Campo 'date' vazio."))

    if not lesson.title or not lesson.title.strip():
        issues.append(ValidationIssue("error", lid, "Campo 'title' vazio."))

    if not lesson.quote.text or not lesson.quote.text.strip():
        issues.append(
            ValidationIssue(
                "error",
                lid,
                f"Lição {lid}: campo 'quote.text' vazio ou ausente.",
            )
        )

    if not lesson.quote.source or not lesson.quote.source.strip():
        issues.append(ValidationIssue("error", lid, "Campo 'quote.source' vazio."))

    if not lesson.quote.philosopher or not lesson.quote.philosopher.strip():
        issues.append(
            ValidationIssue(
                "error",
                lid,
                f"Lição {lid}: campo 'quote.philosopher' ausente ou vazio.",
            )
        )

    if not lesson.text or not lesson.text.strip():
        issues.append(ValidationIssue("error", lid, "Campo 'text' vazio."))

    if not lesson.segments:
        issues.append(ValidationIssue("error", lid, "Campo 'segments' vazio."))
    else:
        for seg in lesson.segments:
            if seg.type in ("quote", "source"):
                issues.append(
                    ValidationIssue(
                        "error",
                        lid,
                        f"Segmento {seg.id} com type={seg.type!r}; "
                        "use apenas type='text' no roteiro.",
                    )
                )
            elif seg.type != "text":
                issues.append(
                    ValidationIssue(
                        "error",
                        lid,
                        f"Segmento {seg.id} com type inválido: {seg.type!r} "
                        "(esperado 'text').",
                    )
                )

            if seg.id < 1:
                issues.append(
                    ValidationIssue(
                        "error", lid, f"Segmento com id inválido: {seg.id}"
                    )
                )

            if not seg.text or not seg.text.strip():
                issues.append(
                    ValidationIssue(
                        "error", lid, f"Segmento {seg.id} com texto vazio."
                    )
                )
                continue

            if re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]-$", seg.text.rstrip()):
                issues.append(
                    ValidationIssue(
                        "error",
                        lid,
                        f"Segmento {seg.id} termina no meio de uma palavra "
                        "(hífen residual).",
                    )
                )

            if seg.text.endswith("\n") or seg.text.endswith("\r"):
                issues.append(
                    ValidationIssue(
                        "error",
                        lid,
                        f"Segmento {seg.id} termina com quebra de linha "
                        "artificial.",
                    )
                )

        # Roteiro: intro → título → citação → transição → comentários
        segs = lesson.segments
        phil = (lesson.quote.philosopher or "").strip()
        qt = (lesson.quote.text or "").strip()
        expected_prefix: list[str] = []
        if phil:
            expected_prefix.append(
                f"A lição deste momento é uma citação de {phil}."
            )
        if lesson.title.strip():
            expected_prefix.append(
                f"A lição se chama: {title_for_narration(lesson.title)}."
            )
        if qt:
            expected_prefix.append(qt)
        expected_prefix.append(NARRATION_TRANSITION)

        if len(segs) < len(expected_prefix):
            issues.append(
                ValidationIssue(
                    "error",
                    lid,
                    "Roteiro de segments incompleto "
                    "(faltam intro/título/citação/transição).",
                )
            )
        else:
            for i, expected in enumerate(expected_prefix):
                actual = segs[i].text.strip()
                if _normalize_content(actual) != _normalize_content(expected):
                    issues.append(
                        ValidationIssue(
                            "error",
                            lid,
                            f"Segmento {segs[i].id} fora da ordem/conteúdo "
                            f"esperado do roteiro narrativo.",
                        )
                    )

            comments = [s.text for s in segs[len(expected_prefix) :]]
            expected_comments = reflection_blocks(lesson.text)
            if [_normalize_content(c) for c in comments] != [
                _normalize_content(c) for c in expected_comments
            ]:
                issues.append(
                    ValidationIssue(
                        "error",
                        lid,
                        "Comentários nos segments não correspondem ao campo "
                        "'text' (após a transição).",
                    )
                )

            ids = [s.id for s in segs]
            if ids != list(range(1, len(segs) + 1)):
                issues.append(
                    ValidationIssue(
                        "error",
                        lid,
                        "IDs dos segments não estão sequenciais a partir de 1.",
                    )
                )

    for w in lesson.warnings:
        issues.append(ValidationIssue("warning", lid, w))
    for e in lesson.errors:
        issues.append(ValidationIssue("error", lid, e))

    return issues


def find_duplicate_dates(lessons: list[Lesson]) -> list[str]:
    """Retorna datas que aparecem mais de uma vez."""
    counts = Counter(lesson.date for lesson in lessons)
    return sorted([d for d, c in counts.items() if c > 1])


def find_duplicate_ids(lessons: list[Lesson]) -> list[int]:
    """Retorna IDs duplicados."""
    counts = Counter(lesson.id for lesson in lessons)
    return sorted([i for i, c in counts.items() if c > 1])


def find_missing_dates(lessons: list[Lesson]) -> list[str]:
    """Detecta datas ausentes no intervalo entre a primeira e a última lição.

    Usa o calendário bissexto (366 dias). Não exige o livro completo —
    apenas lacunas dentro do intervalo presente.
    """
    if len(lessons) < 2:
        return []

    ids_present = {lesson.id for lesson in lessons}
    min_id = min(ids_present)
    max_id = max(ids_present)

    id_to_date: dict[int, str] = {}
    for month in MONTHS:
        for day in range(1, DAYS_IN_MONTH_LEAP[month] + 1):
            doy = date_to_day_of_year(day, month)
            original = f"{day}° de {month}" if day == 1 else f"{day} de {month}"
            id_to_date[doy] = format_date_display(day, month, original)

    missing: list[str] = []
    for doy in range(min_id, max_id + 1):
        if doy not in ids_present:
            missing.append(id_to_date.get(doy, f"id={doy}"))
    return missing


def find_sequence_issues(lessons: list[Lesson]) -> list[str]:
    """Detecta problemas na sequência de IDs conforme ordem de aparição."""
    issues: list[str] = []
    if not lessons:
        return issues

    prev_id = lessons[0].id
    for lesson in lessons[1:]:
        if lesson.id < prev_id:
            issues.append(
                f"Ordem fora de sequência: id {lesson.id} ({lesson.date}) "
                f"aparece após id {prev_id}."
            )
        elif lesson.id == prev_id:
            issues.append(
                f"ID repetido em sequência: id {lesson.id} ({lesson.date})."
            )
        elif lesson.id > prev_id + 1:
            issues.append(
                f"Salto na sequência: de id {prev_id} para id {lesson.id} "
                f"({lesson.date})."
            )
        prev_id = lesson.id
    return issues


def validate_all(
    lessons: list[Lesson],
    input_file: str,
    global_warnings: list[str] | None = None,
) -> ParseReport:
    """Executa validação completa e monta o relatório."""
    report = ParseReport(input_file=input_file)
    report.lessons_found = len(lessons)

    if global_warnings:
        report.warnings.extend(global_warnings)

    if not lessons:
        report.errors.append("Nenhuma lição para validar.")
        return report

    report.first_date = lessons[0].date
    report.last_date = lessons[-1].date

    report.duplicate_dates = find_duplicate_dates(lessons)
    for d in report.duplicate_dates:
        report.issues.append(
            ValidationIssue("warning", None, f"Data duplicada: {d}")
        )

    dup_ids = find_duplicate_ids(lessons)
    for i in dup_ids:
        report.issues.append(
            ValidationIssue("error", i, f"ID de lição duplicado: {i}")
        )

    report.missing_dates = find_missing_dates(lessons)
    for d in report.missing_dates:
        report.issues.append(
            ValidationIssue("warning", None, f"Data ausente no intervalo: {d}")
        )

    report.sequence_issues = find_sequence_issues(lessons)
    for msg in report.sequence_issues:
        report.issues.append(ValidationIssue("warning", None, msg))

    problem_ids: set[int] = set()
    for lesson in lessons:
        lesson_issues = validate_lesson(lesson)
        report.issues.extend(lesson_issues)
        if any(i.level == "error" for i in lesson_issues):
            problem_ids.add(lesson.id)

    report.problem_lessons = len(problem_ids)
    report.valid_lessons = len(lessons) - report.problem_lessons

    if len(lessons) < 366:
        report.warnings.append(
            f"Livro completo espera 366 lições; encontradas {len(lessons)}."
        )

    return report
