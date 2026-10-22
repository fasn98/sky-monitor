# M1 — Arquitetura e decisão build-vs-reuse

**Status:** proposta para revisão · **Data:** 2026-10-18 · **Base:** [`docs/prompt.md`](prompt.md)

Este documento fecha o marco M1. Nenhum código foi escrito ainda. Toda afirmação sobre software de terceiros tem a fonte citada no fim. O que não foi possível confirmar está marcado como **[A VERIFICAR]**.

---

## 1. Resumo das decisões

| Área | Decisão | Motivo principal |
|---|---|---|
| Captura all-sky | **Reaproveitar o indi-allsky** sem modificá-lo, como motor de captura | Já faz captura INDI/libcamera, timelapse, keogram, star trails, detecção de rastros, contagem de estrelas, pseudo-SQM, aquecedor de orvalho, sensores e MQTT [1] |
| Calibração e detecção avançada | **Construir** (camada própria em Python) | O indi-allsky detecta linhas, mas não faz calibração astrométrica da lente, classificação meteoro/satélite com incerteza nem mapa de nuvens por setor |
| Satélites | **Construir** com Skyfield + dados GP da CelesTrak em **JSON/OMM**, não TLE | Objetos novos têm número de catálogo de 6 dígitos e não existem em formato TLE [6] |
| Contribuição a redes de meteoros | **Adiar** e tratar como estação separada (opcional) | A BRAMON usa o pacote SonotaCo UFO [4], e o GMN desaconselha câmeras all-sky comerciais por falta de sensibilidade [5]. Ver seção 5 |
| Telescópio | **Construir** uma camada de abstração com backends **INDI** e **ASCOM Alpaca** | Permite trocar Seestar por montagem modular sem reescrever |
| Seestar | **Reaproveitar o seestar_alp** como ponte de controle | Controlador standalone com agendamento [2]. Usuários o usam para expor o S50 via Alpaca [3] |
| Agendador | **Construir** um agendador leve | N.I.N.A. só roda em Windows [7]. O Ekos é um app desktop (automatizável via D-Bus [8]), pesado demais para uma varanda com Raspberry Pi |
| Dashboard | **Construir** (FastAPI), apontando para a UI do indi-allsky onde ela já resolve | Evita duplicar a visualização ao vivo |
| Fotometria | **Construir** com photutils, exportando no **AAVSO Extended File Format** | Formato documentado [9] |
| Fonte de teste com celular *(adicionado em 2026-10-22)* | **Construído** `skymonitor.ingest.phone`: DNG/JPEG → FITS | Permite testar o processamento com céu real antes da câmera all-sky. Protocolo em [`protocolo-captura-celular.md`](protocolo-captura-celular.md) |

---

## 2. Visão geral dos componentes

```mermaid
flowchart LR
  subgraph HW[Hardware na varanda]
    CAM[Câmera all-sky<br/>ZWO / RPi HQ]
    SENS[Sensores<br/>BME280, MLX90614]
    DEW[Aquecedor de orvalho]
    TEL[Telescópio<br/>Seestar ou montagem INDI]
  end

  subgraph PI[Raspberry Pi 5]
    IAS[indi-allsky<br/>captura · keogram · timelapse<br/>pseudo-SQM · MQTT]
    MQ[(Broker MQTT<br/>Mosquitto)]
    subgraph SM[sky-monitor - este repositório]
      ING[ingest<br/>novos frames + MQTT]
      CAL[calib<br/>modelo da lente]
      DET[detect<br/>meteoros · nuvens · satélites]
      SCH[scheduler<br/>máscara de horizonte + gate de nuvens]
      TELB[telescope<br/>backends INDI / Alpaca]
      PHOT[photometry<br/>photutils → AAVSO]
      API[api + dashboard<br/>FastAPI]
      ALR[alerts<br/>Telegram / e-mail]
      DB[(SQLite → PostgreSQL)]
    end
    ALP[seestar_alp<br/>ponte Alpaca]
  end

  EXT1[CelesTrak<br/>GP JSON/OMM]
  EXT2[Open-Meteo]

  CAM --> IAS
  SENS --> IAS
  IAS --> DEW
  IAS -- FITS/JPEG --> ING
  PHONE[Celular S24<br/>DNG/JPEG - testes] -. ingest.phone → FITS .-> ING
  IAS -- métricas --> MQ --> ING
  ING --> CAL --> DET
  EXT1 --> DET
  DET --> DB
  DET --> SCH
  EXT2 --> SCH
  SCH --> TELB
  TELB -- INDI --> TEL
  TELB -- Alpaca --> ALP --> TEL
  TELB --> PHOT --> DB
  DB --> API
  DET --> ALR
  TELB --> ALR
```

**Princípio central:** o indi-allsky é tratado como um *produtor de dados* externo. O sky-monitor lê os arquivos que ele grava e as mensagens MQTT que ele publica, sem importar nem modificar o código dele. Isso mantém os dois projetos atualizáveis de forma independente.

> **Nota de licença (não é aconselhamento jurídico):** o indi-allsky é GPL-3.0 [1] e o pyindi-client é GPLv3+ [10]. Comunicação por arquivos e MQTT costuma ser tratada como programas separados. Já um módulo nosso que importe o pyindi-client provavelmente herda a GPL. Este repositório é licenciado sob **GPL-3.0**, o que elimina esse conflito.

---

## 3. Fluxo de dados de uma noite

1. **Crepúsculo:** o indi-allsky começa a capturar no modo noturno. O sky-monitor calcula o crepúsculo astronômico com Skyfield a partir das coordenadas do `config.yaml`, para seu próprio agendamento.
2. **Cada frame:**
   - `ingest` detecta o novo arquivo e registra os metadados no banco.
   - `calib` aplica o modelo da lente, convertendo pixel em azimute/altitude.
   - `detect` calcula a contagem de estrelas por setor (mapa de nuvens) e o brilho de fundo.
3. **Rastro detectado:** `detect` mede a trajetória em az/alt e compara com as posições de satélites previstas pelo Skyfield para o mesmo instante. O evento é classificado como **satélite**, **avião** ou **meteoro candidato**, sempre com a margem de erro registrada.
4. **A cada N minutos:**
   - `scheduler` escolhe o próximo alvo do telescópio. O alvo precisa estar acima da altitude mínima, dentro da máscara de horizonte e em setor sem nuvens, e a previsão do Open-Meteo não pode indicar chuva.
   - `telescope` executa a observação; `photometry` processa as imagens.
5. **Segurança:** umidade acima do limite, chuva, perda de conexão ou fim da noite disparam o *park* e um alerta.
6. **Amanhecer:**
   - o indi-allsky gera o timelapse e o keogram;
   - o sky-monitor gera o resumo da noite (fração de céu limpo, eventos, qualidade do céu) e envia um alerta resumido.

---

## 4. Avaliação dos projetos existentes

### 4.1 indi-allsky — **reaproveitar**
- **O que entrega** [1]:
  - suporte a câmeras INDI, incluindo vários modelos ZWO testados, e câmeras Raspberry Pi via libcamera;
  - timelapse, keogram em tempo real e star trails;
  - detecção de rastros (meteoro, avião, satélite) por detecção de linhas no OpenCV;
  - contagem de estrelas como medida objetiva das condições do céu e pseudo-SQM;
  - dashboard Flask;
  - SQLite ou MySQL/MariaDB;
  - MQTT com auto-discovery para Home Assistant;
  - sensores e controle de aquecedor de orvalho (inclusive PWM).
- **Plataforma:** recomenda Raspberry Pi 5 com Raspberry Pi OS 64-bit e pacote `.deb` nativo. ARM 32-bit não funciona [1].
- **Atividade:** mais de 10 mil commits e suporte a distribuições recentes (Debian 13, Ubuntu 26.04) [1].
- **Lacunas que justificam código próprio:**
  - não há calibração astrométrica da lente documentada;
  - não há detecção de nuvens explícita, só condições inferidas da contagem de estrelas;
  - a classificação de rastros é por geometria, sem incerteza formal.

### 4.2 seestar_alp — **reaproveitar (Fase 2)**
- Controlador standalone para comando, controle e agendamento do Seestar, com interface web [2].
- Roda em Windows, macOS, Linux e Raspberry Pi, e tem Docker [2].
- O repositório inclui componentes Alpaca e arquivos de validação ConformU [2]. Usuários relatam usá-lo para expor o S50 via protocolo Alpaca [3].
- **[A VERIFICAR no M5]:** tipos de dispositivo Alpaca expostos, portas e quais comandos funcionam com o firmware atual. A integração com o Ekos ainda não tinha relato de funcionamento na discussão consultada [3].
- O repositório lista as licenças MIT, BSD-3-Clause e GPL-3.0 por componente [2].

### 4.3 KStars/Ekos — **não usar como núcleo, manter como alternativa**
- É possível automatizá-lo via D-Bus (serviço `org.kde.kstars`, scheduler em `/KStars/Ekos/Scheduler`) [8].
- Faz sentido se no futuro você optar por um setup modular com notebook. Para um Raspberry Pi sem monitor numa varanda, um agendador próprio e enxuto é mais simples de operar e testar.

### 4.4 N.I.N.A. — **descartado para este ambiente**
- Requer Windows 10 64-bit ou superior [7].
- Suporta Alpaca [7], então continua compatível se um dia houver um PC Windows na estação.

---

## 5. Meteoros e redes de ciência cidadã — ponto de atenção

Este é o ponto em que a pesquisa mudou o plano original:

- A **BRAMON** usa o pacote SonotaCo UFO (UFOCapture, UFOAnalyzer, UFOOrbit). As estações padrão usam câmeras de vigilância em campo plano; o modelo original (Samsung SCB 2000) foi descontinuado e o IMX291 é sugerido como substituto [4].
- O **Global Meteor Network** usa o software RMS em Raspberry Pi 4/5 com câmera de vídeo de baixa luminosidade via PoE. A própria documentação diz que uma câmera all-sky comercial "geralmente não é uma boa ideia", por falta de sensibilidade [5].

**Consequência:** a câmera all-sky do sky-monitor serve muito bem para monitoramento (nuvens, bólidos, satélites, qualidade do céu), mas **não deve ser apresentada como estação científica de meteoros**. Se você quiser contribuir com essas redes, o caminho honesto é uma **estação dedicada opcional**: uma câmera IMX291 com lente de campo médio rodando RMS (GMN) ou UFOCapture (BRAMON, que roda em Windows). O sky-monitor pode ingerir os resultados dessa estação no mesmo dashboard. O formato de exportação deve ser combinado diretamente com a BRAMON [4].

---

## 6. Detalhes técnicos por módulo

### 6.1 Calibração da lente (`calib`)
- O modelo de projeção olho-de-peixe (equidistante como ponto de partida, mais termos radiais) é ajustado por mínimos quadrados entre os centroides de estrelas detectadas e as posições de catálogo (Yale BSC ou Hipparcos) transformadas para alt/az com Astropy.
- Entrega o resíduo RMS em graus junto com o modelo. Cada evento herda essa incerteza.
- Recalibração automática semanal, ou quando o resíduo piorar (detecta se a câmera foi movida).

### 6.2 Mapa de nuvens (`detect`)
- O céu é dividido em células (ex.: anéis de altitude × setores de azimute).
- Por célula: razão entre estrelas detectadas e estrelas esperadas acima de um limite de magnitude, que é calibrado na própria estação em noites limpas.
- O sensor IR é opcional e entra como evidência adicional.
- **Limitação declarada:** com a Lua alta, a contagem cai mesmo com céu limpo. O limiar é corrigido pela fase e altitude lunar, e as noites afetadas são marcadas.

### 6.3 Satélites
- Busca os dados GP da CelesTrak em `FORMAT=json` (OMM), porque objetos com número de catálogo ≥ 100000 não têm TLE [6].
- Cache local com atualização espaçada, respeitando a política de uso da CelesTrak [6]. **[A VERIFICAR]** a frequência permitida.
- Propagação com Skyfield. O rastro é classificado como satélite se a trajetória prevista coincidir dentro de N × a incerteza da calibração.

### 6.4 Telescópio (`telescope`)
```python
class TelescopeBackend(Protocol):
    def connect(self) -> None: ...
    def slew_to(self, ra_deg: float, dec_deg: float) -> None: ...
    def is_slewing(self) -> bool: ...
    def park(self) -> None: ...
    def capture(self, exposure_s: float, gain: int) -> Path: ...
```
- Implementações previstas:
  - `IndiBackend`, via pyindi-client;
  - `AlpacaBackend`, via cliente Python Alpaca (alpyca, **[A VERIFICAR]** licença e versão);
  - `SimulatorBackend`, para os testes.
- Plate-solving com ASTAP ou astrometry.net local, chamados por CLI.

### 6.5 Fotometria
- Fotometria diferencial de abertura com photutils, usando estrela de comparação e estrela de verificação.
- Exportação no AAVSO Extended File Format [9]:
  - **cabeçalho:** `#TYPE=Extended`, `#OBSCODE`, `#SOFTWARE`, `#DELIM`, `#DATE`, `#OBSTYPE`;
  - **colunas:** STARID, DATE, MAGNITUDE, MAGERR, FILTER, TRANS, MTYPE, CNAME, CMAG, KNAME, KMAG, AIRMASS, GROUP, CHART, NOTES;
  - `na` em campos opcionais sem dado.
- Com câmera colorida sem filtro fotométrico, o filtro reportado deve ser o código não-padrão correspondente (ex.: `CV`) e nunca `V` [9].

### 6.6 Dados e dashboard
- **Banco:** SQLAlchemy com SQLite no início e PostgreSQL depois, sem mudar o código.
- **FITS:** armazenados em disco com retenção configurável (ex.: manter só frames com eventos depois de X dias).
- **Dashboard:** FastAPI com frontend leve e responsivo. A imagem ao vivo vem do indi-allsky.
- **Previsão do tempo:** Open-Meteo, com as coordenadas do config.
- **Alertas:** bot do Telegram como canal principal.

---

## 7. Estrutura proposta do repositório

```
sky-monitor/
├── README.md
├── CLAUDE.md                 # convenções para agentes
├── pyproject.toml            # Python 3.11+, ruff, mypy, pytest
├── config/
│   └── example.yaml          # coordenadas, máscara de horizonte, limites
├── src/skymonitor/
│   ├── config.py
│   ├── ingest/               # watcher de arquivos + cliente MQTT
│   ├── calib/                # modelo da lente
│   ├── detect/               # nuvens, rastros, satélites
│   ├── telescope/            # Protocol + backends
│   ├── scheduler/
│   ├── photometry/
│   ├── storage/              # SQLAlchemy
│   ├── api/                  # FastAPI + dashboard
│   └── alerts/
├── tests/
│   ├── data/                 # imagens all-sky de teste (com fonte e licença)
│   └── ...
├── deploy/
│   ├── systemd/
│   └── docker/
└── docs/
    ├── prompt.md
    └── M1-arquitetura.md
```

---

## 8. Perguntas para você (decidem o M2 em diante)

1. ~~**Licença do repositório**~~ — **Decidido em 2026-10-18: GPL-3.0** (ver `LICENSE`). É compatível com o indi-allsky e o pyindi-client.
2. **Fase 2:** Seestar (mais rápido, menos flexível) ou montagem modular? Isso define qual backend do telescópio será construído primeiro.
3. **Estação de meteoros dedicada** (seção 5): quer incluir no roadmap como fase opcional?
4. ~~**Hardware de desenvolvimento**~~ — **Respondido em 2026-10-18:** ainda não há Raspberry Pi. O M2 será desenvolvido no notebook do usuário, em Docker, com os simuladores INDI. A migração para o Pi fica para depois.
5. **Varanda:** quando souber, a orientação (N/S/L/O) e os obstáculos alimentam a máscara de horizonte.

## 9. Suposições em aberto

- Funcionamento do indi-allsky com `indi_simulator_ccd` para testes sem hardware **[A VERIFICAR no M2]**.
- Formato exato das mensagens MQTT do indi-allsky **[A VERIFICAR no M2]**.
- Detalhes da interface Alpaca do seestar_alp com o firmware atual **[A VERIFICAR no M5]**.
- Política de frequência de download da CelesTrak **[A VERIFICAR no M3]**.

---

## Fontes

1. indi-allsky — https://github.com/aaronwmorris/indi-allsky
2. seestar_alp — https://github.com/smart-underworld/seestar_alp
3. AstroBin, discussão "Seestar S50 Linux control via KStars/Ekos/INDI/Alpaca" — https://app.astrobin.com/forum/topic/239056/seestar-s50-linux-control-via-kstars-ekos-indi-alpaca
4. "A importância das redes de monitoramento de meteoros", Revista Brasileira de Ensino de Física, v. 47 (2025) — https://www.scielo.br/j/rbef/a/y8bqvjMGccgDGhHrWG54NYS/?lang=pt
5. Global Meteor Network, wiki — https://globalmeteornetwork.org/wiki/
6. CelesTrak, GP element data — https://celestrak.org/NORAD/elements/
7. N.I.N.A., requisitos — https://nighttime-imaging.eu/docs/master/site/requirements
8. "Automating KStars & Ekos, Part 1" — https://openastronomy.substack.com/p/automating-kstars-and-ekos-part-1
9. AAVSO Extended File Format — https://aavso.org/node/76453
10. pyindi-client (PyPI) — https://pypi.org/project/pyindi-client/
