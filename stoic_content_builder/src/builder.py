"""Geração de arquivos JSON, pastas de build e relatório."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import Lesson, ParseReport
from .parser import parse_text
from .validator import validate_all


def create_build_dir(output_root: Path) -> Path:
    """Cria uma pasta de build exclusiva com timestamp.

    Nunca apaga builds anteriores.
    """
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    build_dir = output_root / f"build_{stamp}"

    # Evita colisão no mesmo segundo
    suffix = 1
    while build_dir.exists():
        build_dir = output_root / f"build_{stamp}_{suffix}"
        suffix += 1

    build_dir.mkdir(parents=True, exist_ok=False)
    (build_dir / "lessons").mkdir()
    return build_dir


def write_lesson_json(lesson: Lesson, lessons_dir: Path) -> Path:
    """Escreve lesson.json em lessons/NNN/."""
    folder = lessons_dir / f"{lesson.id:03d}"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "lesson.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(lesson.to_dict(), fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def format_report(report: ParseReport) -> str:
    """Monta o texto de output/report.txt."""
    lines: list[str] = []
    lines.append("=" * 40)
    lines.append("DIÁRIO ESTOICO — CONTENT BUILDER")
    lines.append("=" * 40)
    lines.append("")
    lines.append("Arquivo:")
    lines.append(report.input_file)
    lines.append("")
    lines.append(f"Lições encontradas: {report.lessons_found}")
    lines.append("")
    lines.append("Primeira lição:")
    lines.append(report.first_date or "(nenhuma)")
    lines.append("")
    lines.append("Última lição:")
    lines.append(report.last_date or "(nenhuma)")
    lines.append("")
    lines.append(f"Erros: {report.error_count()}")
    lines.append(f"Avisos: {report.warning_count()}")
    lines.append("")

    if report.duplicate_dates:
        lines.append("DATAS DUPLICADAS")
        lines.append("-" * 40)
        for d in report.duplicate_dates:
            lines.append(f"- {d}")
        lines.append("")

    if report.missing_dates:
        lines.append("DATAS AUSENTES (no intervalo)")
        lines.append("-" * 40)
        # Limita listagem muito longa
        shown = report.missing_dates[:50]
        for d in shown:
            lines.append(f"- {d}")
        if len(report.missing_dates) > 50:
            lines.append(f"... e mais {len(report.missing_dates) - 50}")
        lines.append("")

    if report.sequence_issues:
        lines.append("PROBLEMAS DE SEQUÊNCIA")
        lines.append("-" * 40)
        for msg in report.sequence_issues:
            lines.append(f"- {msg}")
        lines.append("")

    # Agrupa avisos/erros por lição
    warning_items = [i for i in report.issues if i.level == "warning"]
    error_items = [i for i in report.issues if i.level == "error"]
    global_warns = list(report.warnings)

    if warning_items or global_warns:
        lines.append("AVISOS")
        lines.append("-" * 40)
        for w in global_warns:
            lines.append(w)
            lines.append("")
        # Agrupar por lesson_id
        by_lesson: dict[int | None, list[str]] = {}
        for item in warning_items:
            by_lesson.setdefault(item.lesson_id, []).append(item.message)
        for lid in sorted(by_lesson.keys(), key=lambda x: (x is None, x or 0)):
            msgs = by_lesson[lid]
            if lid is None:
                for m in msgs:
                    lines.append(m)
                    lines.append("")
            else:
                lines.append(f"Lição {lid}:")
                for m in msgs:
                    lines.append(m)
                lines.append("")

    if error_items or report.errors:
        lines.append("ERROS")
        lines.append("-" * 40)
        for e in report.errors:
            lines.append(e)
            lines.append("")
        by_lesson_e: dict[int | None, list[str]] = {}
        for item in error_items:
            by_lesson_e.setdefault(item.lesson_id, []).append(item.message)
        for lid in sorted(by_lesson_e.keys(), key=lambda x: (x is None, x or 0)):
            msgs = by_lesson_e[lid]
            if lid is None:
                for m in msgs:
                    lines.append(m)
                    lines.append("")
            else:
                lines.append(f"Lição {lid}:")
                for m in msgs:
                    lines.append(m)
                lines.append("")

    lines.append("VALIDAÇÃO")
    lines.append("-" * 40)
    lines.append(f"Lições válidas: {report.valid_lessons}")
    lines.append(f"Lições com problemas: {report.problem_lessons}")
    lines.append("")
    lines.append("STATUS FINAL")
    lines.append("-" * 40)
    if report.lessons_found == 0:
        lines.append("PROCESSAMENTO FALHOU — NENHUMA LIÇÃO")
    elif report.error_count() > 0:
        lines.append("PROCESSAMENTO CONCLUÍDO COM ERROS")
    elif report.warning_count() > 0:
        lines.append("PROCESSAMENTO CONCLUÍDO COM AVISOS")
    else:
        lines.append("PROCESSAMENTO CONCLUÍDO")
    lines.append("=" * 40)
    lines.append("")
    return "\n".join(lines)


def write_report(report: ParseReport, build_dir: Path) -> Path:
    """Grava report.txt no diretório do build."""
    path = build_dir / "report.txt"
    content = format_report(report)
    path.write_text(content, encoding="utf-8")
    return path


class BuildResult:
    """Resultado de uma execução do builder."""

    def __init__(
        self,
        build_dir: Path,
        lessons: list[Lesson],
        report: ParseReport,
        report_path: Path,
    ) -> None:
        self.build_dir = build_dir
        self.lessons = lessons
        self.report = report
        self.report_path = report_path


def process_file(
    input_path: Path,
    output_root: Path,
    log_callback=None,
) -> BuildResult:
    """Pipeline completo: ler → limpar/parsear → validar → gravar.

    Nunca apaga builds anteriores.
    Continua mesmo com problemas em algumas lições.
    """

    def log(msg: str) -> None:
        if log_callback:
            log_callback(msg)

    input_path = Path(input_path)
    output_root = Path(output_root)

    log(f"Lendo arquivo: {input_path}")
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

    raw = input_path.read_text(encoding="utf-8")
    if not raw.strip():
        raise ValueError("O arquivo TXT está vazio.")

    log("Limpando OCR e identificando lições...")
    lessons, global_warnings = parse_text(raw)

    if not lessons:
        raise ValueError(
            "Nenhuma lição encontrada. Verifique se o TXT contém datas "
            "no formato '1° de janeiro', '2 de janeiro', etc."
        )

    log(f"Lições encontradas: {len(lessons)}")
    log("Validando...")
    report = validate_all(lessons, input_path.name, global_warnings)

    log("Criando pasta de build...")
    build_dir = create_build_dir(output_root)
    lessons_dir = build_dir / "lessons"

    log("Gerando arquivos JSON...")
    for lesson in lessons:
        path = write_lesson_json(lesson, lessons_dir)
        log(f"  → {path.relative_to(build_dir)}")

    report_path = write_report(report, build_dir)
    log(f"Relatório: {report_path}")
    log(f"Build concluído em: {build_dir}")

    return BuildResult(
        build_dir=build_dir,
        lessons=lessons,
        report=report,
        report_path=report_path,
    )
