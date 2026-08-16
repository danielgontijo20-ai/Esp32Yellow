"""Testes da ponte TXT → áudio (sem Kokoro)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audio.builder import (
    load_lesson_from_txt,
    peek_txt_label,
    resolve_output_stem,
)
from src.audio.narrative import build_narrative_from_segments


TXT_DIR = ROOT / "input" / "lessons_txt"


class TestTxtToLesson(unittest.TestCase):
    def test_load_001(self) -> None:
        lesson = load_lesson_from_txt(TXT_DIR / "001.txt")
        self.assertEqual(lesson["id"], 1)
        self.assertIn("janeiro", lesson["date"])
        self.assertTrue(lesson["segments"])
        types = [s["type"] for s in lesson["segments"]]
        self.assertIn("quote", types)
        self.assertIn("source", types)
        self.assertIn("text", types)

    def test_narrative_order(self) -> None:
        lesson = load_lesson_from_txt(TXT_DIR / "007.txt")
        narrative = build_narrative_from_segments(lesson["segments"])
        self.assertIn("EPICTETO", narrative)
        # não inclui título
        self.assertNotIn("AS SETE FUNÇÕES", narrative.split("EPICTETO")[0])

    def test_peek_label(self) -> None:
        label = peek_txt_label(TXT_DIR / "010.txt")
        self.assertIn("010.txt", label)
        self.assertIn("janeiro", label)

    def test_output_stem_from_filename(self) -> None:
        lesson = load_lesson_from_txt(TXT_DIR / "007.txt")
        self.assertEqual(resolve_output_stem(TXT_DIR / "007.txt", lesson), "007")


if __name__ == "__main__":
    unittest.main()
