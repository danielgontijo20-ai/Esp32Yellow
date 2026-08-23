# Etapa 1 — Player de lição (Yellow)

Placa: **ESP32-2432S028R** (User_Setup = **ST7789**)  
Caixa: **JBL CINEMA SB110**

## O que esta etapa faz

1. Lê `lessons/007.json` do SD  
2. Mostra **data + título + citação + reflexão**  
3. Rola o texto automaticamente  
4. Toca `audio/007.mp3` na JBL (Bluetooth)  
5. Toque na tela = **pause / play**

Ainda **não** tem: Filosofar, histórico, menu completo (isso é Etapa 2+).

---

## Bibliotecas novas (além da Etapa 0)

No Arduino IDE → **Gerenciar Bibliotecas**:

1. **ArduinoJson** (Benoit Blanchon) — instale a versão **6.21.x** se pedir (o código usa `DynamicJsonDocument`)
2. **ESP8266Audio** (Earle F. Philhower) — decodifica MP3

Já deve ter:
- TFT_eSPI (setup ST7789)
- XPT2046_Touchscreen
- ESP32-A2DP (ZIP)

---

## Preparar o cartão SD

Estrutura:

```text
SD/
├── lessons/
│   └── 007.json
├── audio/
│   └── 007.mp3
└── system/
    └── touch.cal     ← gerado pela calibração 03b (recomendado)
```

### Amostra de JSON
Use: `firmware/etapa1/sd_sample/lessons/007.json`

### MP3
Use um MP3 da lição 7 gerado pelo seu Audio Builder.

**Importante:** o Bluetooth funciona melhor com MP3 **44.1 kHz stereo**.

Se tiver `ffmpeg` no PC:

```bat
ffmpeg -y -i 007.mp3 -ar 44100 -ac 2 -b:a 128k 007_bt.mp3
```

Copie o resultado para o SD como `audio/007.mp3`.

### Exportador automático (opcional)

```bat
python firmware/etapa1/tools/export_sd_pack.py --build-dir CAMINHO\build_XXX --audio-dir CAMINHO\audio_test --out E:\ --ids 7
```

(`E:\` = letra do cartão SD)

### Calibração touch no SD

1. Coloque o SD na Yellow  
2. Grave de novo o sketch `03b_touch_calibracao`  
3. Calibre os 4 cantos  
4. Deve aparecer: `Salvo: /system/touch.cal`

---

## Gravar o firmware

1. Abra: `firmware/etapa1/diario_etapa1/diario_etapa1.ino`
2. Placa: **ESP32 Dev Module**
3. Partition: **Huge APP (3MB No OTA/1MB SPIFFS)**
4. Upload

### Antes de ligar
- SD com `007.json` + `007.mp3` (+ `touch.cal` se tiver)
- JBL despareada do celular, em modo Bluetooth

### Resultado esperado
- Splash **DIARIO ESTOICO**
- Lição 7 na tela (citação + reflexão)
- Texto rolando
- Áudio na JBL
- Toque pausa / continua

---

## Trocar o número da lição

Em `config.h`:

```cpp
#define LESSON_ID 7
```

Mude para `8`, `1`, etc., e coloque os arquivos correspondentes no SD.

---

## Problemas comuns

| Sintoma | O que fazer |
|---------|-------------|
| `Falha no SD` | FAT32; reinserir com placa desligada |
| `JSON nao encontrado` | Verificar `lessons/007.json` |
| Sem áudio | JBL em pairing; nome `JBL CINEMA SB110` |
| Áudio rápido/lento | Converter MP3 para 44.1 kHz |
| Touch torto | Rodar 03b com SD e gerar `touch.cal` |
| Compila com erro ArduinoJson | Instalar ArduinoJson 6.21.x |
| Falta memória | Confirmar Partition **Huge APP** |
