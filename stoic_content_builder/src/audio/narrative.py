"""Montagem do texto narrado a partir dos segments do lesson.json."""

from __future__ import annotations

from typing import Any


SEGMENT_ORDER = ("quote", "source", "text")


def _sort_key(segment: dict[str, Any]) -> tuple[int, int]:
    """Ordena por type (quote→source→text) e depois por id do segment."""
    type_rank = {name: i for i, name in enumerate(SEGMENT_ORDER)}
    seg_type = str(segment.get("type", "text"))
    seg_id = int(segment.get("id") or 0)
    return (type_rank.get(seg_type, 99), seg_id)


def build_narrative_from_segments(segments: list[dict[str, Any]]) -> str:
    """Concatena o texto dos segments na ordem de narração.

    Regras:
    - Ordem: quote → source → text
    - Não narra id / date / title
    - Não altera o texto original de cada segment
    - Preserva \\n internos; separa segments com \\n\\n
    """
    if not segments:
        return ""

    ordered = sorted(segments, key=_sort_key)
    parts: list[str] = []
    for seg in ordered:
        text = seg.get("text")
        if text is None:
            continue
        # Não strip agressivo — só remove espaços/tabs nas bordas,
        # preservando quebras internas do segment.
        cleaned = str(text).strip(" \t")
        if cleaned:
            parts.append(cleaned)

    return "\n\n".join(parts)
