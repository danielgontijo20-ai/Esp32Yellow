# Etapa 0 — Preparar a ESP32-2432S028R (Yellow)

Placa: **ESP32-2432S028R** (USB-C)  
Caixa: **JBL CINEMA SB110**  
Objetivo: validar hardware **antes** do app Diário Estoico.

---

## Ordem dos testes

1. Serial  
2. Tela (limpeza total)  
3. Touch (calibração por cantos)  
4. Cartão SD  
5. Bluetooth → JBL  

Só avance quando o atual passar.

---

## 0. Material

- Placa Yellow USB-C
- Cabo USB-C **de dados**
- Cartão microSD FAT32
- Caixa **JBL CINEMA SB110**
- PC com **Arduino IDE**

---

## 1. Arduino IDE — placa ESP32

1. **Arquivo → Preferências**
2. URL adicional:

```text
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

3. **Ferramentas → Placa → Gerenciador de Placas** → instalar **esp32** (Espressif)

### Configuração

| Opção | Valor |
|--------|--------|
| Placa | **ESP32 Dev Module** |
| Upload Speed | 921600 |
| Flash Size | **4MB** |
| Partition Scheme | **Huge APP (3MB No OTA/1MB SPIFFS)** |
| Port | COM da Yellow |

---

## 2. Bibliotecas

Instale pelo Gerenciador:

- **TFT_eSPI** (Bodmer)
- **XPT2046_Touchscreen** (Paul Stoffregen)

A **ESP32-A2DP** quase não aparece na busca. Instale por ZIP:

1. Baixe: https://github.com/pschatzmann/ESP32-A2DP/archive/refs/heads/main.zip  
2. **Sketch → Incluir Biblioteca → Adicionar biblioteca .ZIP...**

**Não** instale a biblioteca **EspBle**.

---

## 3. Configurar a tela (muito importante)

Existem **duas variantes** da Yellow. Se sobrar a faixa do demo antigo (`shop` / `CPU` / `FPS`), o driver está errado.

### Passo A — tente primeiro ST7789 (comum em USB-C)

1. Abra `firmware/etapa0/TFT_eSPI_User_Setup_CYD_ST7789.h`
2. Copie **todo** o conteúdo
3. Cole em `Documentos\Arduino\libraries\TFT_eSPI\User_Setup.h`
4. Salve
5. Grave o teste `02b_tela_limpeza`

### Passo B — se ainda sobrar faixa, use ILI9341_2

1. Abra `firmware/etapa0/TFT_eSPI_User_Setup_CYD_ILI9341_2.h`
2. Substitua o `User_Setup.h` por esse conteúdo
3. Grave de novo o `02b_tela_limpeza`

### Sucesso da tela

A tela inteira deve ficar vermelha → verde → azul → preta, com **4 cantos amarelos**, e **sem** a faixa do demo de fábrica.

---

## 4. Testes

### 01 — Serial
Arquivo: `01_serial_teste`  
Sucesso: Monitor Serial `115200` mostra `Yellow OK`

### 02b — Limpeza da tela
Arquivo: `02b_tela_limpeza`  
Sucesso: cores cheias sem resto do demo antigo

### 03b — Touch calibrado
Arquivo: `03b_touch_calibracao`

1. Toque no alvo de cada canto (4 vezes)
2. Depois toque livremente: o ponto deve cair sob o dedo
3. Guarde os valores impressos no Serial (vamos reutilizar no app)

### 04 — SD
Arquivo: `04_sd_teste`  
Cartão FAT32, inserido com a placa desligada  
Sucesso: `SD OK`

### 05 — Bluetooth JBL
Arquivo: `05_bluetooth_jbl`  
Desparee a JBL do celular e deixe em pareamento  
Sucesso: `Conectado: JBL CINEMA SB110`

---

## Problemas comuns

| Problema | Solução |
|----------|---------|
| Faixa shop/CPU/FPS sobra | Trocar setup ST7789 ↔ ILI9341_2 |
| Touch no lugar errado | Usar `03b_touch_calibracao` |
| Upload falha | Segurar BOOT; cabo de dados |
| SD falha | FAT32; cartão ≤ 32 GB |
| JBL não conecta | Desparear do celular; modo pairing |

---

## Estrutura

```text
firmware/etapa0/
├── README.md
├── TFT_eSPI_User_Setup_CYD_ST7789.h
├── TFT_eSPI_User_Setup_CYD_ILI9341_2.h
├── TFT_eSPI_User_Setup_CYD.h          (legado)
├── 01_serial_teste/
├── 02_tela_teste/
├── 02b_tela_limpeza/
├── 03_touch_teste/
├── 03b_touch_calibracao/
├── 04_sd_teste/
└── 05_bluetooth_jbl/
```
