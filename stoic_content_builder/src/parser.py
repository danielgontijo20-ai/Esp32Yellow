"""Parser de lições do Diário Estoico a partir de TXT (OCR).

Identifica datas, títulos (possivelmente multilinha), citações,
fontes e textos de reflexão de forma determinística.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .cleaner import clean_inline, clean_ocr_text
from .models import Lesson, Quote, Segment


# Meses em português (ordem do ano)
MONTHS: list[str] = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]

# Dias acumulados antes de cada mês em ano bissexto (366 dias)
# fevereiro tem 29 dias
LEAP_YEAR_OFFSETS: dict[str, int] = {
    "janeiro": 0,
    "fevereiro": 31,
    "março": 60,
    "abril": 91,
    "maio": 121,
    "junho": 152,
    "julho": 182,
    "agosto": 213,
    "setembro": 244,
    "outubro": 274,
    "novembro": 305,
    "dezembro": 335,
}

DAYS_IN_MONTH_LEAP: dict[str, int] = {
    "janeiro": 31,
    "fevereiro": 29,
    "março": 31,
    "abril": 30,
    "maio": 31,
    "junho": 30,
    "julho": 31,
    "agosto": 31,
    "setembro": 30,
    "outubro": 31,
    "novembro": 30,
    "dezembro": 31,
}

# Padrão de data: "1° de janeiro", "1º de janeiro", "2 de janeiro"
DATE_PATTERN = re.compile(
    r"^(\d{1,2})\s*[°ºo]?\s+de\s+"
    r"(janeiro|fevereiro|março|abril|maio|junho|"
    r"julho|agosto|setembro|outubro|novembro|dezembro)\s*$",
    re.IGNORECASE | re.UNICODE,
)

# Autores / fontes típicas do diário estoico
KNOWN_AUTHORS = (
    "EPICTETO",
    "MARCO AURÉLIO",
    "MARCO AURELIO",
    "SÊNECA",
    "SENECA",
    "MUSÔNIO RUFO",
    "MUSONIO RUFO",
    "ZENÃO",
    "ZENAO",
    "CLEANTES",
    "CRÍSIPO",
    "CRISIPO",
)

# Linha de fonte: MAIÚSCULAS, com vírgula e referência numérica
SOURCE_PATTERN = re.compile(
    r"^[A-ZÀ-Ü][A-ZÀ-Ü\s\-']+,\s+.+\d",
    re.UNICODE,
)

# Segmentação: tamanho alvo aproximado (caracteres)
SEGMENT_TARGET_CHARS = 180
SEGMENT_MAX_CHARS = 280


@dataclass
class RawLessonBlock:
    """Bloco bruto entre duas datas."""

    date_raw: str
    day: int
    month: str
    day_of_year: int
    body_lines: list[str]
    line_index: int  # linha da data no arquivo original


def date_to_day_of_year(day: int, month: str) -> int:
    """Converte dia + mês para ID sequencial (1–366, ano bissexto)."""
    month_key = month.lower()
    if month_key not in LEAP_YEAR_OFFSETS:
        raise ValueError(f"Mês inválido: {month}")
    max_day = DAYS_IN_MONTH_LEAP[month_key]
    if day < 1 or day > max_day:
        raise ValueError(f"Dia inválido: {day} de {month}")
    return LEAP_YEAR_OFFSETS[month_key] + day


def format_date_display(day: int, month: str, original: str) -> str:
    """Normaliza a data para exibição, preservando ° quando presente."""
    month_norm = month.lower()
    if "°" in original or "º" in original:
        return f"{day}° de {month_norm}"
    return f"{day} de {month_norm}"


def is_date_line(line: str) -> re.Match[str] | None:
    """Retorna o match se a linha for uma data de lição."""
    return DATE_PATTERN.match(line.strip())


def is_mostly_uppercase(line: str) -> bool:
    """True se a linha parece título/fonte (letras majoritariamente maiúsculas)."""
    letters = [c for c in line if c.isalpha()]
    if not letters:
        return False
    upper = sum(1 for c in letters if c.isupper())
    return (upper / len(letters)) >= 0.85


def looks_like_source(line: str) -> bool:
    """Detecta linha de fonte da citação (autor + obra + referência)."""
    stripped = line.strip()
    if not stripped:
        return False
    upper = stripped.upper()
    if any(author in upper for author in KNOWN_AUTHORS):
        # Fonte tipicamente curta e em maiúsculas
        if is_mostly_uppercase(stripped) and len(stripped) < 120:
            return True
    if SOURCE_PATTERN.match(stripped) and is_mostly_uppercase(stripped):
        return True
    return False


def looks_like_title_line(line: str) -> bool:
    """Linha candidata a título: maiúsculas, sem parecer fonte/citação longa."""
    stripped = line.strip()
    if not stripped:
        return False
    if looks_like_source(stripped):
        return False
    # Títulos podem ter ? ou ! (ex.: "ONDE ESTÁ O BEM?"),
    # mas raramente terminam com ponto final de prosa.
    if stripped[-1] in ".;:":
        return False
    # Citação em prosa costuma ter minúsculas
    if not is_mostly_uppercase(stripped):
        return False
    # Títulos raramente passam de ~80 chars por linha
    if len(stripped) > 100:
        return False
    return True


def looks_like_list_line(line: str) -> bool:
    """Detecta itens de lista simples (aviso informativo)."""
    s = line.strip()
    return bool(re.match(r"^([•\-\*]|\d+[.)])\s+\S", s))


def split_into_blocks(lines: list[str]) -> list[RawLessonBlock]:
    """Divide o arquivo em blocos iniciados por data."""
    blocks: list[RawLessonBlock] = []
    current: RawLessonBlock | None = None

    for idx, raw_line in enumerate(lines):
        match = is_date_line(raw_line)
        if match:
            day = int(match.group(1))
            month = match.group(2).lower()
            try:
                day_of_year = date_to_day_of_year(day, month)
            except ValueError:
                # Data inválida: trata como texto comum se já houver bloco
                if current is not None:
                    current.body_lines.append(raw_line)
                continue

            if current is not None:
                blocks.append(current)

            current = RawLessonBlock(
                date_raw=raw_line.strip(),
                day=day,
                month=month,
                day_of_year=day_of_year,
                body_lines=[],
                line_index=idx,
            )
        else:
            if current is not None:
                current.body_lines.append(raw_line)

    if current is not None:
        blocks.append(current)

    return blocks


def extract_title(body_lines: list[str]) -> tuple[str, int, list[str]]:
    """Extrai título (possivelmente multilinha).

    Retorna (título, índice após o título, avisos).
    Não usa apenas "a próxima linha": coleta linhas maiúsculas consecutivas
    no início do bloco até encontrar prosa (citação) ou linha vazia seguida
    de prosa.
    """
    warnings: list[str] = []
    i = 0
    # Pular linhas vazias iniciais
    while i < len(body_lines) and not body_lines[i].strip():
        i += 1

    title_parts: list[str] = []
    while i < len(body_lines):
        line = body_lines[i].strip()
        if not line:
            # Linha em branco após título: encerra título
            if title_parts:
                break
            i += 1
            continue
        if looks_like_title_line(line):
            title_parts.append(line)
            i += 1
            continue
        # Linha que não parece título → início da citação
        break

    if len(title_parts) > 1:
        warnings.append("Título detectado em múltiplas linhas.")

    title = clean_inline(" ".join(title_parts))
    return title, i, warnings


def extract_quote_and_rest(
    body_lines: list[str], start: int
) -> tuple[str, str, int, list[str]]:
    """Extrai quote.text, quote.source e índice do início da reflexão."""
    warnings: list[str] = []
    i = start
    while i < len(body_lines) and not body_lines[i].strip():
        i += 1

    quote_lines: list[str] = []
    source = ""
    source_idx = -1

    j = i
    while j < len(body_lines):
        line = body_lines[j].strip()
        if looks_like_source(line):
            source = line
            source_idx = j
            break
        j += 1

    if source_idx >= 0:
        # Texto da citação: linhas entre início e fonte
        for k in range(i, source_idx):
            quote_lines.append(body_lines[k])
        rest_start = source_idx + 1
    else:
        # Sem fonte detectada: tenta separar por primeira linha maiúscula curta
        # após algum texto; senão toda a prosa inicial vira citação vazia
        warnings.append("Fonte da citação não detectada automaticamente.")
        # Heurística: se a primeira linha não-vazia parece prosa, citação vazia
        # e todo o restante é reflexão — melhor do que inventar.
        quote_lines = []
        source = ""
        rest_start = i

    quote_text = _join_paragraphs(quote_lines)
    return quote_text, source, rest_start, warnings


def _join_paragraphs(lines: list[str]) -> str:
    """Junta linhas preservando parágrafos (separados por linha em branco)."""
    paragraphs: list[str] = []
    current: list[str] = []

    for line in lines:
        if not line.strip():
            if current:
                paragraphs.append(clean_inline(" ".join(current)))
                current = []
        else:
            current.append(line.strip())

    if current:
        paragraphs.append(clean_inline(" ".join(current)))

    return "\n\n".join(paragraphs)


def extract_reflection(body_lines: list[str], start: int) -> tuple[str, list[str]]:
    """Extrai o texto da reflexão a partir de `start`."""
    warnings: list[str] = []
    lines = body_lines[start:]
    text = _join_paragraphs(lines)

    if any(looks_like_list_line(ln) for ln in lines if ln.strip()):
        warnings.append("Lista detectada no texto.")

    return text, warnings


def segment_text(text: str) -> list[Segment]:
    """Divide o texto em segmentos curtos respeitando parágrafos e frases."""
    if not text.strip():
        return []

    paragraphs = re.split(r"\n\s*\n", text.strip())
    raw_chunks: list[str] = []

    for para in paragraphs:
        para = clean_inline(para)
        if not para:
            continue
        if len(para) <= SEGMENT_MAX_CHARS:
            raw_chunks.append(para)
        else:
            raw_chunks.extend(_split_long_paragraph(para))

    segments: list[Segment] = []
    for idx, chunk in enumerate(raw_chunks, start=1):
        segments.append(Segment(id=idx, text=chunk))
    return segments


def _split_long_paragraph(para: str) -> list[str]:
    """Quebra parágrafo longo em frases, agrupando até o tamanho alvo."""
    # Divide em frases preservando pontuação final
    sentences = re.split(r"(?<=[.!?…])\s+", para)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [para]

    chunks: list[str] = []
    buf = ""
    for sent in sentences:
        if not buf:
            buf = sent
        elif len(buf) + 1 + len(sent) <= SEGMENT_TARGET_CHARS:
            buf = f"{buf} {sent}"
        else:
            chunks.append(buf)
            buf = sent
        # Se uma única frase for enorme, força quebra por vírgula/cláusula
        if len(buf) > SEGMENT_MAX_CHARS:
            chunks.extend(_force_split(buf))
            buf = ""

    if buf:
        if len(buf) > SEGMENT_MAX_CHARS:
            chunks.extend(_force_split(buf))
        else:
            chunks.append(buf)

    return chunks


def _force_split(text: str) -> list[str]:
    """Último recurso: quebra por vírgulas / espaços próximos ao alvo."""
    parts: list[str] = []
    remaining = text
    while len(remaining) > SEGMENT_MAX_CHARS:
        cut = remaining.rfind(", ", 0, SEGMENT_TARGET_CHARS)
        if cut < SEGMENT_TARGET_CHARS // 2:
            cut = remaining.rfind(" ", 0, SEGMENT_TARGET_CHARS)
        if cut <= 0:
            cut = SEGMENT_TARGET_CHARS
        parts.append(remaining[:cut].strip().rstrip(","))
        remaining = remaining[cut:].lstrip(" ,")
    if remaining.strip():
        parts.append(remaining.strip())
    return parts


def parse_block(block: RawLessonBlock) -> Lesson:
    """Converte um bloco bruto em Lesson estruturada."""
    warnings: list[str] = []
    errors: list[str] = []

    date_display = format_date_display(block.day, block.month, block.date_raw)

    title, after_title, title_warns = extract_title(block.body_lines)
    warnings.extend(title_warns)

    quote_text, source, after_quote, quote_warns = extract_quote_and_rest(
        block.body_lines, after_title
    )
    warnings.extend(quote_warns)

    reflection, refl_warns = extract_reflection(block.body_lines, after_quote)
    warnings.extend(refl_warns)

    if not title:
        errors.append("Título vazio.")
    if not quote_text:
        errors.append("Citação (quote.text) vazia.")
    if not source:
        errors.append("Fonte (quote.source) vazia.")
    if not reflection:
        errors.append("Texto da reflexão vazio.")

    segments = segment_text(reflection)

    return Lesson(
        id=block.day_of_year,
        date=date_display,
        title=title,
        quote=Quote(text=quote_text, source=source),
        text=reflection,
        segments=segments,
        warnings=warnings,
        errors=errors,
    )


def parse_text(raw_text: str) -> tuple[list[Lesson], list[str]]:
    """Parse completo do conteúdo TXT.

    Retorna (lições, avisos_globais).
    """
    global_warnings: list[str] = []

    if not raw_text or not raw_text.strip():
        return [], ["Arquivo vazio."]

    cleaned = clean_ocr_text(raw_text)
    lines = cleaned.split("\n")
    blocks = split_into_blocks(lines)

    if not blocks:
        return [], ["Nenhuma lição encontrada (nenhuma data detectada)."]

    lessons = [parse_block(b) for b in blocks]
    return lessons, global_warnings


def expected_dates_leap_year() -> list[tuple[int, str, int]]:
    """Lista (dia, mês, day_of_year) para os 366 dias do ano bissexto."""
    result: list[tuple[int, str, int]] = []
    for month in MONTHS:
        for day in range(1, DAYS_IN_MONTH_LEAP[month] + 1):
            result.append((day, month, date_to_day_of_year(day, month)))
    return result
