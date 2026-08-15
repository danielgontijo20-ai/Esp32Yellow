"""Validação das lições processadas."""

from __future__ import annotations

from collections import Counter

from .models import Lesson, ParseReport, ValidationIssue
from .parser import DAYS_IN_MONTH_LEAP, MONTHS, date_to_day_of_year, format_date_display


def validate_lesson(lesson: Lesson) -> list[ValidationIssue]:
    """Valida campos obrigatórios de uma única lição."""
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
        issues.append(ValidationIssue("error", lid, "Campo 'quote.text' vazio."))

    if not lesson.quote.source or not lesson.quote.source.strip():
        issues.append(ValidationIssue("error", lid, "Campo 'quote.source' vazio."))

    if not lesson.text or not lesson.text.strip():
        issues.append(ValidationIssue("error", lid, "Campo 'text' vazio."))

    if not lesson.segments:
        issues.append(
            ValidationIssue("warning", lid, "Nenhum segmento gerado.")
        )
    else:
        allowed_types = {"quote", "source", "text"}
        seen_types: list[str] = []
        for seg in lesson.segments:
            if not seg.text or not seg.text.strip():
                issues.append(
                    ValidationIssue(
                        "error", lid, f"Segmento {seg.id} com texto vazio."
                    )
                )
            if seg.type not in allowed_types:
                issues.append(
                    ValidationIssue(
                        "error",
                        lid,
                        f"Segmento {seg.id} com type inválido: {seg.type!r}",
                    )
                )
            else:
                seen_types.append(seg.type)

        # Ordem esperada da narração: quote → source → text
        if seen_types:
            order_rank = {"quote": 0, "source": 1, "text": 2}
            ranks = [order_rank[t] for t in seen_types]
            if ranks != sorted(ranks):
                issues.append(
                    ValidationIssue(
                        "warning",
                        lid,
                        "Segmentos fora da ordem quote → source → text.",
                    )
                )
            if "quote" not in seen_types and lesson.quote.text.strip():
                issues.append(
                    ValidationIssue(
                        "warning", lid, "Citação não aparece nos segmentos."
                    )
                )
            if "source" not in seen_types and lesson.quote.source.strip():
                issues.append(
                    ValidationIssue(
                        "warning", lid, "Fonte não aparece nos segmentos."
                    )
                )

    # Propaga avisos/erros do parser
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

    # Mapa inverso id -> data legível
    id_to_date: dict[int, str] = {}
    for month in MONTHS:
        for day in range(1, DAYS_IN_MONTH_LEAP[month] + 1):
            doy = date_to_day_of_year(day, month)
            # Preferir "1°" apenas para o dia 1 (convenção do livro)
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

    # Avisos de contagem esperada (366 no livro completo)
    if len(lessons) < 366:
        report.warnings.append(
            f"Livro completo espera 366 lições; encontradas {len(lessons)}."
        )

    return report
