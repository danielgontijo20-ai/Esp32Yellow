"""Pipeline do Audio Builder: JSON → narrativa → Kokoro → WAV → MP3."""

from __future__ import annotations

import json
import time
from pathlib import Path

from . import config
from .convert import probe_duration_seconds, wav_to_mp3
from .kokoro_engine import KokoroEngine
from .narrative import build_narrative_from_segments
from .report import AudioItemResult, AudioReport, write_audio_report


def find_latest_build(output_root: Path | None = None) -> Path:
    """Retorna o diretório build_* mais recente em output/."""
    root = Path(output_root or (config.PROJECT_ROOT / "output"))
    builds = sorted(root.glob("build_*"), key=lambda p: p.name)
    if not builds:
        raise FileNotFoundError(
            f"Nenhum build encontrado em {root}. "
            "Execute o Content Builder antes do Audio Builder."
        )
    return builds[-1]


def resolve_lessons_dir(build_dir: Path | None = None) -> Path:
    if build_dir is not None:
        lessons = Path(build_dir) / "lessons"
    elif config.LESSONS_BUILD_DIR is not None:
        lessons = Path(config.LESSONS_BUILD_DIR) / "lessons"
    else:
        lessons = find_latest_build() / "lessons"

    if not lessons.is_dir():
        raise FileNotFoundError(f"Pasta de lições não encontrada: {lessons}")
    return lessons


def lesson_json_path(lessons_dir: Path, lesson_id: int) -> Path:
    return lessons_dir / f"{lesson_id:03d}" / "lesson.json"


def load_lesson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def list_all_lesson_ids(lessons_dir: Path) -> list[int]:
    ids: list[int] = []
    for folder in sorted(lessons_dir.glob("*")):
        if folder.is_dir() and (folder / "lesson.json").exists():
            try:
                ids.append(int(folder.name))
            except ValueError:
                continue
    return ids


def generate_lesson_audio(
    lesson: dict,
    output_file: Path,
    engine: KokoroEngine,
    *,
    keep_wav: bool = False,
) -> AudioItemResult:
    """Gera um arquivo de áudio para uma lição."""
    lesson_id = int(lesson["id"])
    filename = output_file.name

    try:
        segments = lesson.get("segments") or []
        narrative = build_narrative_from_segments(segments)
        if not narrative.strip():
            raise ValueError("Segments vazios — nada para narrar.")

        output_file.parent.mkdir(parents=True, exist_ok=True)
        config.TEMP_WAV_DIR.mkdir(parents=True, exist_ok=True)
        wav_path = config.TEMP_WAV_DIR / f"{lesson_id:03d}.wav"

        _, duration = engine.synthesize_to_wav(narrative, wav_path)

        fmt = config.OUTPUT_FORMAT.lower()
        if fmt == "mp3":
            wav_to_mp3(wav_path, output_file)
            if not keep_wav and wav_path.exists():
                wav_path.unlink()
            duration = probe_duration_seconds(output_file) or duration
        elif fmt == "wav":
            # Copia/move o WAV para o destino final
            output_file.write_bytes(wav_path.read_bytes())
            if not keep_wav and wav_path.exists() and wav_path.resolve() != output_file.resolve():
                wav_path.unlink()
        else:
            raise ValueError(f"Formato não suportado: {config.OUTPUT_FORMAT}")

        size = output_file.stat().st_size if output_file.exists() else 0
        return AudioItemResult(
            lesson_id=lesson_id,
            filename=filename,
            status="OK",
            duration_sec=duration,
            size_bytes=size,
        )
    except Exception as exc:  # noqa: BLE001 — registrar no relatório
        return AudioItemResult(
            lesson_id=lesson_id,
            filename=filename,
            status="ERRO",
            error=str(exc),
        )


def run_audio_build(
    *,
    mode: str | None = None,
    build_dir: Path | None = None,
    log_callback=None,
) -> AudioReport:
    """Executa o pipeline completo (teste ou full)."""

    def log(msg: str) -> None:
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    mode = (mode or config.MODE).lower().strip()
    if mode not in {"test", "full"}:
        raise ValueError("MODE deve ser 'test' ou 'full'.")

    lessons_dir = resolve_lessons_dir(build_dir)
    log(f"Lições em: {lessons_dir}")

    if mode == "test":
        lesson_ids = list(config.TEST_LESSON_IDS)
        out_dir = config.OUTPUT_DIR_TEST
    else:
        lesson_ids = list_all_lesson_ids(lessons_dir)
        out_dir = config.OUTPUT_DIR_FULL

    out_dir.mkdir(parents=True, exist_ok=True)
    ext = config.OUTPUT_FORMAT.lower()

    log(f"Modo: {mode.upper()}")
    log(f"Voz: {config.VOICE} (lang={config.LANG_CODE})")
    log(f"Formato: {ext} @ {config.SAMPLE_RATE} Hz, bitrate={config.MP3_BITRATE}")
    log(f"Saída: {out_dir}")
    log(f"Lições: {lesson_ids}")

    engine = KokoroEngine()
    report = AudioReport(mode=mode)
    started = time.perf_counter()

    for lesson_id in lesson_ids:
        json_path = lesson_json_path(lessons_dir, lesson_id)
        out_file = out_dir / f"{lesson_id:03d}.{ext}"
        log(f"→ Processando {json_path.name} → {out_file.name}")

        if not json_path.exists():
            item = AudioItemResult(
                lesson_id=lesson_id,
                filename=out_file.name,
                status="ERRO",
                error=f"JSON não encontrado: {json_path}",
            )
        else:
            lesson = load_lesson(json_path)
            item = generate_lesson_audio(lesson, out_file, engine)

        report.items.append(item)
        if item.status == "OK":
            log(
                f"  OK  {item.filename}  "
                f"{item.duration_sec:.1f}s  {item.size_bytes} bytes"
            )
        else:
            log(f"  ERRO  {item.filename}: {item.error}")

    report.elapsed_sec = time.perf_counter() - started
    report_path = out_dir / "report.txt"
    write_audio_report(report, report_path)
    log(f"Relatório: {report_path}")
    return report
