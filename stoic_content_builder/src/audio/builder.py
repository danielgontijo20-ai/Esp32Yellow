"""Pipeline do Audio Builder: JSON → narrativa → Kokoro → WAV → MP3."""

from __future__ import annotations

import json
import time
from pathlib import Path

from . import config
from .convert import ffmpeg_available, probe_duration_seconds, wav_to_mp3
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
            if not ffmpeg_available():
                # Fallback automático: salva WAV com o mesmo número de lição
                wav_out = output_file.with_suffix(".wav")
                wav_out.write_bytes(wav_path.read_bytes())
                if not keep_wav and wav_path.exists() and wav_path.resolve() != wav_out.resolve():
                    wav_path.unlink()
                size = wav_out.stat().st_size
                return AudioItemResult(
                    lesson_id=lesson_id,
                    filename=wav_out.name,
                    status="OK",
                    duration_sec=duration,
                    size_bytes=size,
                    error="ffmpeg ausente — salvo como WAV",
                )
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


def load_lesson_from_txt(path: Path) -> dict:
    """Parseia um TXT de lição com o parser do Content Builder.

    Não altera o arquivo. Retorna o dict no mesmo formato do lesson.json.
    """
    from src.parser import parse_text

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        raise ValueError(f"Arquivo vazio: {path.name}")

    lessons, _warnings = parse_text(raw)
    if not lessons:
        raise ValueError(
            f"Nenhuma lição encontrada em {path.name}. "
            "Verifique se o TXT contém data no formato '1° de janeiro'."
        )

    # Um TXT da GUI = uma lição (usa a primeira se houver mais)
    lesson = lessons[0]
    data = lesson.to_dict()
    return data


def peek_txt_label(path: Path) -> str:
    """Rótulo amigável para a lista da GUI: '001.txt — data — título'."""
    path = Path(path)
    try:
        lesson = load_lesson_from_txt(path)
        date = lesson.get("date") or "?"
        title = lesson.get("title") or "?"
        return f"{path.name} — {date} — {title}"
    except Exception as exc:  # noqa: BLE001
        return f"{path.name} — (erro ao ler: {exc})"


def resolve_output_stem(txt_path: Path, lesson: dict) -> str:
    """Nome base do áudio: preferir 001 do arquivo; senão id da lição."""
    stem = Path(txt_path).stem.strip()
    if stem.isdigit():
        return f"{int(stem):03d}"
    return f"{int(lesson['id']):03d}"


def run_audio_from_txt_files(
    txt_paths: list[Path],
    output_dir: Path,
    *,
    voice: str | None = None,
    log_callback=None,
    progress_callback=None,
) -> AudioReport:
    """Gera áudios a partir de uma lista de TXT (usado pela GUI e testes).

    Reutiliza generate_lesson_audio / KokoroEngine.
    Não sobrescreve arquivos existentes — a GUI deve filtrar antes.
    """

    def log(msg: str) -> None:
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    def progress(current: int, total: int, message: str) -> None:
        if progress_callback:
            progress_callback(current, total, message)

    # Aplica voz sem alterar o default permanente do módulo se None
    previous_voice = config.VOICE
    if voice:
        config.VOICE = voice

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = config.OUTPUT_FORMAT.lower()
    paths = [Path(p) for p in txt_paths]

    report = AudioReport(mode="gui")
    started = time.perf_counter()
    total = len(paths)

    log("Iniciando geração...")
    log(f"Voz: {config.VOICE} (lang={config.LANG_CODE})")
    log(f"Formato: {ext} @ {config.SAMPLE_RATE} Hz")
    log(f"Saída: {out_dir}")
    if ext == "mp3" and not ffmpeg_available():
        log("AVISO: ffmpeg não encontrado — fallback para WAV.")

    try:
        engine = KokoroEngine()
        for index, txt_path in enumerate(paths, start=1):
            progress(index - 1, total, f"Gerando: {txt_path.name}")
            log(f"[{index}/{total}] {txt_path.name}")

            try:
                lesson = load_lesson_from_txt(txt_path)
                stem = resolve_output_stem(txt_path, lesson)
                # Garante id coerente com o nome do arquivo de saída
                lesson = dict(lesson)
                lesson["id"] = int(stem)
                out_file = out_dir / f"{stem}.{ext}"

                if out_file.exists():
                    item = AudioItemResult(
                        lesson_id=int(stem),
                        filename=out_file.name,
                        status="ERRO",
                        error=f"Arquivo já existe (não sobrescrito): {out_file.name}",
                    )
                else:
                    item = generate_lesson_audio(lesson, out_file, engine)

                report.items.append(item)
                if item.status == "OK":
                    from .report import format_bytes, format_duration

                    log(f"Áudio gerado: {item.filename}")
                    log(f"Duração: {format_duration(item.duration_sec)}")
                    log(f"Tamanho: {format_bytes(item.size_bytes)}")
                    progress(index, total, f"Concluído: {item.filename}")
                else:
                    log(f"ERRO: {item.error}")
                    progress(index, total, f"Erro: {txt_path.name}")
            except Exception as exc:  # noqa: BLE001
                item = AudioItemResult(
                    lesson_id=0,
                    filename=txt_path.name,
                    status="ERRO",
                    error=str(exc),
                )
                report.items.append(item)
                log(f"ERRO: {exc}")
                progress(index, total, f"Erro: {txt_path.name}")
    finally:
        config.VOICE = previous_voice

    report.elapsed_sec = time.perf_counter() - started
    report_path = out_dir / "report.txt"
    write_audio_report(report, report_path)
    log("Processamento concluído.")
    log(f"Relatório: {report_path}")
    progress(total, total, "Concluído")
    return report


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
    if ext == "mp3" and not ffmpeg_available():
        log(
            "AVISO: ffmpeg não encontrado no PATH. "
            "Os arquivos serão salvos como .wav (fallback)."
        )
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
