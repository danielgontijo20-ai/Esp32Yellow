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
ESTOICO_PATH = ROOT / "input" / "Estoico_1_10.txt"


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

    def test_segments_are_text_only(self) -> None:
        for lesson in self.lessons:
            types = [s.type for s in lesson.segments]
            self.assertTrue(types, f"Sem segments: {lesson.date}")
            self.assertTrue(
                all(t == "text" for t in types),
                f"Types inesperados em {lesson.date}: {types}",
            )
            self.assertNotIn("quote", types)
            self.assertNotIn("source", types)

    def test_narrative_prefix_on_segments(self) -> None:
        for lesson in self.lessons:
            segs = lesson.segments
            self.assertGreaterEqual(len(segs), 5, lesson.date)
            self.assertTrue(
                segs[0].text.startswith("A lição deste momento é uma citação de ")
            )
            self.assertTrue(segs[1].text.startswith("A lição se chama: "))
            self.assertEqual(segs[2].text, lesson.quote.text)
            self.assertEqual(
                segs[3].text, "Agora vamos para os comentários desta citação."
            )
            self.assertEqual(lesson.quote.philosopher, segs[0].text[len(
                "A lição deste momento é uma citação de "
            ):].rstrip("."))

    def test_source_not_in_segments(self) -> None:
        for lesson in self.lessons:
            blob = "\n".join(s.text for s in lesson.segments)
            self.assertNotIn(lesson.quote.source, blob)

    def test_list_items_not_merged_in_segments(self) -> None:
        lesson7 = self.lessons[6]
        text_segs = [s.text for s in lesson7.segments]
        joined = "\n".join(text_segs)
        self.assertIn("1. Observe seus juízos.", joined)
        self.assertIn("2. Distinga o que depende de você.", joined)
        self.assertIn("3. Aja com justiça e coragem.", joined)
        for seg in lesson7.segments:
            if "1. Observe" in seg.text and "2. Distinga" in seg.text:
                self.assertIn("\n", seg.text)
                self.assertNotIn("juízos. 2.", seg.text)

    def test_text_field_preserves_paragraphs(self) -> None:
        lesson1 = self.lessons[0]
        self.assertIn("\n\n", lesson1.text)
        # text continua sendo só a reflexão (sem a fonte)
        self.assertNotIn("EPICTETO, DISCURSOS", lesson1.text)

    def test_list_warning_on_lesson7(self) -> None:
        lesson7 = self.lessons[6]
        self.assertTrue(
            any("lista" in w.lower() for w in lesson7.warnings),
            f"Avisos da lição 7: {lesson7.warnings}",
        )


class TestEstoico110(unittest.TestCase):
    """Validação com o TXT real das 10 primeiras lições."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.path = ESTOICO_PATH
        cls.lessons, _ = parse_text(cls.path.read_text(encoding="utf-8"))
        cls.report = validate_all(cls.lessons, cls.path.name)

    def test_ten_lessons(self) -> None:
        self.assertEqual(len(self.lessons), 10)
        self.assertEqual(self.report.lessons_found, 10)

    def test_zero_errors(self) -> None:
        self.assertEqual(self.report.error_count(), 0)

    def test_lesson3_paragraph_blocks(self) -> None:
        lesson3 = self.lessons[2]
        self.assertEqual(lesson3.id, 3)
        self.assertEqual(
            lesson3.title,
            "SER IMPIEDOSO COM AS COISAS QUE NÃO IMPORTAM",
        )
        types = [s.type for s in lesson3.segments]
        self.assertTrue(all(t == "text" for t in types))
        self.assertEqual(lesson3.segments[0].id, 1)
        self.assertIn("Sêneca", lesson3.segments[0].text)
        # Comentários (após transição): prosa sem quebra OCR residual
        comments = lesson3.segments[4:]
        for seg in comments:
            self.assertFalse(seg.text.endswith("\n"))
            if "—" not in seg.text and not re_listish(seg.text):
                self.assertNotIn("\n", seg.text)

    def test_lesson5_narrative_seneca(self) -> None:
        lesson5 = self.lessons[4]
        self.assertEqual(lesson5.id, 5)
        self.assertEqual(lesson5.title, "TORNE SUAS INTENÇÕES CLARAS")
        self.assertEqual(lesson5.quote.philosopher, "Sêneca")
        self.assertEqual(
            lesson5.segments[0].text,
            "A lição deste momento é uma citação de Sêneca.",
        )
        self.assertEqual(
            lesson5.segments[1].text,
            "A lição se chama: Torne suas intenções claras.",
        )
        self.assertEqual(lesson5.segments[2].text, lesson5.quote.text)
        self.assertEqual(
            lesson5.segments[3].text,
            "Agora vamos para os comentários desta citação.",
        )
        # title original permanece em maiúsculas
        self.assertEqual(lesson5.title, "TORNE SUAS INTENÇÕES CLARAS")

    def test_lesson7_emdash_list_one_block(self) -> None:
        lesson7 = self.lessons[6]
        self.assertEqual(lesson7.id, 7)
        text_segs = lesson7.segments
        self.assertTrue(all(s.type == "text" for s in text_segs))

        labels = (
            "Escolha —",
            "Recusa —",
            "Anseio —",
            "Repulsa —",
            "Preparação —",
            "Objetivo —",
            "Consentimento —",
        )
        list_seg = None
        for seg in text_segs:
            if "Escolha —" in seg.text:
                list_seg = seg
                break
        self.assertIsNotNone(list_seg)
        assert list_seg is not None
        for label in labels:
            self.assertIn(label, list_seg.text)
        self.assertIn("\n", list_seg.text)
        self.assertNotIn("corretamente Recusa", list_seg.text)
        list_hits = sum(1 for s in text_segs if "Escolha —" in s.text)
        self.assertEqual(list_hits, 1)

    def test_lesson9_text_only_segments(self) -> None:
        lesson9 = self.lessons[8]
        self.assertEqual(lesson9.id, 9)
        self.assertTrue(lesson9.segments)
        self.assertTrue(all(s.type == "text" for s in lesson9.segments))
        self.assertEqual(lesson9.quote.philosopher, "Epicteto")
        self.assertIn("Epicteto", lesson9.segments[0].text)
        blob = "\n".join(s.text for s in lesson9.segments)
        self.assertNotIn(lesson9.quote.source, blob)

    def test_lesson1_serenity_in_quote_not_cut(self) -> None:
        lesson1 = self.lessons[0]
        prayer = (
            "Deus, concedei-me a serenidade para aceitar as coisas que não posso mudar, "
            "a coragem para mudar as coisas que posso e a sabedoria para distingui-las."
        )
        flat_quote = lesson1.quote.text.replace("\n", " ")
        if "concedei-me a serenidade" in flat_quote:
            self.assertIn(prayer, flat_quote)
        # Citação também aparece no segment 3 do roteiro
        self.assertEqual(lesson1.segments[2].text, lesson1.quote.text)
        self.assertTrue(all(s.type == "text" for s in lesson1.segments))


def re_listish(text: str) -> bool:
    return bool(
        any(
            line.strip().startswith(("1.", "2.", "3.", "•", "-"))
            or " — " in line
            for line in text.split("\n")
        )
    )


class TestOcrNormalization(unittest.TestCase):
    def test_ocr_wrap_inside_editorial_item(self) -> None:
        raw = """7 de janeiro
AS SETE FUNÇÕES CLARAS DA MENTE

Citação de teste sobre a mente e suas funções claras no cotidiano.

EPICTETO, DISCURSOS, 4.11.6-7

Vamos decompor:

Escolha — fazer e pensar corretamente
Preparação — para o que quer que
possa acontecer
Objetivo — nosso princípio

É para isso que serve a mente.
"""
        lessons, _ = parse_text(raw)
        self.assertEqual(len(lessons), 1)
        lesson = lessons[0]
        list_seg = next(s for s in lesson.segments if "Preparação —" in s.text)
        self.assertIn("para o que quer que possa acontecer", list_seg.text)
        self.assertNotIn("que\npossa", list_seg.text)
        self.assertIn("Escolha —", list_seg.text)
        self.assertIn("Objetivo —", list_seg.text)


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
                self.assertTrue(data["segments"])
                self.assertIn("text", data["quote"])
                self.assertIn("source", data["quote"])
                self.assertIn("philosopher", data["quote"])
                for seg in data["segments"]:
                    self.assertEqual(seg["type"], "text")
                    self.assertIn("text", seg)
                    self.assertIn("id", seg)
                self.assertTrue(
                    data["segments"][0]["text"].startswith(
                        "A lição deste momento é uma citação de "
                    )
                )
                self.assertEqual(
                    data["segments"][3]["text"],
                    "Agora vamos para os comentários desta citação.",
                )
                # Sem campos de áudio nesta versão
                self.assertNotIn("audio_file", data)
                self.assertNotIn("start", data)
                self.assertNotIn("duration", data)

            report = validate_all(result.lessons, SAMPLE_PATH.name)
            self.assertEqual(report.lessons_found, 10)
            self.assertEqual(report.error_count(), 0)
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
