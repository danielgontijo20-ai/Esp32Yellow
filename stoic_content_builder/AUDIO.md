# Diário Estoico — Audio Builder (Kokoro TTS)

Gera arquivos de áudio **offline** a partir dos `lesson.json` do Content Builder,
usando o modelo **Kokoro-82M**.

> Nesta etapa: **somente** o gerador de áudio (modo TESTE).  
> Sem ESP32, Bluetooth, SD, GUI ou sincronização texto/áudio.

## 1. Instalar dependências

### Python (obrigatório)

Use **Python 3.10, 3.11 ou 3.12**.

O pacote `kokoro` **não** funciona em Python 3.13/3.14.

**Recomendado no Windows: Python 3.11** (tem instalador oficial atual).

- 3.11: https://www.python.org/downloads/release/python-3119/
- 3.12.10 (último com instalador): https://www.python.org/downloads/release/python-31210/

Na página, role até **Files** e baixe:
`Windows installer (64-bit)`

Marque **Add python.exe to PATH**.

Confira:
```bat
py -0
py -3.11 --version
```

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

# Windows — use explicitamente o Python 3.11 (ou 3.12):
py -3.11 -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3.11 -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install -r requirements-audio.txt
```

## FFmpeg (necessário para MP3)

O Kokoro gera **WAV**. Para MP3 é preciso o `ffmpeg` no PATH.

**Windows (rápido):**
1. Baixe: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
2. Extraia, por exemplo, em `C:\ffmpeg`
3. Adicione `C:\ffmpeg\bin` ao PATH do Windows
4. Feche e abra um Prompt novo
5. Teste: `ffmpeg -version`

Sem ffmpeg, o Audio Builder salva automaticamente `.wav` em `audio_test/`.

Ou force WAV em `src/audio/config.py`:
```python
OUTPUT_FORMAT = "wav"
```

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

## Interface gráfica (Tkinter)

```bash
cd stoic_content_builder
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python audio_gui.py
```

1. Clique em **Selecionar arquivos** e escolha um ou mais `lesson.json`
   (ex.: `output/build_.../lessons/001/lesson.json`)
2. Escolha a **Voz** (`pf_dora` / `pm_alex`)
3. Pasta de destino padrão: `audio_test_gui/`
4. Clique em **GERAR ÁUDIOS**

A GUI reutiliza o mesmo Kokoro do `generate_audio.py` (não altera a CLI).

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

> **Nota:** em 24 kHz, o LAME costuma gravar MP3 em ~160 kbps (limite do
> MPEG-2 Layer III nessa taxa). Isso é normal e adequado para narração.

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
