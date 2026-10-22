# BOM — Estação all-sky (protótipo em protoboard)

**Objetivo:** montar na bancada o conjunto Raspberry Pi 5 + câmera + sensores, validar o sistema (indi-allsky + sky-monitor) e depois levar para a varanda.

**Data:** 2026-10-22. Preços ficam em branco de propósito: variam muito no Mercado Livre e com importação. Compare na hora da compra.

Legenda: **[OBR]** obrigatório · **[REC]** recomendado · **[OPC]** opcional.

---

## A. Computador

| # | Qtd | Item | Especificação | Por quê | Atenção na compra |
|---|---|---|---|---|---|
| A1 | 1 | **Raspberry Pi 5** [OBR] | 8 GB de RAM | Roda indi-allsky + detecção/calibração do sky-monitor | Tem que ser *Raspberry Pi* original (não Orange/Banana Pi). Vendedor com boa reputação |
| A2 | 1 | **Fonte oficial USB-C 27 W** [OBR] | 5,1 V / 5 A, USB-PD | Com fonte comum o Pi 5 limita a corrente das portas USB e pode reiniciar sob carga | Evite "fonte 5 V 3 A genérica" |
| A3 | 1 | **Active Cooler oficial** [OBR] | Dissipador + ventoinha para Pi 5 | Uso contínuo a noite toda aquece o SoC | É específico do Pi 5 |
| A4 | 1 | **Cartão microSD 64 GB** [OBR] | Classe A2, marca conhecida (Samsung, SanDisk, Kingston) | Sistema e dados iniciais | Muita falsificação: desconfie de preço muito baixo |
| A5 | 1 | **Bateria RTC oficial do Pi 5** [REC] | Panasonic ML-2020 recarregável, com conector para o header "BAT" | Mantém o relógio certo sem internet. Horário correto é essencial para astrometria e meteoros | O carregamento precisa ser ativado na configuração (ver documentação oficial do Pi) |
| A6 | 1 | Cabo micro-HDMI → HDMI [OPC] | — | Só para a primeira configuração com monitor | Dá para configurar sem monitor, via rede (SSH) |
| A7 | 1 | Cabo de rede (Ethernet) [OPC] | Cat 5e ou superior | Conexão mais estável que Wi-Fi na bancada | — |

## B. Câmera e óptica

| # | Qtd | Item | Especificação | Por quê | Atenção na compra |
|---|---|---|---|---|---|
| B1 | 1 | **Raspberry Pi High Quality Camera — versão M12** [OBR] | Sony IMX477, 12,3 MP, 7,9 mm de diagonal (1/2.3"), filtro IR integrado | Suportada pelo indi-allsky via libcamera, com captura RAW (DNG) | **Vem sem lente** e não funciona sem uma. Prefira a **M12**. Alternativa: versão C/CS + a lente LN031, que vem com adaptador M12 → C/CS |
| B2 | 1 | **Lente olho-de-peixe M12 para sensor 1/2.3"** [OBR] | Ex.: Arducam LN031, 1,56 mm, f/2, cerca de 180° na HQ Camera | Cobre o céu inteiro | Confirme "1/2.3 polegada" no anúncio. Lentes para sensores menores (1/3", 1/4") deixam a imagem com borda preta ou cortada |
| B3 | 1 | **Cabo de câmera para Pi 5** [OBR] | "Mini para padrão" (22 → 15 pinos), 200–300 mm | O Pi 5 tem conector de câmera menor; o cabo que vem na HQ Camera não encaixa nele | Item barato e fácil de esquecer |

> **Campo de visão (estimativa):** com 1,56 mm e projeção equidistante, o círculo de 180° teria ~4,9 mm de diâmetro, um pouco maior que a altura do sensor (~4,7 mm). Ou seja, círculo quase completo, com um corte pequeno no topo e na base. **[A VERIFICAR]** na primeira imagem real, porque a projeção exata da lente não é publicada.

## C. Sensores (protoboard)

| # | Qtd | Item | Especificação | Por quê | Atenção na compra |
|---|---|---|---|---|---|
| C1 | 1 | **BME280** [OBR] | Módulo I2C, 3,3 V | Temperatura, umidade e pressão. Com isso o sistema calcula o **ponto de orvalho** e controla o aquecedor | **Muito anúncio vende BMP280 como BME280.** O BMP280 não mede umidade. Confirme "BME280" e "umidade" na descrição. A placa roxa "GY-BME/P-280" é usada para os dois chips. Teste ao receber: o registrador 0xD0 retorna **0x60** no BME280 e 0x56–0x58 no BMP280 |
| C2 | 1 | **MLX90614 versão 3 V (ESF-BAA)** [REC] | Infravermelho, I2C, endereço 0x5A, campo de 90° | Mede a temperatura do céu: céu limpo é muito mais frio que nuvem. É o detector de nuvens independente da câmera | Existe versão de 5 V (ESF-**AAA**). Prefira a **BAA** (3,3 V) ou um módulo GY-906 com regulador |
| C3 | 1 | **DS18B20 à prova d'água** [REC] | Sonda 1-Wire com cabo | Temperatura da lente/cúpula, para comparar com o ponto de orvalho | Precisa de resistor de 4,7 kΩ. Existem kits que já trazem uma plaquinha adaptadora com o resistor |
| C4 | 1 | TSL2591 [OPC] | Sensor de luz I2C | Referência de brilho do céu e do crepúsculo | — |
| C5 | 1 | Módulo GPS USB (u-blox) [OPC] | Compatível com gpsd | Posição e horário sem internet | — |

## D. Controle e potência (protoboard)

| # | Qtd | Item | Especificação | Por quê | Atenção na compra |
|---|---|---|---|---|---|
| D1 | 1 | **Módulo MOSFET de nível lógico** [OBR] | Ex.: módulo D4184 (AOD4184), aciona com 3,3 V, de preferência com 2 canais | O GPIO do Pi não pode alimentar o aquecedor direto. O MOSFET faz o chaveamento (PWM) | **Evite o módulo "IRF520"**: ele não conduz direito com os 3,3 V do Pi |
| D2 | 1 | **Aquecedor anti-orvalho** [OBR] | Pastilha PTC de 12 V, 5–10 W | Evita orvalho na cúpula. O PTC limita a própria temperatura, o que é mais seguro | Potência baixa é suficiente para uma cúpula pequena |
| D3 | 1 | **Fonte 12 V, 2 A** [OBR] | Com plug P4, mais adaptador P4 → borne | Alimenta o aquecedor (e o ventilador, se for de 12 V) | O GND da fonte de 12 V precisa ser ligado ao GND do Pi |
| D4 | 1 | Kit de resistores [OBR] | Inclui 4,7 kΩ e 10 kΩ | Pull-up do DS18B20 e usos gerais | — |
| D5 | 1 | Ventilador 40 mm [OPC] | 5 V ou 12 V | Circulação dentro da caixa, contra condensação | Use o 2º canal do MOSFET |

## E. Bancada

| # | Qtd | Item | Especificação | Por quê |
|---|---|---|---|---|
| E1 | 1 | **Protoboard 830 pontos** [OBR] | — | Montagem sem solda |
| E2 | 1 | **Jumpers** [OBR] | Kit macho-macho, macho-fêmea e fêmea-fêmea | Ligações entre Pi, protoboard e módulos |
| E3 | 1 | **T-Cobbler (extensor GPIO 40 pinos) + cabo flat** [REC] | — | Leva os pinos do Pi para a protoboard com os nomes impressos, o que reduz erro de ligação |
| E4 | 1 | **Multímetro** [REC] | Básico | Conferir tensões antes de ligar os módulos |
| E5 | 1 | Leitor de cartão microSD (USB) [REC] | — | Gravar o sistema no cartão pelo notebook |

## F. Instalação externa (depois da bancada)

| # | Qtd | Item | Especificação | Por quê |
|---|---|---|---|---|
| F1 | 1 | Caixa hermética IP65 | Cabe o Pi, a câmera e o MOSFET | Proteção contra chuva |
| F2 | 1 | Cúpula de acrílico transparente | Tipo usada em câmeras de segurança | Janela para a lente |
| F3 | 2–3 | Prensa-cabos (PG7/PG9) | — | Passagem de cabos vedada |
| F4 | 1 | Sílica gel em sachês | — | Umidade dentro da caixa (importante em SC) |
| F5 | 1 | SSD NVMe + M.2 HAT+ oficial [OPC] | — | Substitui o microSD para gravação contínua por anos |

---

## Resumo por fase

- **Comprar agora para a bancada:** A1–A4, B1–B3, C1, D1–D4, E1–E2. Recomendo também A5, C2, C3, E3 e E4.
- **Depois:** C4, C5, D5 e o bloco F.

## Ligações (resumo para a protoboard)

| Módulo | Pino do módulo | Pino do Pi 5 |
|---|---|---|
| BME280 / MLX90614 / TSL2591 (I2C, em paralelo) | VCC / GND / SDA / SCL | 3V3 (pino 1) / GND (pino 6) / GPIO 2 (pino 3) / GPIO 3 (pino 5) |
| DS18B20 (1-Wire) | dados (+ 4,7 kΩ para 3V3) | GPIO 4 (pino 7), padrão do 1-Wire |
| MOSFET (aquecedor) | sinal / GND | um pino com PWM em hardware, ex. GPIO 18 (pino 12) **[A VERIFICAR no Pi 5]** / GND |

Os sensores I2C dividem os mesmos dois fios (cada um tem endereço próprio). Para habilitar I2C e 1-Wire: `sudo raspi-config`.

## Fontes

- indi-allsky, sensores suportados: https://github-wiki-see.page/m/aaronwmorris/indi-allsky/wiki/Sensors
- indi-allsky, aquecedor de orvalho: https://github-wiki-see.page/m/aaronwmorris/indi-allsky/wiki/Dew-Heater-Support
- indi-allsky, HQ Camera: https://github.com/aaronwmorris/indi-allsky/wiki/Raspberry-PI-HQ-Camera
- HQ Camera M12 (conteúdo da caixa, cabo do Pi 5): https://www.pishop.us/product/raspberry-pi-hq-camera-m12/
- Arducam LN031: https://welectron.com/Arducam-LN031-180-Degree-Fisheye-1-23-M12-Lens-with-Lens-Adapter-for-Raspberry-Pi-High-Quality-Camera
- MLX90614 3 V (ESF-BAA): https://www.adafruit.com/products/1747
- Bateria RTC do Pi 5: https://www.pishop.us/product/rtc-battery-for-raspberry-pi-5/
