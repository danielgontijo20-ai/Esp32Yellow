"""Relatório do Audio Builder."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AudioItemResult:
    lesson_id: int
    filename: str
    status: str  # OK | ERRO
    duration_sec: float = 0.0
    size_bytes: int = 0
    error: str = ""


@dataclass
class AudioReport:
    mode: str
    items: list[AudioItemResult] = field(default_factory=list)
    elapsed_sec: float = 0.0

    @property
    def ok_count(self) -> int:
        return sum(1 for i in self.items if i.status == "OK")

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.items if i.status == "ERRO")

    @property
    def total_bytes(self) -> int:
        return sum(i.size_bytes for i in self.items if i.status == "OK")


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    rem = seconds - minutes * 60
    return f"{minutes}m {rem:.1f}s"


def format_bytes(num: int) -> str:
    if num < 1024:
        return f"{num} B"
    if num < 1024**2:
        return f"{num / 1024:.1f} KB"
    return f"{num / (1024**2):.2f} MB"


def format_audio_report(report: AudioReport) -> str:
    lines: list[str] = []
    lines.append("=" * 40)
    lines.append("DIÁRIO ESTOICO — AUDIO BUILDER")
    lines.append("=" * 40)
    lines.append("")
    lines.append(f"Modo: {report.mode.upper()}")
    lines.append("")
    lines.append(f"Lições processadas: {len(report.items)}")
    lines.append("")

    for item in report.items:
        if item.status == "OK":
            lines.append(
                f"{item.filename}  OK  "
                f"({format_duration(item.duration_sec)}, "
                f"{format_bytes(item.size_bytes)})"
            )
        else:
            lines.append(f"{item.filename}  ERRO  ({item.error})")

    lines.append("")
    lines.append(f"Erros: {report.error_count}")
    lines.append("")
    lines.append("Tempo total:")
    lines.append(format_duration(report.elapsed_sec))
    lines.append("")
    lines.append("Tamanho total:")
    lines.append(format_bytes(report.total_bytes))
    lines.append("")
    lines.append("=" * 40)
    lines.append("")
    return "\n".join(lines)


def write_audio_report(report: AudioReport, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_audio_report(report), encoding="utf-8")
    return path
