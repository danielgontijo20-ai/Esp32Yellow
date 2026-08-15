"""Testes automatizados do Content Builder (parser, cleaner, builder)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Raiz do projeto no path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.builder import process_file
from src.cleaner import clean_ocr_text, fix_hyphenation
from src.parser import (
    date_to_day_of_year,
    expected_dates_leap_year,
    parse_text,
)
from src.validator import validate_all


SAMPLE_PATH = ROOT / "input" / "amostra_10_licoes.txt"


class TestCleaner(unittest.TestCase):
    def test_hyphenation_join(self) -> None:
        raw = "clara-\nmente"
        self.assertEqual(fix_hyphenation(raw), "claramente")

    def test_hyphenation_accents(self) -> None:
        raw = "impo-\nsições"
        self.assertEqual(fix_hyphenation(raw), "imposições")

    def test_double_spaces(self) -> None:
        raw = "texto  com   espaços"
        cleaned = clean_ocr_text(raw)
        self.assertNotIn("  ", cleaned.strip())

    def test_preserve_paragraphs(self) -> None:
        raw = "parágrafo um.\n\nparágrafo dois."
        cleaned = clean_ocr_text(raw)
        self.assertIn("\n\n", cleaned)


class TestDateIds(unittest.TestCase):
    def test_january_first(self) -> None:
        self.assertEqual(date_to_day_of_year(1, "janeiro"), 1)

    def test_january_second(self) -> None:
        self.assertEqual(date_to_day_of_year(2, "janeiro"), 2)

    def test_february_29_leap(self) -> None:
        self.assertEqual(date_to_day_of_year(29, "fevereiro"), 60)

    def test_march_first_after_leap(self) -> None:
        self.assertEqual(date_to_day_of_year(1, "março"), 61)

    def test_december_31(self) -> None:
        self.assertEqual(date_to_day_of_year(31, "dezembro"), 366)

    def test_full_leap_year_count(self) -> None:
        all_dates = expected_dates_leap_year()
        self.assertEqual(len(all_dates), 366)
        self.assertEqual(all_dates[0], (1, "janeiro", 1))
        self.assertEqual(all_dates[-1], (31, "dezembro", 366))


class TestParserSample(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        raw = SAMPLE_PATH.read_text(encoding="utf-8")
        cls.lessons, cls.warnings = parse_text(raw)

    def test_ten_lessons_found(self) -> None:
        self.assertEqual(len(self.lessons), 10)

    def test_ids_sequential_january(self) -> None:
        ids = [lesson.id for lesson in self.lessons]
        self.assertEqual(ids, list(range(1, 11)))

    def test_first_date(self) -> None:
        self.assertEqual(self.lessons[0].date, "1° de janeiro")
        self.assertEqual(self.lessons[0].title, "CONTROLE E ESCOLHA")

    def test_multiline_title(self) -> None:
        lesson3 = self.lessons[2]
        self.assertEqual(
            lesson3.title,
            "SER IMPIEDOSO COM AS COISAS QUE NÃO IMPORTAM",
        )
        self.assertTrue(
            any("múltiplas linhas" in w.lower() for w in lesson3.warnings)
        )

    def test_title_with_question_mark(self) -> None:
        lesson6 = self.lessons[5]
        self.assertTrue(lesson6.title.endswith("?"))
        self.assertIn("BEM", lesson6.title)
        self.assertFalse(lesson6.errors)

    def test_quote_and_source_lesson1(self) -> None:
        q = self.lessons[0].quote
        self.assertIn("principal tarefa", q.text.lower())
        self.assertEqual(q.source, "EPICTETO, DISCURSOS, 2.5.4-5")

    def test_hyphen_fixed_in_quote(self) -> None:
        # Lição 3 contém "im-\npiedoso" no TXT de amostra
        q = self.lessons[2].quote
        self.assertIn("impiedoso", q.text.lower())
        self.assertNotIn("im-\n", q.text)
        self.assertNotIn("im- piedoso", q.text.lower())

    def test_reflection_present(self) -> None:
        for lesson in self.lessons:
            self.assertTrue(lesson.text.strip(), f"Sem texto: {lesson.date}")

    def test_segments_generated(self) -> None:
        for lesson in self.lessons:
            self.assertGreaterEqual(
                len(lesson.segments), 1, f"Sem segmentos: {lesson.date}"
            )

    def test_list_warning_on_lesson7(self) -> None:
        lesson7 = self.lessons[6]
        self.assertTrue(
            any("lista" in w.lower() for w in lesson7.warnings),
            f"Avisos da lição 7: {lesson7.warnings}",
        )


class TestBuilderIntegration(unittest.TestCase):
    def test_process_creates_ten_json_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            result = process_file(SAMPLE_PATH, out)

            self.assertEqual(len(result.lessons), 10)
            self.assertTrue(result.report_path.exists())

            lessons_dir = result.build_dir / "lessons"
            for i in range(1, 11):
                path = lessons_dir / f"{i:03d}" / "lesson.json"
                self.assertTrue(path.exists(), f"Faltando {path}")
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(data["id"], i)
                self.assertIn("title", data)
                self.assertIn("quote", data)
                self.assertIn("text", data)
                self.assertIn("segments", data)
                # Sem campos de áudio nesta versão
                self.assertNotIn("audio_file", data)
                self.assertNotIn("start", data)
                self.assertNotIn("duration", data)

            report = validate_all(result.lessons, SAMPLE_PATH.name)
            self.assertEqual(report.lessons_found, 10)
            self.assertEqual(report.first_date, "1° de janeiro")
            self.assertEqual(report.last_date, "10 de janeiro")

    def test_does_not_delete_previous_builds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            r1 = process_file(SAMPLE_PATH, out)
            r2 = process_file(SAMPLE_PATH, out)
            builds = list(out.glob("build_*"))
            self.assertGreaterEqual(len(builds), 2)
            self.assertTrue(r1.build_dir.exists())
            self.assertTrue(r2.build_dir.exists())
            self.assertNotEqual(r1.build_dir, r2.build_dir)


if __name__ == "__main__":
    unittest.main()
