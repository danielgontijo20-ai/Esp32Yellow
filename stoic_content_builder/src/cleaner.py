"""Limpeza determinística de erros típicos de OCR.

Regras:
1. Juntar palavras hifenizadas no fim da linha.
2. Corrigir espaços duplicados.
3. Preservar acentos, pontuação e parágrafos.
4. Não alterar conteúdo editorial.
5. Transformações 100% determinísticas (sem IA).
"""

from __future__ import annotations

import re


def fix_hyphenation(text: str) -> str:
    """Junta palavras quebradas com hífen no fim da linha.

    Exemplo:
        "clara-\\nmente" -> "claramente"
        "impo-\\nsições" -> "imposições"
    """
    # Hífen no fim da linha seguido de continuação alfabética
    pattern = re.compile(
        r"([A-Za-zÀ-ÖØ-öø-ÿ])-\s*\n\s*([A-Za-zÀ-ÖØ-öø-ÿ])",
        re.UNICODE,
    )
    return pattern.sub(r"\1\2", text)


def collapse_spaces(text: str) -> str:
    """Colapsa espaços/tabs duplicados dentro de cada linha.

    Preserva quebras de linha e parágrafos (linhas em branco).
    """
    lines: list[str] = []
    for line in text.split("\n"):
        # Não altera linhas vazias (marcam parágrafo)
        if not line.strip():
            lines.append("")
            continue
        cleaned = re.sub(r"[ \t]{2,}", " ", line)
        lines.append(cleaned.strip())
    return "\n".join(lines)


def normalize_blank_lines(text: str) -> str:
    """Limita sequências de linhas em branco a no máximo duas.

    Duas linhas em branco consecutivas = um parágrafo vazio preservado
    de forma legível, sem expansões excessivas do OCR.
    """
    return re.sub(r"\n{3,}", "\n\n", text)


def clean_ocr_text(text: str) -> str:
    """Aplica toda a limpeza determinística de OCR."""
    result = text.replace("\r\n", "\n").replace("\r", "\n")
    result = fix_hyphenation(result)
    result = collapse_spaces(result)
    result = normalize_blank_lines(result)
    return result.strip() + ("\n" if text.strip() else "")


def clean_inline(text: str) -> str:
    """Limpa um trecho já extraído (sem depender de quebras de linha)."""
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
