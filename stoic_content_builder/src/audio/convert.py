"""Conversão WAV → MP3 (ffmpeg) e utilitários de áudio."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import config


def ffmpeg_available() -> bool:
    """True se o executável ffmpeg estiver no PATH."""
    return shutil.which("ffmpeg") is not None


def require_ffmpeg() -> str:
    """Retorna o caminho do ffmpeg ou levanta erro claro no Windows."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    raise FileNotFoundError(
        "ffmpeg não encontrado no PATH.\n"
        "O Kokoro gera WAV; o MP3 depende do ffmpeg.\n\n"
        "Opções:\n"
        "  1) Instale o ffmpeg e reabra o Prompt:\n"
        "     https://www.gyan.dev/ffmpeg/builds/\n"
        "     (baixe 'ffmpeg-release-essentials.zip', extraia e adicione a pasta\n"
        "      'bin' ao PATH do Windows)\n"
        "  2) Ou gere WAV sem ffmpeg, em src/audio/config.py:\n"
        "     OUTPUT_FORMAT = \"wav\"\n"
        "     Depois: python generate_audio.py --mode test"
    )


def wav_to_mp3(
    wav_path: Path,
    mp3_path: Path,
    *,
    bitrate: str | None = None,
    sample_rate: int | None = None,
) -> Path:
    """Converte WAV em MP3 via ffmpeg (etapa separada da síntese)."""
    ffmpeg_bin = require_ffmpeg()
    wav_path = Path(wav_path)
    mp3_path = Path(mp3_path)
    mp3_path.parent.mkdir(parents=True, exist_ok=True)

    if not wav_path.exists():
        raise FileNotFoundError(f"WAV não encontrado para conversão: {wav_path}")

    bitrate = bitrate or config.MP3_BITRATE
    sample_rate = sample_rate or config.SAMPLE_RATE

    cmd = [
        ffmpeg_bin,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(wav_path),
        "-codec:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        "-ar",
        str(sample_rate),
        "-ac",
        "1",
        str(mp3_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg falhou ao converter {wav_path.name} → {mp3_path.name}:\n"
            f"{result.stderr}"
        )
    return mp3_path


def probe_duration_seconds(path: Path) -> float:
    """Obtém duração em segundos via ffprobe (fallback: 0.0)."""
    path = Path(path)
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0.0
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return 0.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0
