"""Testes do Audio Builder (sem exigir Kokoro na CI leve)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audio.narrative import build_narrative_from_segments


class TestNarrative(unittest.TestCase):
    def test_order_quote_source_text(self) -> None:
        segments = [
            {"id": 3, "type": "text", "text": "Reflexão linha1\nlinha2"},
            {"id": 1, "type": "quote", "text": "Citação"},
            {"id": 2, "type": "source", "text": "EPICTETO, DISCURSOS, 1.1"},
        ]
        narrative = build_narrative_from_segments(segments)
        self.assertEqual(
            narrative,
            "Citação\n\nEPICTETO, DISCURSOS, 1.1\n\nReflexão linha1\nlinha2",
        )

    def test_preserves_internal_newlines(self) -> None:
        segments = [
            {
                "id": 1,
                "type": "text",
                "text": "Escolha — a\nRecusa — b",
            }
        ]
        narrative = build_narrative_from_segments(segments)
        self.assertIn("\n", narrative)
        self.assertNotIn("a Recusa", narrative)

    def test_ignores_empty(self) -> None:
        self.assertEqual(build_narrative_from_segments([]), "")


if __name__ == "__main__":
    unittest.main()
