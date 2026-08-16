"""Validação das lições processadas."""

from __future__ import annotations

import re
from collections import Counter

from .models import Lesson, ParseReport, ValidationIssue
from .parser import DAYS_IN_MONTH_LEAP, MONTHS, date_to_day_of_year, format_date_display


def _normalize_content(text: str) -> str:
    """Normaliza espaços/quebras para comparação segments ↔ text."""
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def validate_lesson(lesson: Lesson) -> list[ValidationIssue]:
    """Valida campos obrigatórios e regras de segments de uma lição."""
    issues: list[ValidationIssue] = []
    lid = lesson.id

    # 1) Campos obrigatórios da lição
    if lesson.id < 1 or lesson.id > 366:
        issues.append(
            ValidationIssue("error", lid, f"ID fora do intervalo 1–366: {lesson.id}")
        )

    if not lesson.date or not lesson.date.strip():
        issues.append(ValidationIssue("error", lid, "Campo 'date' vazio."))

    if not lesson.title or not lesson.title.strip():
        issues.append(ValidationIssue("error", lid, "Campo 'title' vazio."))

    # 2) quote.text / quote.source
    if not lesson.quote.text or not lesson.quote.text.strip():
        issues.append(ValidationIssue("error", lid, "Campo 'quote.text' vazio."))

    if not lesson.quote.source or not lesson.quote.source.strip():
        issues.append(ValidationIssue("error", lid, "Campo 'quote.source' vazio."))

    if not lesson.text or not lesson.text.strip():
        issues.append(ValidationIssue("error", lid, "Campo 'text' vazio."))

    if not lesson.segments:
        issues.append(
            ValidationIssue("error", lid, "Campo 'segments' vazio.")
        )
    else:
        for seg in lesson.segments:
            # 3) Proibido type quote/source nos segments
            if seg.type in ("quote", "source"):
                issues.append(
                    ValidationIssue(
                        "error",
                        lid,
                        f"Segmento {seg.id} com type={seg.type!r}; "
                        "citação deve existir só em quote.",
                    )
                )
            # 4) Todo segment: id, type=text, text
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

            # 5) Não terminar no meio de uma palavra (hífen de OCR residual)
            if re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]-$", seg.text.rstrip()):
                issues.append(
                    ValidationIssue(
                        "error",
                        lid,
                        f"Segmento {seg.id} termina no meio de uma palavra "
                        "(hífen residual).",
                    )
                )

            # 6) Não terminar com quebra artificial de OCR
            if seg.text.endswith("\n") or seg.text.endswith("\r"):
                issues.append(
                    ValidationIssue(
                        "error",
                        lid,
                        f"Segmento {seg.id} termina com quebra de linha "
                        "artificial.",
                    )
                )

        # 7) Conteúdo concatenado dos segments ≈ reflexão (normalizado)
        if lesson.text.strip() and lesson.segments:
            seg_blob = _normalize_content(
                " ".join(s.text for s in lesson.segments if s.text)
            )
            text_blob = _normalize_content(lesson.text)
            if seg_blob != text_blob:
                issues.append(
                    ValidationIssue(
                        "error",
                        lid,
                        "Conteúdo dos segments não corresponde ao campo "
                        "'text' (após normalizar espaços/quebras).",
                    )
                )

    # 8) text permanece disponível independentemente (já validado acima)

    # Propaga avisos/erros do parser
    for w in lesson.warnings:
        # Título multilinha por OCR não é erro
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
