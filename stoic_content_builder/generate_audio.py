#!/usr/bin/env python3
"""Diário Estoico — Audio Builder (Kokoro TTS offline).

Uso:
  # Ative o venv primeiro
  python generate_audio.py              # modo definido em src/audio/config.py
  python generate_audio.py --mode test  # apenas 001, 007, 010
  python generate_audio.py --mode full  # todas as lições do build
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from src.audio import config
from src.audio.builder import run_audio_build
from src.audio.report import format_audio_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diário Estoico — Audio Builder (Kokoro TTS offline)"
    )
    parser.add_argument(
        "--mode",
        choices=("test", "full"),
        default=None,
        help="test = 001/007/010 | full = todas as lições (padrão: config.MODE)",
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=None,
        help="Pasta build_* do Content Builder (padrão: build mais recente)",
    )
    parser.add_argument(
        "--voice",
        default=None,
        help="Sobrescreve config.VOICE (ex.: pf_dora, pm_alex, pm_santa)",
    )
    parser.add_argument(
        "--format",
        choices=("mp3", "wav"),
        default=None,
        help="mp3 (precisa ffmpeg) ou wav (sem ffmpeg)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.voice:
        config.VOICE = args.voice
    if args.format:
        config.OUTPUT_FORMAT = args.format

    report = run_audio_build(mode=args.mode, build_dir=args.build_dir)
    print()
    print(format_audio_report(report))
    return 0 if report.error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
