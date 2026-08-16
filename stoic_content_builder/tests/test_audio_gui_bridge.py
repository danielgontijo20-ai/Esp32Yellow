"""Testes da ponte JSON → áudio (sem Kokoro)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audio.builder import (
    find_latest_build,
    load_lesson,
    peek_json_label,
    resolve_output_stem,
)
from src.audio.narrative import build_narrative_from_segments


def _lesson_json(lesson_id: int) -> Path:
    build = find_latest_build(ROOT / "output")
    return build / "lessons" / f"{lesson_id:03d}" / "lesson.json"


class TestJsonToLesson(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path_001 = _lesson_json(1)
        cls.path_007 = _lesson_json(7)
        if not cls.path_001.exists():
            raise unittest.SkipTest("Nenhum build com lesson.json encontrado")

    def test_load_001(self) -> None:
        lesson = load_lesson(self.path_001)
        self.assertEqual(lesson["id"], 1)
        self.assertIn("janeiro", lesson["date"])
        self.assertTrue(lesson["segments"])
        types = [s["type"] for s in lesson["segments"]]
        self.assertTrue(all(t == "text" for t in types))
        self.assertIn("quote", lesson)
        self.assertIn("source", lesson["quote"])

    def test_narrative_from_reflection_segments(self) -> None:
        lesson = load_lesson(self.path_007)
        narrative = build_narrative_from_segments(lesson["segments"])
        # Roteiro completo: intro + título + citação + transição + comentários
        self.assertIn("citação de", narrative)
        self.assertIn("A lição se chama:", narrative)
        self.assertIn("Agora vamos para os comentários", narrative)
        self.assertIn("Vamos decompor", narrative)
        self.assertIn("philosopher", lesson["quote"])
        self.assertNotIn(lesson["quote"]["source"], narrative)

    def test_peek_label(self) -> None:
        label = peek_json_label(self.path_001)
        self.assertIn("lesson.json", label)
        self.assertIn("janeiro", label)

    def test_output_stem_from_parent_folder(self) -> None:
        lesson = load_lesson(self.path_007)
        self.assertEqual(resolve_output_stem(self.path_007, lesson), "007")


if __name__ == "__main__":
    unittest.main()
