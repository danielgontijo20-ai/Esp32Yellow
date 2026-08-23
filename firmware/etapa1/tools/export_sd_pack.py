#!/usr/bin/env python3
"""Empacota lessons JSON + MP3s para o layout do cartão SD da ESP32.

Layout gerado:
  OUT/
    lessons/001.json ...
    audio/001.mp3 ...
    system/   (pasta criada; touch.cal vem da calibração na ESP)

Converte MP3 para 44.1 kHz stereo (compatível com Bluetooth A2DP),
se o ffmpeg estiver instalado.

Exemplos:
  python export_sd_pack.py --build-dir caminho/output/build_XXX --out E:/
  python export_sd_pack.py --lessons-json-dir ... --audio-dir ... --out ./sd_pack
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def find_lesson_jsons(build_dir: Path) -> list[Path]:
    lessons = build_dir / "lessons"
    if not lessons.is_dir():
        return []
    files = sorted(lessons.glob("*/lesson.json"))
    return files


def copy_json(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def convert_or_copy_mp3(src: Path, dest: Path, ffmpeg: str | None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not ffmpeg:
        shutil.copy2(src, dest)
        return
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(src),
        "-ar",
        "44100",
        "-ac",
        "2",
        "-b:a",
        "128k",
        str(dest),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"AVISO: ffmpeg falhou em {src.name}; copiando original", file=sys.stderr)
        shutil.copy2(src, dest)


def main() -> int:
    ap = argparse.ArgumentParser(description="Exporta pacote SD do Diario Estoico")
    ap.add_argument("--build-dir", type=Path, help="Pasta build_YYYY... do Content Builder")
    ap.add_argument("--lessons-json-dir", type=Path, help="Pasta com NNN.json já prontos")
    ap.add_argument("--audio-dir", type=Path, help="Pasta com NNN.mp3")
    ap.add_argument("--out", type=Path, required=True, help="Destino (ex.: E:/ ou ./sd_pack)")
    ap.add_argument("--ids", type=str, default="", help="Lista opcional: 1,7,8")
    args = ap.parse_args()

    out = args.out
    (out / "lessons").mkdir(parents=True, exist_ok=True)
    (out / "audio").mkdir(parents=True, exist_ok=True)
    (out / "system").mkdir(parents=True, exist_ok=True)

    only: set[int] | None = None
    if args.ids.strip():
        only = {int(x.strip()) for x in args.ids.split(",") if x.strip()}

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        print(f"ffmpeg encontrado: {ffmpeg} (converterá para 44.1kHz stereo)")
    else:
        print("ffmpeg NÃO encontrado — MP3s serão copiados sem conversão")

    count = 0

    if args.build_dir:
        for lesson_json in find_lesson_jsons(args.build_dir):
            data = json.loads(lesson_json.read_text(encoding="utf-8"))
            lid = int(data["id"])
            if only is not None and lid not in only:
                continue
            dest_json = out / "lessons" / f"{lid:03d}.json"
            copy_json(lesson_json, dest_json)
            print(f"JSON {lid:03d}")
            count += 1

            # Áudio no mesmo build? senão --audio-dir
            if args.audio_dir:
                src_mp3 = args.audio_dir / f"{lid:03d}.mp3"
                if src_mp3.exists():
                    convert_or_copy_mp3(src_mp3, out / "audio" / f"{lid:03d}.mp3", ffmpeg)
                    print(f"MP3  {lid:03d}")
                else:
                    print(f"AVISO: sem MP3 para {lid:03d}")

    elif args.lessons_json_dir:
        for src in sorted(args.lessons_json_dir.glob("*.json")):
            try:
                lid = int(src.stem)
            except ValueError:
                continue
            if only is not None and lid not in only:
                continue
            copy_json(src, out / "lessons" / f"{lid:03d}.json")
            count += 1
            if args.audio_dir:
                src_mp3 = args.audio_dir / f"{lid:03d}.mp3"
                if src_mp3.exists():
                    convert_or_copy_mp3(src_mp3, out / "audio" / f"{lid:03d}.mp3", ffmpeg)

    else:
        print("Informe --build-dir ou --lessons-json-dir", file=sys.stderr)
        return 2

    print(f"\nPronto: {count} lições em {out}")
    print("Estrutura: lessons/  audio/  system/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
