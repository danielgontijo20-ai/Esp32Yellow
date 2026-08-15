# Diário Estoico — Content Builder

Ferramenta **local** para Windows (também funciona em Linux/macOS) que transforma um arquivo TXT obtido por OCR do livro em pastas JSON estruturadas — **uma pasta por lição**.

> Escopo desta versão: apenas o Content Builder (TXT → JSON).  
> **Não** inclui ESP32, Bluetooth, áudio, Kokoro, SD Card ou Wi-Fi.

## Requisitos

- Python 3.10 ou superior
- Tkinter (já incluso na instalação oficial do Python para Windows)

## 1. Instalar Python

### Windows

1. Baixe o instalador em [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Durante a instalação, marque **“Add python.exe to PATH”**
3. Confirme no Prompt de Comando:

```bash
python --version
```

### Linux / macOS

```bash
python3 --version
```

No Ubuntu/Debian, se o Tkinter não estiver disponível:

```bash
sudo apt install python3-tk
```

## 2. Instalar dependências

O Content Builder usa **apenas a biblioteca padrão** do Python. Não há pacotes obrigatórios.

Opcional (apenas para rodar os testes automatizados):

```bash
cd stoic_content_builder
pip install -r requirements.txt
pip install pytest
```

## 3. Executar a interface

```bash
cd stoic_content_builder
python app.py
```

(No Linux/macOS: `python3 app.py`)

## 4. Selecionar o TXT

1. Clique em **Selecionar** ao lado de **Arquivo TXT:**
2. Escolha o arquivo `.txt` em UTF-8 (ex.: `input/amostra_10_licoes.txt`)

## 5. Selecionar a pasta de saída

1. Clique em **Selecionar** ao lado de **Pasta de saída:**
2. Escolha a pasta onde os builds serão gravados (padrão: `output/`)

## 6. Processar e interpretar o relatório

1. Clique em **PROCESSAR**
2. Acompanhe o log na área de status
3. Abra `report.txt` dentro da pasta do build

O relatório informa:

- número de lições encontradas
- primeira e última data
- datas duplicadas / ausentes (no intervalo)
- problemas de sequência
- erros e avisos por lição
- status final da validação

## 7. Estrutura dos arquivos gerados

Cada execução cria uma pasta **nova** (builds anteriores **nunca** são apagados):

```text
output/
└── build_2026-08-15_120000/
    ├── report.txt
    └── lessons/
        ├── 001/
        │   └── lesson.json
        ├── 002/
        │   └── lesson.json
        └── ...
```

Formato de `lesson.json`:

```json
{
  "id": 1,
  "date": "1 de janeiro",
  "title": "CONTROLE E ESCOLHA",
  "quote": {
    "text": "...",
    "source": "EPICTETO, DISCURSOS, 2.5.4-5"
  },
  "text": "...",
  "segments": [
    { "id": 1, "text": "..." }
  ]
}
```

## Testes automatizados

```bash
cd stoic_content_builder
python -m unittest tests.test_parser -v
```

O arquivo `input/amostra_10_licoes.txt` contém as 10 primeiras lições para validar o parser.

## Processamento em linha de comando (sem GUI)

```bash
cd stoic_content_builder
python -c "from pathlib import Path; from src.builder import process_file; r=process_file(Path('input/amostra_10_licoes.txt'), Path('output')); print(r.build_dir)"
```

## Arquitetura

| Arquivo | Responsabilidade |
|---------|------------------|
| `app.py` | Interface gráfica (Tkinter) |
| `src/parser.py` | Identificação de datas, títulos, citações e reflexões |
| `src/cleaner.py` | Limpeza determinística de OCR |
| `src/validator.py` | Validação e detecção de inconsistências |
| `src/models.py` | Estruturas de dados |
| `src/builder.py` | Geração de JSON e relatório |

## Privacidade

- 100% local
- Sem APIs externas
- Sem OpenAI / Gemini / nuvem
- Nenhum conteúdo é enviado à internet
