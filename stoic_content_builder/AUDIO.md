# Diário Estoico — Audio Builder (Kokoro TTS)

Gera arquivos de áudio **offline** a partir dos `lesson.json` do Content Builder,
usando o modelo **Kokoro-82M**.

> Nesta etapa: **somente** o gerador de áudio (modo TESTE).  
> Sem ESP32, Bluetooth, SD, GUI ou sincronização texto/áudio.

## 1. Instalar dependências

### Sistema

**Windows**
- Python 3.11 ou 3.12
- [FFmpeg](https://ffmpeg.org/download.html) no PATH (necessário para MP3)
- `espeak-ng` (phonemizer do Kokoro) — no Windows costuma vir via dependências pip; se falhar, instale [eSpeak NG](https://github.com/espeak-ng/espeak-ng/releases)

**Linux**
```bash
sudo apt install espeak-ng ffmpeg python3-venv
```

### Ambiente virtual + pip

```bash
cd stoic_content_builder
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements-audio.txt
```

## 2. Baixar / preparar o modelo Kokoro

Na **primeira execução**, o Kokoro baixa automaticamente o modelo
`hexgrad/Kokoro-82M` do Hugging Face (~centenas de MB).

Depois disso, a síntese funciona **offline**.

Não é necessário baixar manualmente, salvo se a rede estiver bloqueada —
nesse caso, faça o download uma vez em outro PC e copie o cache do Hugging Face.

## 3. Selecionar a voz

Edite `src/audio/config.py`:

```python
VOICE = "pf_dora"   # pt-BR feminino (padrão)
# VOICE = "pm_alex"   # pt-BR masculino
# VOICE = "pm_santa"  # pt-BR masculino
LANG_CODE = "p"     # português brasileiro
```

Ou na linha de comando:

```bash
python generate_audio.py --mode test --voice pm_alex
```

## 4. Executar o modo TESTE

Pré-requisito: já existir um build do Content Builder em `output/build_*/lessons/`.

```bash
cd stoic_content_builder
source .venv/bin/activate   # ou .venv\Scripts\activate no Windows
python generate_audio.py --mode test
```

Isso gera **apenas**:

- `audio_test/001.mp3`
- `audio_test/007.mp3`
- `audio_test/010.mp3`
- `audio_test/report.txt`

## 5. Onde os MP3 são gerados

| Modo | Pasta |
|------|--------|
| `test` | `audio_test/` |
| `full` | `audio/` |

Kokoro gera WAV internamente (24 kHz). Em seguida o `ffmpeg` converte para MP3
(`192k` por padrão — configurável).

## 6. Como gerar as 366 lições depois

1. Em `src/audio/config.py`, altere:

```python
MODE = "full"
```

2. Ou execute:

```bash
python generate_audio.py --mode full
```

Os arquivos vão para `audio/001.mp3` … `audio/366.mp3`.

**Não execute o modo full até validar os 3 áudios de teste.**

## Configuração relevante (`src/audio/config.py`)

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `VOICE` | `pf_dora` | Voz Kokoro |
| `LANG_CODE` | `p` | Português BR |
| `SAMPLE_RATE` | `24000` | Taxa nativa do Kokoro |
| `OUTPUT_FORMAT` | `mp3` | `mp3` ou `wav` |
| `MP3_BITRATE` | `192k` | Bitrate (sem compressão excessiva) |
| `MODE` | `test` | `test` ou `full` |
| `TEST_LESSON_IDS` | `[1, 7, 10]` | IDs do modo teste |
| `SPEED` | `1.0` | Velocidade da fala |

## Narração

O áudio usa **somente** os `segments` do JSON, nesta ordem:

1. `quote`
2. `source`
3. `text`

**Não** narra `id`, `date` nem `title`.

## Estrutura do código

```
generate_audio.py          # CLI
src/audio/
  config.py                # VOICE, formato, modo
  narrative.py             # concatena segments
  kokoro_engine.py         # síntese → WAV
  convert.py               # WAV → MP3 (ffmpeg)
  report.py                # report.txt
  builder.py               # pipeline
audio_test/                # saída do modo teste
```
