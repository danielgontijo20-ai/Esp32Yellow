# Etapa 0 — Preparar a ESP32-2432S028R (Yellow)

Placa: **ESP32-2432S028R** (USB-C)  
Caixa: **JBL CINEMA SB110**  
Objetivo: validar hardware **antes** do app Diário Estoico.

Ordem dos testes:

1. Serial (placa responde)
2. Tela
3. Touch
4. Cartão SD
5. Bluetooth → JBL

Só avance para o próximo teste quando o atual passar.

---

## 0. Material

- Placa Yellow USB-C
- Cabo USB-C **de dados** (não só carga)
- Cartão microSD FAT32 (pode estar vazio no teste 04)
- Caixa **JBL CINEMA SB110**
- PC com **Arduino IDE**

---

## 1. Instalar suporte ESP32 no Arduino IDE

1. Abra o Arduino IDE.
2. **Arquivo → Preferências**.
3. Em **URLs Adicionais para Gerenciadores de Placas**, cole:

```text
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

4. **Ferramentas → Placa → Gerenciador de Placas**.
5. Busque **esp32** (Espressif Systems) → **Instalar**.

### Configuração da placa (use sempre isto)

**Ferramentas:**

| Opção | Valor |
|--------|--------|
| Placa | **ESP32 Dev Module** |
| Upload Speed | 921600 |
| CPU Frequency | 240MHz |
| Flash Frequency | 80MHz |
| Flash Mode | QIO |
| Flash Size | **4MB** |
| Partition Scheme | **Huge APP (3MB No OTA/1MB SPIFFS)** |
| PSRAM | Disabled |
| Port | a porta COM da Yellow (Windows) |

Se o upload falhar: segure o botão **BOOT** da placa, clique em Upload, solte o BOOT quando começar a gravar.

---

## 2. Instalar bibliotecas

**Ferramentas → Gerenciar Bibliotecas** e instale:

1. **TFT_eSPI** (Bodmer)
2. **XPT2046_Touchscreen** (Paul Stoffregen)
3. **ESP32-A2DP** (Phil Schatzmann) — para o teste da JBL

---

## 3. Configurar TFT_eSPI (obrigatório)

A biblioteca TFT_eSPI **não** detecta a Yellow sozinha. Você precisa editar o setup.

1. No PC, abra a pasta das bibliotecas do Arduino, normalmente:

```text
Documentos\Arduino\libraries\TFT_eSPI\
```

2. Faça backup do arquivo `User_Setup.h` (copie e renomeie para `User_Setup.h.bak`).

3. Abra `User_Setup.h` e **substitua o conteúdo** pelo arquivo:

```text
firmware/etapa0/TFT_eSPI_User_Setup_CYD.h
```

(deste repositório — copie o conteúdo inteiro para dentro de `User_Setup.h`).

4. Salve.

Se a tela ficar invertida/errada no teste 02, avise: às vezes a variante usa `ILI9341_2_DRIVER` em vez de `ILI9341_DRIVER`.

---

## 4. Como abrir e gravar cada teste

1. Abra o `.ino` da pasta do teste (ex.: `01_serial_teste/01_serial_teste.ino`).
2. Confira placa/porta em **Ferramentas**.
3. Clique em **Upload** (→).
4. Abra o **Monitor Serial** em **115200 baud**.

---

## 5. O que cada teste deve mostrar

### 01 — Serial
- Monitor Serial imprime `Yellow OK` a cada segundo.
- Se não aparecer nada: cabo/porta/driver errado.

### 02 — Tela
- Tela preta com texto **DIARIO ESTOICO** e **Etapa 0 - Tela OK**.
- Se ficar branca/preta sem texto: revise `User_Setup.h`.

### 03 — Touch
- Toque na tela: aparece um ponto e coordenadas no Serial.
- Se não reagir: confira se instalou `XPT2046_Touchscreen`.

### 04 — SD
- Coloque um microSD FAT32 no slot **com a placa desligada**, depois ligue.
- Tela/Serial mostram `SD OK` e listam arquivos da raiz.
- Se falhar: formate FAT32, tente outro cartão (alguns SDXC grandes falham).

### 05 — Bluetooth JBL
1. Desconecte a JBL do celular.
2. Coloque a JBL em modo Bluetooth/pareamento.
3. Grave o sketch 05.
4. Na tela deve aparecer **Procurando JBL...** e depois **Conectado** (ou erro claro).

Nome buscado no código: `JBL CINEMA SB110`.

Se a barra anunciar outro nome no celular, anote o nome exato e me envie para ajustarmos o sketch.

---

## 6. Checklist (marque mentalmente)

- [ ] 01 Serial OK  
- [ ] 02 Tela OK  
- [ ] 03 Touch OK  
- [ ] 04 SD OK  
- [ ] 05 JBL conectada OK  

Quando os 5 estiverem OK, partimos para o firmware do Diário Estoico (Etapa 1).

---

## 7. Problemas comuns

| Problema | O que tentar |
|----------|----------------|
| Porta COM não aparece | Trocar cabo; instalar driver CP210x/CH340 |
| Upload falha | Segurar BOOT; baixar Upload Speed para 115200 |
| Tela sem imagem | Refazer `User_Setup.h`; conferir backlight |
| Touch sem resposta | Biblioteca XPT2046; rotação do touch |
| SD falha | FAT32; cartão ≤32GB costuma ser mais estável |
| JBL não conecta | Desparear do celular; modo pairing; nome exato |

---

## Estrutura desta pasta

```text
firmware/etapa0/
├── README.md
├── TFT_eSPI_User_Setup_CYD.h
├── 01_serial_teste/
├── 02_tela_teste/
├── 03_touch_teste/
├── 04_sd_teste/
└── 05_bluetooth_jbl/
```
