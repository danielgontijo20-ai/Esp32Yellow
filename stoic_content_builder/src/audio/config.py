"""Configuração do Diário Estoico — Audio Builder (Kokoro TTS).

Altere VOICE / MODE / demais parâmetros aqui sem mexer no restante do código.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Raiz do projeto (stoic_content_builder/)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Modo de execução
# ---------------------------------------------------------------------------
# "test" → gera apenas TEST_LESSON_IDS em audio_test/
# "full" → gera todas as lições encontradas no build (366 no futuro)
MODE: str = "test"

TEST_LESSON_IDS: list[int] = [1, 7, 10]

# ---------------------------------------------------------------------------
# Kokoro TTS
# ---------------------------------------------------------------------------
# Vozes pt-BR: pf_dora (F), pm_alex (M), pm_santa (M)
VOICE: str = "pf_dora"

# Código de idioma Kokoro: 'p' = português brasileiro
LANG_CODE: str = "p"

# Repositório Hugging Face do modelo (download inicial apenas)
REPO_ID: str = "hexgrad/Kokoro-82M"

# Velocidade da fala (1.0 = normal)
SPEED: float = 1.0

# Taxa nativa do Kokoro (não alterar sem motivo — o modelo gera 24 kHz)
SAMPLE_RATE: int = 24000

# ---------------------------------------------------------------------------
# Formato de saída
# ---------------------------------------------------------------------------
# Kokoro gera WAV internamente; em seguida convertemos para MP3 via ffmpeg.
OUTPUT_FORMAT: str = "mp3"  # "mp3" | "wav"

# Bitrate MP3 — alvo 192k (em 24 kHz o ffmpeg/LAME pode gravar ~160k,
# que é o teto típico para MPEG-2 Layer III @ 24 kHz; adequado para voz)
MP3_BITRATE: str = "192k"

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
# Pasta de build do Content Builder (ajuste se necessário)
# Se None, usa automaticamente o build_* mais recente em output/
LESSONS_BUILD_DIR: Path | None = None

OUTPUT_DIR_TEST: Path = PROJECT_ROOT / "audio_test"
OUTPUT_DIR_FULL: Path = PROJECT_ROOT / "audio"

# WAV temporários (apagados após conversão para MP3, se FORMAT=mp3)
TEMP_WAV_DIR: Path = PROJECT_ROOT / "audio_temp"
