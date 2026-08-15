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
    """Junta linhas preservando parágrafos (linha em branco).

    Linhas de prosa quebradas pelo OCR são unidas com espaço.
    Itens de lista editorial NÃO são fundidos num parágrafo único:
    cada item permanece em sua própria linha (quebra significativa).
    """
    paragraphs: list[str] = []
    current_prose: list[str] = []
    current_list: list[str] = []

    def flush_prose() -> None:
        nonlocal current_prose
        if current_prose:
            paragraphs.append(clean_inline(" ".join(current_prose)))
            current_prose = []

    def flush_list() -> None:
        nonlocal current_list
        if current_list:
            items = [clean_inline(item) for item in current_list]
            paragraphs.append("\n".join(items))
            current_list = []

    for line in lines:
        if not line.strip():
            flush_prose()
            flush_list()
            continue
        stripped = line.strip()
        if looks_like_list_line(stripped):
            flush_prose()
            current_list.append(stripped)
        else:
            flush_list()
            current_prose.append(stripped)

    flush_prose()
    flush_list()
    return "\n\n".join(paragraphs)


def extract_reflection(body_lines: list[str], start: int) -> tuple[str, list[str]]:
    """Extrai o texto da reflexão a partir de `start`."""
    warnings: list[str] = []
    lines = body_lines[start:]
    text = _join_paragraphs(lines)

    if any(looks_like_list_line(ln) for ln in lines if ln.strip()):
        warnings.append("Lista detectada no texto.")

    return text, warnings


def build_lesson_segments(quote_text: str, source: str, reflection: str) -> list[Segment]:
    """Monta segmentos na ordem de narração: quote → source → text.

    O campo `text` da lição permanece intacto; esta função só gera `segments`.
    """
    segments: list[Segment] = []
    next_id = 1

    for chunk in segment_body(quote_text):
        segments.append(Segment(id=next_id, type="quote", text=chunk))
        next_id += 1

    source_clean = source.strip()
    if source_clean:
        segments.append(Segment(id=next_id, type="source", text=source_clean))
        next_id += 1

    for chunk in segment_body(reflection):
        segments.append(Segment(id=next_id, type="text", text=chunk))
        next_id += 1

    return segments


def segment_text(text: str) -> list[Segment]:
    """Compatibilidade: segmenta apenas reflexão como type=text."""
    chunks = segment_body(text)
    return [Segment(id=i, type="text", text=c) for i, c in enumerate(chunks, start=1)]


def segment_body(text: str) -> list[str]:
    """Divide um corpo de texto em pedaços curtos.

    Prioridade: parágrafo → frase → tamanho máximo.
    Preserva quebras significativas (ex.: itens de lista).
    Evita cortar frase no meio sempre que couber no limite.
    """
    if not text or not text.strip():
        return []

    paragraphs = re.split(r"\n\s*\n", text.strip())
    raw_chunks: list[str] = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        lines = [ln.strip() for ln in para.split("\n") if ln.strip()]
        if not lines:
            continue

        # Lista editorial: nunca fundir itens num único parágrafo
        if _is_list_block(lines):
            for item in lines:
                raw_chunks.extend(_fit_chunk(item, preserve_newlines=False))
            continue

        # Bloco com quebras internas significativas (não lista pura)
        if len(lines) > 1:
            # Mantém \n entre linhas; só quebra se o bloco inteiro for longo
            block = "\n".join(lines)
            raw_chunks.extend(_fit_chunk(block, preserve_newlines=True))
            continue

        # Parágrafo de prosa (uma linha lógica)
        raw_chunks.extend(_fit_chunk(lines[0], preserve_newlines=False))

    return raw_chunks


def _is_list_block(lines: list[str]) -> bool:
    """True se o bloco é (predominantemente) uma lista editorial."""
    if not lines:
        return False
    list_lines = sum(1 for ln in lines if looks_like_list_line(ln))
    # Exige maioria de itens de lista; evita falso positivo em prosa
    return list_lines >= 1 and list_lines >= (len(lines) + 1) // 2


def _fit_chunk(text: str, *, preserve_newlines: bool) -> list[str]:
    """Encaixa um bloco: inteiro se couber; senão frase; senão tamanho máx."""
    if not text.strip():
        return []

    if preserve_newlines:
        # Se couber, preserva as quebras; se não, tenta por linha e depois frase
        if len(text) <= SEGMENT_MAX_CHARS:
            return [text]
        parts: list[str] = []
        for line in text.split("\n"):
            line = line.strip()
            if line:
                parts.extend(_fit_chunk(line, preserve_newlines=False))
        return parts

    if len(text) <= SEGMENT_MAX_CHARS:
        return [text]
    return _split_long_paragraph(text)


def _split_long_paragraph(para: str) -> list[str]:
    """Quebra parágrafo longo preferindo frases inteiras.

    1) Agrupa frases até SEGMENT_TARGET_CHARS
    2) Permite ultrapassar o alvo até SEGMENT_MAX_CHARS para não cortar frase
    3) Só força corte no meio se UMA frase sozinha exceder o máximo
    """
    sentences = re.split(r"(?<=[.!?…])\s+", para)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [para]

    chunks: list[str] = []
    buf = ""

    for sent in sentences:
        if not buf:
            if len(sent) > SEGMENT_MAX_CHARS:
                chunks.extend(_force_split(sent))
            else:
                buf = sent
            continue

        candidate = f"{buf} {sent}"
        if len(candidate) <= SEGMENT_TARGET_CHARS:
            buf = candidate
        elif len(candidate) <= SEGMENT_MAX_CHARS:
            # Prefere segmento um pouco maior a cortar a frase
            buf = candidate
        else:
            # Fecha o buffer atual; a frase seguinte começa outro segmento
            chunks.append(buf)
            if len(sent) > SEGMENT_MAX_CHARS:
                chunks.extend(_force_split(sent))
                buf = ""
            else:
                buf = sent

    if buf:
        chunks.append(buf)

    return chunks


def _force_split(text: str) -> list[str]:
    """Último recurso: quebra por vírgulas / espaços próximos ao alvo."""
    parts: list[str] = []
    remaining = text
    while len(remaining) > SEGMENT_MAX_CHARS:
        window = remaining[:SEGMENT_MAX_CHARS]
        cut = window.rfind(", ")
        if cut < SEGMENT_TARGET_CHARS // 2:
            cut = window.rfind(" ")
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

    # Campo text permanece a reflexão completa; segments incluem quote/source/text
    segments = build_lesson_segments(quote_text, source, reflection)

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
